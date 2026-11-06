"""A small job queue stored in PostgreSQL (DEC-003).

Why not Celery or Redis: the queue lives in the same database as the data, so a
submission and its processing job are created in one transaction. There is no
extra service to run, which keeps the free demo deployment simple.

How a worker takes a job without two workers taking the same one:
`SELECT ... FOR UPDATE SKIP LOCKED` locks the first ready row and makes other
workers skip it instead of waiting.
"""

from __future__ import annotations

import json
import logging
import threading
import time
import traceback
from collections.abc import Callable
from uuid import UUID

import psycopg

from daleel.db.database import system_tx

log = logging.getLogger("daleel.queue")

Handler = Callable[[UUID, dict], None]
_handlers: dict[str, Handler] = {}

MAX_ATTEMPTS = 2

# A job still marked running after this long belongs to a worker that died, for
# example when the free host restarted mid job (BUG-060). It goes back in the
# queue, or fails if it has used its attempts. Comfortably longer than the
# slowest AI run (several models, each with its own timeout).
STALE_AFTER = "15 minutes"


def handler(kind: str) -> Callable[[Handler], Handler]:
    def register(fn: Handler) -> Handler:
        _handlers[kind] = fn
        return fn

    return register


def enqueue(conn: psycopg.Connection, kind: str, workspace_id: UUID | str, payload: dict) -> int:
    """Add a job inside the caller's transaction (the transactional outbox, CON-091)."""
    row = conn.execute(
        "INSERT INTO job (kind, workspace_id, payload) VALUES (%s, %s, %s) RETURNING id",
        (kind, str(workspace_id), json.dumps(payload)),
    ).fetchone()
    conn.execute("SELECT pg_notify('daleel_jobs', %s)", (str(row["id"]),))
    return row["id"]


# The slow AI step runs in its own lane (BUG-059). A free model can take minutes,
# and with one shared worker that wait blocked every other upload behind it.
AI_KINDS = ("narrate",)


def _claim(kinds: tuple[str, ...] | None = None, exclude: tuple[str, ...] = ()) -> dict | None:
    """Lock the oldest ready job. `kinds` limits the lane to those job kinds;
    `exclude` keeps kinds out of it. Both empty means any job."""
    where = "status = 'queued' AND run_after <= now()"
    params: list = []
    if kinds:
        where += " AND kind = ANY(%s)"
        params.append(list(kinds))
    if exclude:
        where += " AND NOT (kind = ANY(%s))"
        params.append(list(exclude))
    with system_tx() as conn:
        conn.execute(
            "UPDATE job SET status = CASE WHEN attempts >= %s THEN 'failed' ELSE 'queued' END,"
            " error = 'Worker stopped while running this job', locked_at = NULL"
            " WHERE status = 'running' AND locked_at < now() - %s::interval",
            (MAX_ATTEMPTS, STALE_AFTER),
        )
        row = conn.execute(
            "SELECT id, kind, workspace_id, payload, attempts FROM job"
            f" WHERE {where} ORDER BY id FOR UPDATE SKIP LOCKED LIMIT 1",
            params,
        ).fetchone()
        if row is None:
            return None
        conn.execute(
            "UPDATE job SET status = 'running', locked_at = now(), attempts = attempts + 1"
            " WHERE id = %s",
            (row["id"],),
        )
        return row


def _finish(job_id: int, error: str | None, attempts: int) -> None:
    with system_tx() as conn:
        if error is None:
            conn.execute("UPDATE job SET status = 'done', error = NULL WHERE id = %s", (job_id,))
        elif attempts < MAX_ATTEMPTS:
            conn.execute(
                "UPDATE job SET status = 'queued', error = %s,"
                " run_after = now() + interval '5 seconds' WHERE id = %s",
                (error, job_id),
            )
        else:
            conn.execute("UPDATE job SET status = 'failed', error = %s WHERE id = %s", (error, job_id))


def run_one(kinds: tuple[str, ...] | None = None, exclude: tuple[str, ...] = ()) -> bool:
    """Process one ready job in the given lane. Returns False when the lane is empty."""
    job = _claim(kinds, exclude)
    if job is None:
        return False
    fn = _handlers.get(job["kind"])
    error = None
    try:
        if fn is None:
            raise RuntimeError(f"No handler for job kind {job['kind']}")
        fn(job["workspace_id"], job["payload"])
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}\n{traceback.format_exc(limit=5)}"
        log.exception("job %s failed", job["id"])
    _finish(job["id"], error, job["attempts"] + 1)
    return True


class Worker:
    """Polls the queue in a background thread. Several can run at once safely.

    `kinds` and `exclude` choose the lane, as in `_claim`."""

    def __init__(self, poll_seconds: float = 0.5, kinds: tuple[str, ...] | None = None,
                 exclude: tuple[str, ...] = (), name: str = "daleel-worker"):
        self.poll_seconds = poll_seconds
        self.kinds = kinds
        self.exclude = exclude
        self.name = name
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._thread = threading.Thread(target=self._loop, name=self.name, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=10)

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                busy = run_one(self.kinds, self.exclude)
            except Exception:
                log.exception("worker loop error")
                busy = False
            if not busy:
                time.sleep(self.poll_seconds)


def lanes() -> list[Worker]:
    """The two workers a process runs: one for ingest and calculation, one for AI."""
    return [
        Worker(exclude=AI_KINDS, name="daleel-worker-core"),
        Worker(kinds=AI_KINDS, name="daleel-worker-ai"),
    ]
