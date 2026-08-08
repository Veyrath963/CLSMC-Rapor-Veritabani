from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import struct
import time
from collections import defaultdict, deque
from io import BytesIO
from urllib.parse import quote, urlencode


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


def build_totp_provisioning_uri(
    secret: str,
    account_name: str,
    issuer: str = "CLSMC Medical Center",
) -> str:
    """Build an RFC-compatible otpauth URI for authenticator applications."""
    clean_secret = "".join((secret or "").strip().upper().split())
    clean_account = (account_name or "").strip()
    clean_issuer = (issuer or "CLSMC Medical Center").strip()
    if not clean_secret or not clean_account:
        raise ValueError("TOTP secret and account name are required.")

    label = quote(f"{clean_issuer}:{clean_account}", safe="")
    query = urlencode({
        "secret": clean_secret,
        "issuer": clean_issuer,
        "algorithm": "SHA1",
        "digits": "6",
        "period": "30",
    })
    return f"otpauth://totp/{label}?{query}"


def generate_qr_svg_data_uri(payload: str) -> str:
    """Generate a self-contained SVG QR code without any external QR service."""
    if not payload:
        raise ValueError("QR payload is required.")

    import qrcode
    from qrcode.image.svg import SvgPathImage

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=4,
    )
    qr.add_data(payload)
    qr.make(fit=True)
    image = qr.make_image(image_factory=SvgPathImage)
    output = BytesIO()
    image.save(output)
    encoded = base64.b64encode(output.getvalue()).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"


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


def verify_totp(
    secret: str,
    submitted: str | None,
    window: int = 1,
    at_time: int | None = None,
) -> bool:
    code = "".join(ch for ch in (submitted or "") if ch.isdigit())
    if len(code) != 6 or not secret:
        return False
    now = int(time.time() if at_time is None else at_time)
    for offset in range(-window, window + 1):
        candidate_time = now + offset * 30
        if candidate_time < 0:
            continue
        if hmac.compare_digest(totp_code(secret, candidate_time), code):
            return True
    return False
