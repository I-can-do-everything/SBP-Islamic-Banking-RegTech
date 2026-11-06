"""Four eyes approval: the database enforces every rule, and the API journey works end to end."""

from __future__ import annotations

from uuid import uuid4

import psycopg
import pytest
from fastapi.testclient import TestClient

from daleel.db.database import workspace_tx


def _setup():
    """A workspace with three people and one READY submission that has two breaches."""
    ws = uuid4()
    with workspace_tx(ws) as conn:
        conn.execute("INSERT INTO workspace (id) VALUES (%s)", (ws,))
        people = {}
        for name, role in (("prep", "PREPARER"), ("appr", "APPROVER"), ("admin", "ADMIN")):
            people[name] = conn.execute(
                "INSERT INTO workspace_member (workspace_id, display_name, title, role) VALUES (%s,%s,%s,%s)"
                " RETURNING id", (ws, name, name, role)).fetchone()["id"]
        sub = conn.execute("INSERT INTO submission (workspace_id, institution, status, created_by)"
                           " VALUES (%s, 'T', 'READY', %s) RETURNING id", (ws, people["prep"])).fetchone()["id"]
        for metric_id, status in (("cap.car", "PASS"), ("pool.mudarib_share_max", "FAIL")):
            conn.execute("INSERT INTO metric_result (workspace_id, submission_id, metric_id, category, label, unit,"
                         " value, status, detail, sort_order) VALUES (%s,%s,%s,'c','l','percent',1,%s,'{}',0)",
                         (ws, sub, metric_id, status))
        conn.execute("INSERT INTO validation_result (workspace_id, submission_id, check_id, category, label, status,"
                     " message, evidence, rule_refs, sort_order) VALUES (%s,%s,'shariah.charity','s','l','FAIL','m',"
                     "'{}','[]',0)", (ws, sub))
    return ws, sub, people


def _act(ws, sub, who, action, comment=None):
    with workspace_tx(ws) as conn:
        conn.execute("INSERT INTO approval (workspace_id, submission_id, action, actor_id, comment)"
                     " VALUES (%s,%s,%s,%s,%s)", (ws, sub, action, who, comment))


def _explain(ws, sub, who, item):
    with workspace_tx(ws) as conn:
        conn.execute("INSERT INTO review_note (workspace_id, submission_id, author_id, item_id, kind, body)"
                     " VALUES (%s,%s,%s,%s,'explanation','Reviewed with treasury; correction planned.')",
                     (ws, sub, who, item))


def _status(ws, sub):
    with workspace_tx(ws) as conn:
        return conn.execute("SELECT workflow_status, locked FROM submission WHERE id = %s", (sub,)).fetchone()


def refused(fn, *args, match: str):
    with pytest.raises(psycopg.errors.RaiseException, match=match):
        fn(*args)


def test_database_enforces_four_eyes():
    ws, sub, p = _setup()
    refused(_act, ws, sub, p["appr"], "SUBMIT", match="Only a preparer")
    refused(_act, ws, sub, p["prep"], "SUBMIT", match="2 still missing")
    _explain(ws, sub, p["prep"], "pool.mudarib_share_max")
    refused(_act, ws, sub, p["prep"], "SUBMIT", match="1 still missing")
    _explain(ws, sub, p["prep"], "shariah.charity")
    _act(ws, sub, p["prep"], "SUBMIT")
    assert _status(ws, sub)["workflow_status"] == "SUBMITTED"
    refused(_explain, ws, sub, p["prep"], "shariah.charity", match="frozen|with the approver")
    refused(_act, ws, sub, p["prep"], "APPROVE", match="Only an approver")
    refused(_act, ws, sub, p["appr"], "REJECT", match="needs a reason")
    _act(ws, sub, p["appr"], "REJECT", "Please attach the treasury memo.")
    assert _status(ws, sub)["workflow_status"] == "REJECTED"
    # The administrator resubmits, so the administrator may not decide (four eyes).
    _act(ws, sub, p["admin"], "SUBMIT")
    refused(_act, ws, sub, p["admin"], "APPROVE", match="Four eyes rule")
    # Results change after submission: approval refused.
    with workspace_tx(ws) as conn:
        conn.execute("UPDATE metric_result SET value = 2 WHERE submission_id = %s AND metric_id = 'cap.car'", (sub,))
    refused(_act, ws, sub, p["appr"], "APPROVE", match="changed after they were submitted")
    with workspace_tx(ws) as conn:
        conn.execute("UPDATE metric_result SET value = 1 WHERE submission_id = %s AND metric_id = 'cap.car'", (sub,))
    _act(ws, sub, p["appr"], "APPROVE")
    assert dict(_status(ws, sub)) == {"workflow_status": "APPROVED", "locked": True}


def test_approved_submission_is_locked_and_history_is_append_only():
    ws, sub, p = _setup()
    for item in ("pool.mudarib_share_max", "shariah.charity"):
        _explain(ws, sub, p["prep"], item)
    _act(ws, sub, p["prep"], "SUBMIT")
    _act(ws, sub, p["appr"], "APPROVE")
    with pytest.raises(psycopg.errors.RaiseException, match="locked"), workspace_tx(ws) as conn:
        conn.execute("UPDATE metric_result SET value = 9 WHERE submission_id = %s", (sub,))
    with pytest.raises(psycopg.errors.RaiseException, match="locked"), workspace_tx(ws) as conn:
        conn.execute("UPDATE submission SET locked = false WHERE id = %s", (sub,))
    with pytest.raises(psycopg.errors.RaiseException, match="append only"), workspace_tx(ws) as conn:
        conn.execute("DELETE FROM approval WHERE submission_id = %s", (sub,))
    refused(_explain, ws, sub, p["prep"], "shariah.charity", match="locked")


def test_review_journey_through_the_api():
    from daleel.api.app import app
    from daleel.pipeline.queue import run_one

    client = TestClient(app)
    token = client.post("/api/v1/session").json()["token"]
    auth = {"Authorization": f"Bearer {token}"}
    me = client.get("/api/v1/me", headers=auth).json()
    assert me["role"] == "PREPARER" and len(me["members"]) == 3
    sub = client.post("/api/v1/submissions", headers=auth, data={"sample": "stressed"}).json()["id"]
    while run_one():
        pass  # ingest, calculate, narrate (AI off in tests)
    review = client.get(f"/api/v1/submissions/{sub}/review", headers=auth).json()
    assert review["workflow_status"] == "DRAFT" and len(review["breaches"]) == 8
    assert review["allowed"]["submit"] is False and "8 still missing" in review["blocked_reason"]["submit"]

    response = client.post(f"/api/v1/submissions/{sub}/submit", headers=auth)
    assert response.status_code == 409 and "explanation" in response.json()["title"]

    for b in review["breaches"]:
        r = client.post(f"/api/v1/submissions/{sub}/notes", headers=auth,
                        json={"kind": "explanation", "item_id": b["id"], "body": "Known issue; fix booked for October."})
        assert r.status_code == 200
    assert client.post(f"/api/v1/submissions/{sub}/submit", headers=auth, json={}).status_code == 200

    # The preparer cannot approve their own work.
    assert client.post(f"/api/v1/submissions/{sub}/approve", headers=auth, json={"confirm": True}).status_code == 409

    approver = next(m for m in me["members"] if m["role"] == "APPROVER")
    token2 = client.post("/api/v1/session/switch", headers=auth, json={"member_id": approver["id"]}).json()["token"]
    auth2 = {"Authorization": f"Bearer {token2}"}
    assert client.get(f"/api/v1/submissions/{sub}/review", headers=auth2).json()["allowed"]["approve"] is True
    assert client.post(f"/api/v1/submissions/{sub}/approve", headers=auth2, json={}).status_code == 422
    ok = client.post(f"/api/v1/submissions/{sub}/approve", headers=auth2, json={"confirm": True, "comment": "Agreed."})
    assert ok.status_code == 200
    final = client.get(f"/api/v1/submissions/{sub}/review", headers=auth2).json()
    assert final["workflow_status"] == "APPROVED" and final["locked"] is True
    assert [h["action"] for h in final["history"]] == ["SUBMIT", "APPROVE"]
    assert final["history"][1]["results_digest"] == final["submitted_digest"]
    assert client.get("/api/v1/audit/verify", headers=auth2).json()["valid"] is True
