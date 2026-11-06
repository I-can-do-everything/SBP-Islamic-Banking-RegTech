"""Review and four eyes approval endpoints.

The rules themselves live in the database (migrations/0003_four_eyes.sql), so
these endpoints are thin: they record the request, and any rule the database
refuses comes back as a 409 with the database's own plain message. The screen
also explains in advance what is allowed (`allowed` and `blocked_reason`), but
that is only a convenience; the database is the authority.
"""

from __future__ import annotations

from uuid import UUID

import psycopg
from fastapi import APIRouter, Depends

from daleel.api.security import Session, SessionDep, review_limit
from daleel.core.errors import DaleelError, InvalidInput, NotFound
from daleel.db.database import workspace_tx
from daleel.pipeline.jobs import audit

router = APIRouter(prefix="/api/v1/submissions/{sub}", tags=["review"])


class Conflict(DaleelError):
    status = 409


def _rule_error(exc: psycopg.Error) -> Conflict:
    message = (exc.diag.message_primary if exc.diag else None) or "This action is not allowed."
    return Conflict("not_allowed", message)


def _members(conn) -> dict:
    return {r["id"]: r for r in conn.execute("SELECT id, display_name, title, role FROM workspace_member")}


def _who(members: dict, member_id) -> dict | None:
    m = members.get(member_id)
    return None if m is None else {"id": str(m["id"]), "name": m["display_name"], "role": m["role"]}


def _breaches(conn, sub: UUID) -> list[dict]:
    rows = conn.execute("""
        SELECT metric_id AS id, label, category, 'metric' AS kind FROM metric_result
         WHERE submission_id = %s AND status = 'FAIL'
        UNION ALL
        SELECT check_id, label, category, 'check' FROM validation_result
         WHERE submission_id = %s AND status = 'FAIL'
        ORDER BY 3, 2""", (sub, sub)).fetchall()
    return [dict(r) for r in rows]


def _blocked_reason(session: Session, s: dict, breaches: list[dict], explained: set[str]) -> dict:
    """Explain in advance why an action would be refused (the database enforces it either way)."""
    reasons: dict[str, str | None] = {"submit": None, "approve": None, "reject": None, "note": None}
    if s["status"] != "READY":
        for k in reasons:
            reasons[k] = "The results are not ready yet."
        return reasons
    if s["locked"]:
        for k in reasons:
            reasons[k] = "Approved and locked."
        return reasons
    missing = [b for b in breaches if b["id"] not in explained]
    if session.role not in ("PREPARER", "ADMIN"):
        reasons["submit"] = "Only a preparer can submit."
    elif s["workflow_status"] not in ("DRAFT", "REJECTED"):
        reasons["submit"] = f"Already {s['workflow_status'].lower()}."
    elif missing:
        reasons["submit"] = f"Explain every breach first ({len(missing)} still missing)."
    for action in ("approve", "reject"):
        if session.role not in ("APPROVER", "ADMIN"):
            reasons[action] = "Only an approver can decide."
        elif s["workflow_status"] != "SUBMITTED":
            reasons[action] = "Waiting for the preparer to submit."
        elif session.member_id in (s["submitted_by"], s["created_by"]):
            reasons[action] = "Four eyes rule: you prepared or submitted this, so someone else must decide."
    if s["workflow_status"] == "SUBMITTED":
        reasons["note"] = "Explanations are frozen while the submission is with the approver."
    return reasons


@router.get("/review")
def get_review(sub: UUID, session: Session = SessionDep) -> dict:
    with workspace_tx(session.workspace_id) as conn:
        s = conn.execute("SELECT * FROM submission WHERE id = %s", (sub,)).fetchone()
        if s is None:
            raise NotFound("no_submission", "Submission not found.")
        members = _members(conn)
        breaches = _breaches(conn, sub)
        notes = conn.execute("SELECT * FROM review_note WHERE submission_id = %s ORDER BY created_at",
                             (sub,)).fetchall()
        actions = conn.execute("SELECT * FROM approval WHERE submission_id = %s ORDER BY id", (sub,)).fetchall()
        digest = conn.execute("SELECT submission_results_digest(%s) AS d", (sub,)).fetchone()["d"]
    explained = {n["item_id"] for n in notes if n["kind"] == "explanation"}
    latest: dict[str, dict] = {}
    for n in notes:
        if n["kind"] == "explanation":
            latest[n["item_id"]] = n
    blocked = _blocked_reason(session, s, breaches, explained)
    submitted_digest = next((a["results_digest"] for a in reversed(actions) if a["action"] == "SUBMIT"), None)
    return {
        "workflow_status": s["workflow_status"],
        "locked": s["locked"],
        "results_ready": s["status"] == "READY",
        "created_by": _who(members, s["created_by"]),
        "submitted_by": _who(members, s["submitted_by"]),
        "submitted_at": s["submitted_at"].isoformat() if s["submitted_at"] else None,
        "decided_by": _who(members, s["decided_by"]),
        "decided_at": s["decided_at"].isoformat() if s["decided_at"] else None,
        "results_digest": digest,
        "submitted_digest": submitted_digest,
        "you": {"id": str(session.member_id), "name": session.name, "role": session.role},
        "breaches": [{**b, "explanation": None if b["id"] not in latest else {
            "body": latest[b["id"]]["body"], "author": _who(members, latest[b["id"]]["author_id"]),
            "at": latest[b["id"]]["created_at"].isoformat()}} for b in breaches],
        "notes": [{"id": str(n["id"]), "item_id": n["item_id"], "kind": n["kind"], "body": n["body"],
                   "author": _who(members, n["author_id"]), "at": n["created_at"].isoformat()} for n in notes],
        "history": [{"id": a["id"], "action": a["action"], "actor": _who(members, a["actor_id"]),
                     "comment": a["comment"], "results_digest": a["results_digest"],
                     "at": a["created_at"].isoformat()} for a in actions],
        "allowed": {k: v is None for k, v in blocked.items()},
        "blocked_reason": blocked,
    }


def _act(session: Session, sub: UUID, action: str, comment: str | None) -> dict:
    try:
        with workspace_tx(session.workspace_id) as conn:
            row = conn.execute(
                "INSERT INTO approval (workspace_id, submission_id, action, actor_id, comment)"
                " VALUES (%s,%s,%s,%s,%s) RETURNING id, results_digest",
                (session.workspace_id, sub, action, session.member_id, (comment or "").strip() or None)).fetchone()
            audit(conn, session.workspace_id, session.name, f"review.{action.lower()}", f"submission/{sub}",
                  {"role": session.role, "comment": comment, "results_digest": row["results_digest"]})
    except psycopg.errors.RaiseException as exc:
        raise _rule_error(exc) from exc
    return {"ok": True, "results_digest": row["results_digest"]}


@router.post("/notes", dependencies=[Depends(review_limit)])
def add_note(sub: UUID, body: dict, session: Session = SessionDep) -> dict:
    kind = body.get("kind", "comment")
    text = str(body.get("body", "")).strip()
    if kind not in ("explanation", "comment"):
        raise InvalidInput("bad_kind", "A note is an explanation or a comment.")
    if len(text) < 3:
        raise InvalidInput("too_short", "Write at least a few words.")
    if kind == "explanation" and session.role not in ("PREPARER", "ADMIN"):
        raise Conflict("not_allowed", "Only a preparer explains breaches.")
    try:
        with workspace_tx(session.workspace_id) as conn:
            note = conn.execute(
                "INSERT INTO review_note (workspace_id, submission_id, author_id, item_id, kind, body)"
                " VALUES (%s,%s,%s,%s,%s,%s) RETURNING id",
                (session.workspace_id, sub, session.member_id, body.get("item_id"), kind, text[:4000])).fetchone()
            audit(conn, session.workspace_id, session.name, f"review.{kind}", f"submission/{sub}",
                  {"item_id": body.get("item_id")})
    except psycopg.errors.RaiseException as exc:
        raise _rule_error(exc) from exc
    except psycopg.errors.CheckViolation as exc:
        raise InvalidInput("bad_note", "The note is too short or too long.") from exc
    return {"id": str(note["id"])}


@router.post("/submit", dependencies=[Depends(review_limit)])
def submit(sub: UUID, body: dict | None = None, session: Session = SessionDep) -> dict:
    return _act(session, sub, "SUBMIT", (body or {}).get("comment"))


@router.post("/approve", dependencies=[Depends(review_limit)])
def approve(sub: UUID, body: dict | None = None, session: Session = SessionDep) -> dict:
    if not (body or {}).get("confirm"):
        raise InvalidInput("confirm", "Confirm that you reviewed the results and explanations.")
    return _act(session, sub, "APPROVE", (body or {}).get("comment"))


@router.post("/reject", dependencies=[Depends(review_limit)])
def reject(sub: UUID, body: dict | None = None, session: Session = SessionDep) -> dict:
    return _act(session, sub, "REJECT", (body or {}).get("comment"))
