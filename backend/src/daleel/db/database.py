"""Database access.

One connection pool for the process. Two ways to use it:

- `workspace_tx(workspace_id)`: a transaction scoped to one workspace. It sets
  `app.workspace_id` for the transaction only, so row level security filters
  every query to that workspace (DEC-012).
- `system_tx()`: a transaction with no workspace, for the job queue and the
  shared source text. Workspace tables return no rows here, by design.
"""

from __future__ import annotations

import atexit
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from uuid import UUID

import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from daleel.core.config import BACKEND_DIR, get_settings

_pool: ConnectionPool | None = None
_lock = threading.Lock()


def pool() -> ConnectionPool:
    global _pool
    with _lock:
        if _pool is None:
            _pool = ConnectionPool(
                get_settings().database_url,
                min_size=1,
                max_size=10,
                kwargs={"row_factory": dict_row, "autocommit": False},
                open=True,
            )
            atexit.register(close_pool)
        return _pool


def close_pool() -> None:
    global _pool
    if not _lock.acquire(timeout=5):
        return
    try:
        if _pool is not None:
            _pool.close()
            _pool = None
    finally:
        _lock.release()


@contextmanager
def workspace_tx(workspace_id: UUID | str) -> Iterator[psycopg.Connection]:
    with pool().connection() as conn, conn.transaction():
        conn.execute("SELECT set_config('app.workspace_id', %s, true)", (str(workspace_id),))
        yield conn


@contextmanager
def system_tx() -> Iterator[psycopg.Connection]:
    with pool().connection() as conn, conn.transaction():
        yield conn


def migrate() -> list[str]:
    """Apply SQL files in backend/migrations that have not run yet, in name order."""
    applied: list[str] = []
    migrations_dir: Path = BACKEND_DIR / "migrations"
    with pool().connection() as conn:
        with conn.transaction():
            conn.execute(
                "CREATE TABLE IF NOT EXISTS schema_migration ("
                " name text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now())"
            )
            done = {r["name"] for r in conn.execute("SELECT name FROM schema_migration")}
        for path in sorted(migrations_dir.glob("*.sql")):
            if path.name in done:
                continue
            with conn.transaction():
                conn.execute(path.read_text())
                conn.execute("INSERT INTO schema_migration (name) VALUES (%s)", (path.name,))
            applied.append(path.name)
    return applied
