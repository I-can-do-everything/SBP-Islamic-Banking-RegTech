"""Mapping, credit engine and metric tests, including golden results for both scenarios."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import duckdb
from hypothesis import given
from hypothesis import strategies as st

from daleel.mapping.mapper import Rule
from daleel.metrics.credit import enrich_contracts
from daleel.rulebook.rulebook import load_rulebook


def test_bug018_full_match_only():
    rule = Rule(0, "3590-MUR", (("A.FIN_MUR", Decimal(100)),))
    assert rule.matches("3590-MUR")
    assert not rule.matches("3590-MUR-NPF-001")


@given(st.decimals(min_value=Decimal("-1e12"), max_value=Decimal("1e12"), places=4, allow_nan=False),
       st.lists(st.integers(min_value=1, max_value=97), min_size=2, max_size=5))
def test_bug019_apportionment_conserves_total(amount, weights):
    """Property: an apportioned amount always adds back to the original, to the last 0.0001."""
    total_w = sum(weights)
    shares = [Decimal(w) / total_w for w in weights]
    shares[-1] = Decimal(1) - sum(shares[:-1])
    con = duckdb.connect()
    con.execute("CREATE TABLE s (share DECIMAL(18,10), rem BOOLEAN)")
    largest = max(range(len(shares)), key=lambda i: shares[i])
    con.executemany("INSERT INTO s VALUES (?, ?)", [(sh, i == largest) for i, sh in enumerate(shares)])
    total = con.execute("""
        WITH p AS (SELECT rem, CAST(round(CAST(? AS DECIMAL(38,4)) * share, 4) AS DECIMAL(38,4)) AS part FROM s)
        SELECT sum(CASE WHEN rem THEN CAST(? AS DECIMAL(38,4)) - (SELECT sum(part) FROM p WHERE NOT rem)
                        ELSE part END) FROM p""", [amount, amount]).fetchone()[0]
    assert total == amount


def test_classification_follows_annexure_c():
    con = duckdb.connect()
    con.execute("""CREATE TABLE f AS SELECT * FROM (VALUES
        ('C1','CORPORATE','CORPORATE',100.0,90,0.0,0.01,0.1,0.45),
        ('H1','HOUSING','MORTGAGE',100.0,90,0.0,0.01,0.1,0.25),
        ('A1','AGRI_PRODUCTION','RETAIL',100.0,364,0.0,0.01,0.1,0.5),
        ('P1','CONSUMER_PERSONAL','RETAIL',100.0,180,0.0,NULL,NULL,NULL))
        t(contract_id, portfolio, counterparty_type, outstanding, days_past_due, collateral_fsv, pd_12m, pd_lifetime, lgd)""")
    con.execute("CREATE TABLE fin AS SELECT contract_id, portfolio, counterparty_type, "
                "CAST(outstanding AS DECIMAL(38,4)) outstanding, days_past_due, CAST(collateral_fsv AS DECIMAL(38,4)) "
                "collateral_fsv, CAST(pd_12m AS DECIMAL(18,10)) pd_12m, CAST(pd_lifetime AS DECIMAL(18,10)) pd_lifetime,"
                " CAST(lgd AS DECIMAL(18,10)) lgd FROM f")
    enrich_contracts(con, "fin", load_rulebook(), date(2026, 9, 30))
    rows = {r[0]: r[1:] for r in con.execute(
        "SELECT contract_id, classification, stage, ecl, pr_required, provision_required FROM contracts").fetchall()}
    assert rows["C1"][:2] == ("SUBSTANDARD", 3)
    assert rows["H1"][:2] == ("OAEM", 2)          # housing OAEM at 90 to 179 days is Stage 2
    assert rows["A1"][:2] == ("OAEM", 2)          # agriculture OAEM runs to 364 days
    assert rows["P1"][:2] == ("LOSS", 3)          # personal loans are Loss from 180 days
    c1 = rows["C1"]
    assert c1[4] == max(c1[2], c1[3])             # Stage 3: higher of ECL and PR provision


def _by_id(result):
    return {m.id: m for m in result.metrics}, {c.id: c for c in result.checks}


def test_baseline_golden(baseline):
    _, result = baseline
    metrics, checks = _by_id(result)
    assert checks["integrity.tb_balanced"].status == "PASS"
    assert checks["recon.financing"].status == "PASS"
    assert checks["recon.deposits"].status == "PASS"
    assert checks["integrity.unmapped"].status == "WARNING"          # planted new product account
    assert metrics["cap.car"].status == "PASS" and Decimal(17) < metrics["cap.car"].value < Decimal(22)
    assert metrics["pool.savings_lowest_rate"].status == "PASS"
    fails = [m.id for m in result.metrics if m.status == "FAIL"] + [c.id for c in result.checks if c.status == "FAIL"]
    assert fails == []


def test_stressed_detects_every_planted_breach(stressed):
    _, result = stressed
    metrics, _ = _by_id(result)
    fails = {m.id for m in result.metrics if m.status == "FAIL"} | {c.id for c in result.checks if c.status == "FAIL"}
    assert fails == {"aq.provision_gap", "pool.savings_lowest_rate", "pool.mudarib_share_max",
                     "pool.per_contribution_max", "pool.irr_contribution_max", "pool.weightage_notice",
                     "recon.deposits", "shariah.charity_not_income"}
    assert metrics["cap.car"].status == "WARNING"                     # inside the conservation buffer


def test_wagy_excludes_scf_and_omo(stressed):
    _, result = stressed
    table = {m.id: m for m in result.metrics}["pool.wagy"].table
    excluded = {row[0] for row in table["rows"] if row[5] == "yes"}
    assert excluded == {"SCF-01", "OMO-01"}


def test_every_metric_has_lineage(baseline):
    _, result = baseline
    for m in result.metrics:
        if m.status != "NOT_AVAILABLE":
            assert m.formula, m.id
    rules = {r["rule_id"]: r for m in result.metrics for r in m.rules}
    assert rules["pools.savings_min_share_of_wagy"]["source"]["verification"] == "primary"


def test_rulebook_effective_dates():
    book = load_rulebook()
    assert book.value("capital.ccb", date(2019, 12, 31)) == Decimal("2.5")
    assert book.value("capital.ccb", date(2026, 9, 30)) == Decimal("1.5")
    assert book.value("pools.wagy_excludes_fixed_assets", date(2025, 1, 10)) == 1
    assert book.value("pools.wagy_excludes_fixed_assets", date(2026, 9, 30)) == 0
