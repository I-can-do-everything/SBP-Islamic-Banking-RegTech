"""Error types that carry a message safe to show to users."""

from __future__ import annotations


class DaleelError(Exception):
    """Base error. `code` is stable and machine readable, `message` is for people."""

    status = 400

    def __init__(self, code: str, message: str, details: dict | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}


class NotFound(DaleelError):
    status = 404


class Forbidden(DaleelError):
    status = 403


class InvalidInput(DaleelError):
    status = 422
