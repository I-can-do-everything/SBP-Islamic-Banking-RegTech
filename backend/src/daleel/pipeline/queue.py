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


def _claim() -> dict | None:
    with system_tx() as conn:
        row = conn.execute(
            "SELECT id, kind, workspace_id, payload, attempts FROM job"
            " WHERE status = 'queued' AND run_after <= now()"
            " ORDER BY id FOR UPDATE SKIP LOCKED LIMIT 1"
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


def run_one() -> bool:
    """Process one ready job. Returns False when the queue is empty."""
    job = _claim()
    if job is None:
        return False
    fn = _handlers.get(job["kind"])
    error = None
    try:
        if fn is None:
            raise RuntimeError(f"No handler for job kind {job['kind']}")
        fn(job["workspace_id"], job["payload"])
    except Exception as exc:  # noqa: BLE001 (any failure is recorded on the job)
        error = f"{type(exc).__name__}: {exc}\n{traceback.format_exc(limit=5)}"
        log.exception("job %s failed", job["id"])
    _finish(job["id"], error, job["attempts"] + 1)
    return True


class Worker:
    """Polls the queue in a background thread. Several can run at once safely."""

    def __init__(self, poll_seconds: float = 0.5):
        self.poll_seconds = poll_seconds
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._thread = threading.Thread(target=self._loop, name="daleel-worker", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=10)

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                busy = run_one()
            except Exception:  # noqa: BLE001
                log.exception("worker loop error")
                busy = False
            if not busy:
                time.sleep(self.poll_seconds)
