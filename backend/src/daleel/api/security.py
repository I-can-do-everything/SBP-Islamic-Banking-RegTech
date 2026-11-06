"""Demo sessions, people in a workspace, and simple rate limits.

The public demo has no sign up. Each visitor gets an anonymous workspace with
three people in it, so the four eyes approval can be tried by one visitor:

  Reporting Officer   PREPARER  uploads, explains breaches, submits
  Head of Compliance  APPROVER  approves or rejects
  Chief Risk Officer  ADMIN     can do both, but never on their own work

A signed token (HS256 JWT) names the workspace AND the person. Every request
runs inside the workspace's row level security scope (DEC-012). In demo mode
the visitor may switch person (DEMO_PERSONAS=true); in a real deployment each
person signs in separately and that switch is turned off.

Rate limits are kept in memory per client address, which is enough for a single
demo container. A multi instance deployment would move them to the database or
Valkey.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import jwt
from fastapi import Depends, Header, Request

from daleel.core.config import get_settings
from daleel.core.errors import DaleelError, Forbidden
from daleel.db.database import system_tx, workspace_tx

PERSONAS = (
    ("Reporting Officer", "Prepares and submits the return", "PREPARER"),
    ("Head of Compliance", "Reviews and approves", "APPROVER"),
    ("Chief Risk Officer", "Administrator: can prepare or approve, never both on one submission", "ADMIN"),
)


class TooManyRequests(DaleelError):
    status = 429


@dataclass(frozen=True)
class Session:
    workspace_id: UUID
    member_id: UUID
    role: str
    name: str


def _token(ws: UUID, member: UUID, role: str, name: str, expires: datetime) -> str:
    return jwt.encode({"ws": str(ws), "mid": str(member), "role": role, "name": name, "exp": expires,
                       "iat": datetime.now(UTC)}, get_settings().jwt_secret, algorithm="HS256")


def create_workspace() -> tuple[UUID, str, datetime]:
    settings = get_settings()
    ws = uuid4()
    expires = datetime.now(UTC) + timedelta(hours=settings.session_hours)
    with workspace_tx(ws) as conn:
        conn.execute("INSERT INTO workspace (id, expires_at) VALUES (%s, %s)", (ws, expires + timedelta(days=1)))
        members = [conn.execute(
            "INSERT INTO workspace_member (workspace_id, display_name, title, role) VALUES (%s,%s,%s,%s)"
            " RETURNING id, display_name, role", (ws, name, title, role)).fetchone() for name, title, role in PERSONAS]
        conn.execute("INSERT INTO audit_event (workspace_id, actor, action, resource, details)"
                     " VALUES (%s, 'visitor', 'session.created', %s, '{}')", (ws, f"workspace/{ws}"))
    with system_tx() as conn:
        conn.execute("INSERT INTO workspace_registry (id, expires_at) VALUES (%s, %s)",
                     (ws, expires + timedelta(days=1)))
    first = members[0]
    return ws, _token(ws, first["id"], first["role"], first["display_name"], expires), expires


def switch_member(session: Session, member_id: UUID) -> tuple[str, dict]:
    if not get_settings().demo_personas:
        raise Forbidden("switch_disabled", "Switching person is only available in demo mode.")
    with workspace_tx(session.workspace_id) as conn:
        m = conn.execute("SELECT id, display_name, title, role FROM workspace_member WHERE id = %s",
                         (member_id,)).fetchone()
        if m is None:
            raise Forbidden("no_member", "That person is not in this workspace.")
        conn.execute("INSERT INTO audit_event (workspace_id, actor, action, resource, details)"
                     " VALUES (%s, %s, 'session.switched_person', %s, '{}')",
                     (session.workspace_id, m["display_name"], f"member/{m['id']}"))
    expires = datetime.now(UTC) + timedelta(hours=get_settings().session_hours)
    return _token(session.workspace_id, m["id"], m["role"], m["display_name"], expires), dict(m)


def current_session(authorization: str = Header(default="")) -> Session:
    if not authorization.lower().startswith("bearer "):
        raise Forbidden("no_session", "Start a demo session first.")
    try:
        claims = jwt.decode(authorization[7:], get_settings().jwt_secret, algorithms=["HS256"])
        return Session(UUID(claims["ws"]), UUID(claims["mid"]), claims["role"], claims["name"])
    except (jwt.PyJWTError, KeyError, ValueError) as exc:
        raise Forbidden("bad_session", "Your demo session has expired. Start a new one.") from exc


def current_workspace(session: Session = Depends(current_session)) -> UUID:
    return session.workspace_id


def token_from_query(token: str = "") -> UUID:
    """Browsers cannot set headers on EventSource or plain download links, so those pass ?token=."""
    return current_session(f"Bearer {token}").workspace_id


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
review_limit = RateLimiter(limit=120, seconds=3600)

WorkspaceDep = Depends(current_workspace)
SessionDep = Depends(current_session)
