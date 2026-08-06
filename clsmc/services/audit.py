from __future__ import annotations

import json

SENSITIVE_KEYS = {"password", "password_hash", "new_password", "secret", "totp_secret", "csrf"}


def sanitize_mapping(value):
    if value is None:
        return None
    if not isinstance(value, dict):
        return value
    cleaned = {}
    for key, item in value.items():
        lowered = str(key).casefold()
        cleaned[key] = "[GİZLENDİ]" if any(token in lowered for token in SENSITIVE_KEYS) else item
    return cleaned


def json_text(value) -> str | None:
    if value is None:
        return None
    return json.dumps(sanitize_mapping(value), ensure_ascii=False, default=str)
