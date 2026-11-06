"""Job queue lanes and stale job recovery (BUG-059, BUG-060).

Each test uses job kinds with a random suffix, so jobs left by a running dev
server never interfere and these jobs are never picked up by its workers.
"""

from __future__ import annotations

import json
from uuid import uuid4

from daleel.db.database import system_tx
from daleel.pipeline.queue import AI_KINDS, MAX_ATTEMPTS, _claim, lanes


def _kinds(n: int) -> list[str]:
    tag = uuid4().hex[:8]
    return [f"test-{i}-{tag}" for i in range(n)]


def _add(kind: str, status: str = "queued", attempts: int = 0, locked_ago: str | None = None) -> int:
    with system_tx() as conn:
        return conn.execute(
            "INSERT INTO job (kind, workspace_id, payload, status, attempts, locked_at)"
            " VALUES (%s, %s, %s, %s, %s, CASE WHEN %s::text IS NULL THEN NULL ELSE now() - %s::interval END)"
            " RETURNING id",
            (kind, str(uuid4()), json.dumps({}), status, attempts, locked_ago, locked_ago),
        ).fetchone()["id"]


def _cleanup(kinds: list[str]) -> None:
    with system_tx() as conn:
        conn.execute("DELETE FROM job WHERE kind = ANY(%s)", (kinds,))


def test_lanes_keep_slow_ai_jobs_apart():
    slow, fast = _kinds(2)
    try:
        _add(slow)  # older, so a single shared lane would take it first
        fast_id = _add(fast)
        # The core lane skips the slow kind even though it is older.
        job = _claim(kinds=(slow, fast), exclude=(slow,))
        assert job["id"] == fast_id
        # The AI lane only ever takes its own kinds.
        assert _claim(kinds=(fast,)) is None
        assert _claim(kinds=(slow,))["kind"] == slow
    finally:
        _cleanup([slow, fast])
    core, ai = lanes()
    assert core.exclude == AI_KINDS and core.kinds is None
    assert ai.kinds == AI_KINDS


def test_stale_running_job_is_requeued_or_failed():
    retry, spent, fresh = _kinds(3)
    try:
        retry_id = _add(retry, "running", attempts=1, locked_ago="1 hour")
        spent_id = _add(spent, "running", attempts=MAX_ATTEMPTS, locked_ago="1 hour")
        fresh_id = _add(fresh, "running", attempts=1, locked_ago="1 minute")
        job = _claim(kinds=(retry,))
        assert job["id"] == retry_id  # back in the queue and claimed again
        with system_tx() as conn:
            rows = {r["id"]: r for r in conn.execute(
                "SELECT id, status, error FROM job WHERE id = ANY(%s)", ([retry_id, spent_id, fresh_id],))}
        assert rows[retry_id]["status"] == "running"
        assert rows[spent_id]["status"] == "failed" and "Worker stopped" in rows[spent_id]["error"]
        assert rows[fresh_id]["status"] == "running"  # still within its time, left alone
    finally:
        _cleanup([retry, spent, fresh])
