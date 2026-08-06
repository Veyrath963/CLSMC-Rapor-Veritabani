from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import struct
import time
from collections import defaultdict, deque


def generate_csrf_token(session) -> str:
    token = session.get("_csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["_csrf_token"] = token
    return token


def validate_csrf_token(session, submitted: str | None) -> bool:
    expected = session.get("_csrf_token", "")
    return bool(expected and submitted and hmac.compare_digest(expected, submitted))


class AttemptLimiter:
    """Small process-local limiter used in addition to persistent account locks."""

    def __init__(self, limit: int = 8, window_seconds: int = 900):
        self.limit = limit
        self.window_seconds = window_seconds
        self._attempts: dict[str, deque[float]] = defaultdict(deque)

    def _trim(self, key: str, now: float) -> deque[float]:
        values = self._attempts[key]
        cutoff = now - self.window_seconds
        while values and values[0] < cutoff:
            values.popleft()
        return values

    def blocked(self, key: str) -> bool:
        now = time.time()
        return len(self._trim(key, now)) >= self.limit

    def record(self, key: str) -> None:
        now = time.time()
        self._trim(key, now).append(now)

    def clear(self, key: str) -> None:
        self._attempts.pop(key, None)


def generate_totp_secret() -> str:
    return base64.b32encode(secrets.token_bytes(20)).decode("ascii").rstrip("=")


def _decode_secret(secret: str) -> bytes:
    clean = "".join((secret or "").strip().upper().split())
    padding = "=" * ((8 - len(clean) % 8) % 8)
    return base64.b32decode(clean + padding, casefold=True)


def totp_code(secret: str, timestamp: int | None = None, period: int = 30) -> str:
    timestamp = int(time.time() if timestamp is None else timestamp)
    counter = timestamp // period
    digest = hmac.new(_decode_secret(secret), struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    value = (struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF) % 1_000_000
    return f"{value:06d}"


def verify_totp(secret: str, submitted: str | None, window: int = 1) -> bool:
    code = "".join(ch for ch in (submitted or "") if ch.isdigit())
    if len(code) != 6 or not secret:
        return False
    now = int(time.time())
    return any(hmac.compare_digest(totp_code(secret, now + offset * 30), code) for offset in range(-window, window + 1))
