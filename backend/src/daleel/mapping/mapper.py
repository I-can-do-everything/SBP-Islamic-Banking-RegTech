"""Maps the bank's GL accounts to reporting codes (the gold layer).

Sign convention (DEC-008, closes FIX-015):
- signed amount = debit minus credit (debit positive), the ledger convention
- each reporting code has a normal side; the presented amount is positive when
  the balance sits on that side
- calculations read presented amounts only
- a code whose presented amount is negative is on its abnormal side and is
  reported as a warning, never silently flipped

Matching (closes BUG-018): a rule's pattern must match the WHOLE GL code.
If one account matches more than one rule, the first rule wins and the overlap
is reported, because rule order should never decide an answer silently.

Apportionment (closes BUG-019): shares are exact decimals that must total 100%.
Every share is rounded to 4 places except the largest, which takes the
remainder, so the split always adds back to the original amount.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from decimal import Decimal
from functools import lru_cache

import duckdb
import yaml

from daleel.core.config import get_settings
from daleel.core.errors import InvalidInput


@dataclass(frozen=True)
class ReportingCode:
    code: str
    label: str
    normal: str
    group: str
    rw: str | None


@dataclass(frozen=True)
class Rule:
    order: int
    pattern: str
    split: tuple[tuple[str, Decimal], ...]

    def matches(self, gl_code: str) -> bool:
        return re.fullmatch(self.pattern, gl_code) is not None


@dataclass
class MappingSet:
    version: str
    codes: dict[str, ReportingCode]
    rules: list[Rule]


@dataclass
class MappingReport:
    version: str
    unmapped: list[dict] = field(default_factory=list)
    overlaps: list[dict] = field(default_factory=list)
    abnormal: list[dict] = field(default_factory=list)
    mapped_accounts: int = 0


@lru_cache
def load_mapping(name: str = "default") -> MappingSet:
    base = get_settings().mappings_dir
    codes_data = yaml.safe_load((base / "reporting_codes.yaml").read_text())
    codes = {c["code"]: ReportingCode(c["code"], c["label"], c["normal"], c["group"], c.get("rw"))
             for c in codes_data["codes"]}
    data = yaml.safe_load((base / f"{name}.yaml").read_text())
    rules = []
    for i, r in enumerate(data["rules"]):
        if r.get("kind") == "apportion":
            split = tuple((k, Decimal(str(v))) for k, v in r["split"].items())
            if sum(s for _, s in split) != Decimal(100):
                raise InvalidInput("bad_split", f"Apportionment for {r['pattern']} does not total 100%.")
        else:
            split = ((r["code"], Decimal(100)),)
        for code, _ in split:
            if code not in codes:
                raise InvalidInput("unknown_code", f"Mapping rule uses unknown reporting code {code}.")
        re.compile(r["pattern"])
        rules.append(Rule(i, r["pattern"], split))
    return MappingSet(data["version"], codes, rules)


def build_gold(con: duckdb.DuckDBPyConnection, mapping: MappingSet) -> MappingReport:
    """From table `trial_balance` create `gl_map` and `gold` tables in DuckDB."""
    report = MappingReport(mapping.version)
    codes = [r[0] for r in con.execute("SELECT DISTINCT gl_code FROM trial_balance").fetchall()]
    rows = []
    for gl in codes:
        hits = [r for r in mapping.rules if r.matches(gl)]
        if not hits:
            continue
        if len(hits) > 1:
            report.overlaps.append({"gl_code": gl, "rules": [h.pattern for h in hits],
                                    "used": hits[0].pattern})
        rule = hits[0]
        largest = max(rule.split, key=lambda s: s[1])[0]
        for code, share in rule.split:
            rows.append((gl, code, share / 100, code == largest))
    con.execute("CREATE OR REPLACE TABLE gl_map (gl_code VARCHAR, code VARCHAR, share DECIMAL(18,10), "
                "takes_remainder BOOLEAN)")
    if rows:
        con.executemany("INSERT INTO gl_map VALUES (?,?,?,?)", rows)
    con.execute("""
        CREATE OR REPLACE TABLE tb_alloc AS
        WITH base AS (
            SELECT t.branch_code, t.gl_code, t.gl_name, m.code, m.share, m.takes_remainder,
                   CAST(t.debit - t.credit AS DECIMAL(38,4)) AS signed
            FROM trial_balance t JOIN gl_map m USING (gl_code)
        ),
        shares AS (
            SELECT *, CAST(round(signed * share, 4) AS DECIMAL(38,4)) AS part FROM base
        )
        SELECT branch_code, gl_code, gl_name, code,
               CAST(CASE WHEN takes_remainder
                    THEN signed - (sum(CASE WHEN takes_remainder THEN 0 ELSE part END)
                                   OVER (PARTITION BY branch_code, gl_code))
                    ELSE part END AS DECIMAL(38,4)) AS amount
        FROM shares
    """)
    con.execute("CREATE OR REPLACE TABLE codes (code VARCHAR, label VARCHAR, normal VARCHAR, grp VARCHAR, rw VARCHAR)")
    con.executemany("INSERT INTO codes VALUES (?,?,?,?,?)",
                    [(c.code, c.label, c.normal, c.group, c.rw) for c in mapping.codes.values()])
    con.execute("""
        CREATE OR REPLACE TABLE gold AS
        SELECT c.code, c.label, c.normal, c.grp, c.rw,
               CAST(coalesce(sum(a.amount), 0) AS DECIMAL(38,4)) AS signed_amount,
               CAST(CASE WHEN c.normal = 'DEBIT' THEN coalesce(sum(a.amount), 0)
                         ELSE -coalesce(sum(a.amount), 0) END AS DECIMAL(38,4)) AS presented,
               count(a.amount) AS source_count
        FROM codes c LEFT JOIN tb_alloc a USING (code)
        GROUP BY c.code, c.label, c.normal, c.grp, c.rw ORDER BY c.code
    """)
    report.unmapped = [
        {"gl_code": g, "gl_name": n, "signed_amount": str(a), "rows": k}
        for g, n, a, k in con.execute("""
            SELECT gl_code, any_value(gl_name), sum(debit - credit), count(*)
            FROM trial_balance WHERE gl_code NOT IN (SELECT gl_code FROM gl_map)
            GROUP BY gl_code ORDER BY abs(sum(debit - credit)) DESC""").fetchall()
    ]
    report.abnormal = [
        {"code": c, "label": lbl, "presented": str(p)}
        for c, lbl, p in con.execute("SELECT code, label, presented FROM gold WHERE presented < 0").fetchall()
    ]
    report.mapped_accounts = len({r[0] for r in rows})
    return report
