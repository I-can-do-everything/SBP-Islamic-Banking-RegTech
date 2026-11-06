"""Row level security, audit chain and the AI validator."""

from __future__ import annotations

from uuid import uuid4

import psycopg
import pytest

from daleel.ai.facts import Fact
from daleel.ai.narrative import _validate, generate_breakdown
from daleel.db.database import system_tx, workspace_tx


def _workspace():
    ws = uuid4()
    with workspace_tx(ws) as conn:
        conn.execute("INSERT INTO workspace (id) VALUES (%s)", (ws,))
        conn.execute("INSERT INTO submission (workspace_id, institution) VALUES (%s, 'T')", (ws,))
        for action in ("a", "b", "c"):
            conn.execute("INSERT INTO audit_event (workspace_id, actor, action) VALUES (%s, 't', %s)", (ws, action))
    return ws


def test_rls_isolates_workspaces():
    a, b = _workspace(), _workspace()
    with workspace_tx(a) as conn:
        ids = {r["workspace_id"] for r in conn.execute("SELECT workspace_id FROM submission")}
        assert ids == {a}
    with pytest.raises(psycopg.errors.InsufficientPrivilege), workspace_tx(a) as conn:
        conn.execute("INSERT INTO submission (workspace_id, institution) VALUES (%s, 'x')", (b,))
    with system_tx() as conn:
        assert conn.execute("SELECT count(*) AS n FROM submission").fetchone()["n"] == 0


def test_audit_chain_links_and_is_append_only():
    ws = _workspace()
    with workspace_tx(ws) as conn:
        rows = conn.execute("SELECT prev_hash, hash FROM audit_event ORDER BY id").fetchall()
    assert rows[0]["prev_hash"] is None
    assert all(rows[i]["prev_hash"] == rows[i - 1]["hash"] for i in range(1, len(rows)))
    with pytest.raises(psycopg.errors.RaiseException), workspace_tx(ws) as conn:
        conn.execute("UPDATE audit_event SET action = 'edited'")


FACTS = {
    "F1": Fact("F1", "Lowest savings tier profit rate", "9.10%, 0.45 percentage points below the 9.55% minimum",
               "FAIL", "metric", "pool.savings_lowest_rate", "Profit distribution"),
    "F2": Fact("F2", "Capital adequacy ratio (CAR)", "19.25%, 7.75 percentage points above the 11.50% requirement",
               "PASS", "metric", "cap.car", "Capital"),
}


def test_validator_rejects_digits_and_bad_citations():
    good = {"headline": "One breach needs action.", "points": [
        {"kind": "breach", "text": "The lowest savings tier rate is {F1}.", "fact_ids": ["F1"], "source_ids": ["S1"]}]}
    assert _validate(good, FACTS, {"S1": "IFPD"}, {"F1": ["S1"]}) == []
    digits = {"headline": "x", "points": [
        {"kind": "breach", "text": "The savings tier rate is 9.1%.", "fact_ids": ["F1"], "source_ids": []}]}
    assert any("digit" in p for p in _validate(digits, FACTS, {}, {}))
    unrelated_source = {"headline": "x", "points": [
        {"kind": "strength", "text": "Capital adequacy is {F2}.", "fact_ids": ["F2"], "source_ids": ["S1"]}]}
    assert any("does not relate" in p for p in _validate(unrelated_source, FACTS, {"S1": "IFPD"}, {"F1": ["S1"]}))
    contradiction = {"headline": "x", "points": [
        {"kind": "strength", "text": "The savings tier rate {F1} meets the rule.", "fact_ids": ["F1"], "source_ids": []}]}
    assert any("compliant" in p for p in _validate(contradiction, FACTS, {}, {}))
    renamed = {"headline": "x", "points": [
        {"kind": "breach", "text": "The industry contribution is {F1}.", "fact_ids": ["F1"], "source_ids": []}]}
    assert any("without naming it" in p for p in _validate(renamed, FACTS, {}, {}))


def test_template_covers_every_failure(stressed):
    _, result = stressed
    metrics = [{"id": m.id, "category": m.category, "label": m.label, "unit": m.unit,
                "value": None if m.value is None else str(m.value), "status": m.status, "detail": m.detail()}
               for m in result.metrics]
    checks = [{"id": c.id, "category": c.category, "label": c.label, "status": c.status, "message": c.message,
               "evidence": c.evidence, "rule_refs": c.rule_refs} for c in result.checks]
    b = generate_breakdown(metrics, checks, use_ai=False)
    assert b.source == "template"
    assert b.grounding["fails_total"] == 8
    cited = {f for p in b.points for f in p["fact_ids"]}
    fail_ids = {f["id"] for f in b.facts if f["status"] == "FAIL" and f["kind"] in ("metric", "check")}
    assert fail_ids <= cited
    assert all("{" not in p["rendered"] for p in b.points)
