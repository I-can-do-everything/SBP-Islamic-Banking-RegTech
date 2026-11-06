"""Demo sessions and simple rate limits.

The public demo has no sign up. Each visitor gets an anonymous workspace and a
signed token (HS256 JWT, 12 hours) that names it. Every request with that token
runs inside the workspace's row level security scope (DEC-012), so visitors can
never see each other's uploads.

Rate limits are kept in memory per client address, which is enough for a single
demo container. A multi instance deployment would move them to the database or
Valkey.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import jwt
from fastapi import Depends, Header, Request

from daleel.core.config import get_settings
from daleel.core.errors import DaleelError, Forbidden
from daleel.db.database import system_tx, workspace_tx


class TooManyRequests(DaleelError):
    status = 429


def create_workspace() -> tuple[UUID, str, datetime]:
    settings = get_settings()
    ws = uuid4()
    expires = datetime.now(UTC) + timedelta(hours=settings.session_hours)
    with workspace_tx(ws) as conn:
        conn.execute("INSERT INTO workspace (id, expires_at) VALUES (%s, %s)", (ws, expires + timedelta(days=1)))
        conn.execute("INSERT INTO audit_event (workspace_id, actor, action, resource, details)"
                     " VALUES (%s, 'visitor', 'session.created', %s, '{}')", (ws, f"workspace/{ws}"))
    with system_tx() as conn:
        conn.execute("INSERT INTO workspace_registry (id, expires_at) VALUES (%s, %s)",
                     (ws, expires + timedelta(days=1)))
    token = jwt.encode({"ws": str(ws), "exp": expires, "iat": datetime.now(UTC)},
                       settings.jwt_secret, algorithm="HS256")
    return ws, token, expires


def current_workspace(authorization: str = Header(default="")) -> UUID:
    if not authorization.lower().startswith("bearer "):
        raise Forbidden("no_session", "Start a demo session first.")
    try:
        claims = jwt.decode(authorization[7:], get_settings().jwt_secret, algorithms=["HS256"])
        return UUID(claims["ws"])
    except (jwt.PyJWTError, KeyError, ValueError) as exc:
        raise Forbidden("bad_session", "Your demo session has expired. Start a new one.") from exc


def token_from_query(token: str = "") -> UUID:
    """Browsers cannot set headers on EventSource or plain download links, so those pass ?token=."""
    return current_workspace(f"Bearer {token}")


class RateLimiter:
    def __init__(self, limit: int, seconds: int):
        self.limit, self.seconds = limit, seconds
        self.hits: dict[str, deque] = defaultdict(deque)
        self.lock = threading.Lock()

    def __call__(self, request: Request) -> None:
        key = request.client.host if request.client else "unknown"
        now = time.monotonic()
        with self.lock:
            q = self.hits[key]
            while q and now - q[0] > self.seconds:
                q.popleft()
            if len(q) >= self.limit:
                raise TooManyRequests("rate_limited", "Too many requests. Please wait a minute and try again.")
            q.append(now)


session_limit = RateLimiter(limit=10, seconds=3600)
upload_limit = RateLimiter(limit=12, seconds=3600)

WorkspaceDep = Depends(current_workspace)
