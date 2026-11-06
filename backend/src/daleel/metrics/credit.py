"""Contract level credit calculations, done in DuckDB SQL so they scale.

For every financing contract this works out:

- classification and IFRS 9 stage from days past due, using the bands in
  SBP's IFRS 9 Application Instructions, Annexure C (rule asset_quality.classification)
- Prudential Regulations (PR) provision: rate x (outstanding less forced sale value)
- expected credit loss (ECL):
    Stage 1: 12 month PD x LGD x exposure
    Stage 2: lifetime PD x LGD x exposure
    Stage 3: LGD x exposure (default has happened, so PD is 1)
- required provision: ECL, except Stage 3 where it is the higher of ECL and the
  PR amount (the SBP "whichever is higher" rule)
- risk weight class for credit RWA (past due contracts use PAST_DUE)

The rulebook is turned into SQL CASE expressions, so one query handles the whole
portfolio using every CPU core, whether it has 3 thousand or 3 million rows.
All amounts stay DECIMAL; nothing passes through floating point.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import duckdb

from daleel.rulebook.rulebook import Rulebook

RATE = "DECIMAL(18,10)"
AMOUNT = "DECIMAL(38,4)"


def _lit(value: Decimal) -> str:
    return f"CAST('{value}' AS {RATE})"


def classification_case(book: Rulebook, as_of: date) -> tuple[str, str]:
    """SQL CASE expressions giving (classification, stage) from portfolio and DPD."""
    table = book.get("asset_quality.classification", as_of).table
    cls_parts, stage_parts = [], []
    for portfolio, bands in table.items():
        cls_when, stage_when = [], []
        for low, high, label, stage in bands:
            cond = f"days_past_due >= {low}" + (f" AND days_past_due <= {high}" if high is not None else "")
            cls_when.append(f"WHEN {cond} THEN '{label}'")
            stage_when.append(f"WHEN {cond} THEN {stage}")
        cls_parts.append(f"WHEN '{portfolio}' THEN CASE {' '.join(cls_when)} END")
        stage_parts.append(f"WHEN '{portfolio}' THEN CASE {' '.join(stage_when)} END")
    return (
        f"CASE portfolio {' '.join(cls_parts)} END",
        f"CASE portfolio {' '.join(stage_parts)} END",
    )


def _map_case(column: str, table: dict, divide_by_100: bool = True) -> str:
    parts = []
    for key, value in table.items():
        v = Decimal(value) / 100 if divide_by_100 else Decimal(value)
        parts.append(f"WHEN '{key}' THEN {_lit(v)}")
    return f"CASE {column} {' '.join(parts)} END"


def enrich_contracts(con: duckdb.DuckDBPyConnection, source: str, book: Rulebook, as_of: date,
                     target: str = "contracts") -> None:
    """Create table `target` from relation `source` (canonical FINANCING columns)."""
    cls_case, stage_case = classification_case(book, as_of)
    pr_case = _map_case("classification", book.get("asset_quality.pr_provision_rate", as_of).table)
    pd_defaults = book.get("asset_quality.default_pd", as_of).table
    default_lgd = book.value("asset_quality.default_lgd", as_of) / 100
    pd1 = _lit(pd_defaults["1"] / 100)
    pd2 = _lit(pd_defaults["2"] / 100)

    con.execute(f"""
        CREATE OR REPLACE TABLE {target} AS
        WITH base AS (
            SELECT *,
                   {cls_case} AS classification,
                   {stage_case} AS stage
            FROM {source}
        ),
        params AS (
            SELECT *,
                   CAST(coalesce(lgd, {_lit(default_lgd)}) AS {RATE}) AS lgd_used,
                   CAST(CASE stage WHEN 1 THEN coalesce(pd_12m, {pd1})
                                   WHEN 2 THEN coalesce(pd_lifetime, {pd2})
                                   ELSE 1 END AS {RATE}) AS pd_used,
                   (lgd IS NULL) AS lgd_defaulted,
                   (stage = 1 AND pd_12m IS NULL) OR (stage = 2 AND pd_lifetime IS NULL) AS pd_defaulted,
                   CAST(greatest(outstanding - coalesce(collateral_fsv, 0), 0) AS {AMOUNT}) AS net_of_fsv
            FROM base
        ),
        calc AS (
            SELECT *,
                   CAST(round(outstanding * pd_used * lgd_used, 4) AS {AMOUNT}) AS ecl,
                   CAST(round(net_of_fsv * {pr_case}, 4) AS {AMOUNT}) AS pr_required
            FROM params
        )
        SELECT *,
               CAST(CASE WHEN stage = 3 THEN greatest(ecl, pr_required) ELSE ecl END AS {AMOUNT})
                   AS provision_required,
               CASE WHEN stage = 3 THEN 'PAST_DUE' ELSE counterparty_type END AS rw_class
        FROM calc
    """)
