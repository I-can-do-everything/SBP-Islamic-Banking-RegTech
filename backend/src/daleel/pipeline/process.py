"""Calculation step: canonical datasets in, metrics and checks out.

Pure function of its inputs (canonical Parquet files, the reporting date, the
rulebook and the mapping), so the same inputs always give the same results.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

import duckdb

import daleel.metrics.definitions
from daleel.mapping.mapper import MappingReport, build_gold, load_mapping
from daleel.metrics.credit import enrich_contracts
from daleel.metrics.engine import Context, MetricResult, run_all
from daleel.rulebook.rulebook import load_rulebook
from daleel.validation.checks import Check, run_checks

TABLES = {"TRIAL_BALANCE": "trial_balance", "FINANCING": "financing", "DEPOSITS": "deposits",
          "POOLS": "pools", "CAPITAL": "capital"}


@dataclass
class ProcessResult:
    metrics: list[MetricResult]
    checks: list[Check]
    mapping: MappingReport | None
    gold: list[dict]
    mapping_version: str | None
    con: duckdb.DuckDBPyConnection


def process(parquet: dict[str, str], as_of: date, period_days: int, ingestion: dict) -> ProcessResult:
    con = duckdb.connect()
    book = load_rulebook()
    available = set()
    for kind, table in TABLES.items():
        if kind in parquet and Path(parquet[kind]).exists():
            con.execute(f"CREATE TABLE {table} AS SELECT * FROM read_parquet('{parquet[kind]}')")
            available.add(kind)
    if "FINANCING" in available:
        enrich_contracts(con, "financing", book, as_of)
    mapping_report, mapping_version, gold = None, None, []
    if "TRIAL_BALANCE" in available:
        mapping = load_mapping()
        mapping_version = mapping.version
        mapping_report = build_gold(con, mapping)
        gold = [dict(zip(("code", "label", "normal", "grp", "signed_amount", "presented", "source_count"), r))
                for r in con.execute("SELECT code, label, normal, grp, signed_amount, presented, source_count "
                                     "FROM gold ORDER BY code").fetchall()]
    ctx = Context(con, book, as_of, period_days, available)
    metrics = run_all(ctx)
    order = {m: i for i, m in enumerate(daleel.metrics.engine.REGISTRY)}
    for m in metrics:
        m.sort_order = order[m.id]
    metrics.sort(key=lambda m: m.sort_order)
    checks = run_checks(con, book, as_of, available, mapping_report, ingestion)
    return ProcessResult(metrics, checks, mapping_report, gold, mapping_version, con)
