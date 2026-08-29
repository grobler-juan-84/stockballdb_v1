"""Sanitize snapshot and manifest metadata — never persist secrets."""

from __future__ import annotations

import re
from typing import Any

SECRET_KEY_PATTERNS = (
    re.compile(r"api[_-]?key", re.I),
    re.compile(r"^token$", re.I),
    re.compile(r"authorization", re.I),
    re.compile(r"password", re.I),
    re.compile(r"secret", re.I),
    re.compile(r"credential", re.I),
    re.compile(r"database[_-]?url", re.I),
)

SECRET_VALUE_PATTERNS = (
    re.compile(r"postgresql\+psycopg://[^@]+@", re.I),
    re.compile(r"Token\s+[A-Za-z0-9]+", re.I),
)


def is_secret_key(key: str) -> bool:
    return any(p.search(key) for p in SECRET_KEY_PATTERNS)


def sanitize_request_identity(data: dict[str, Any]) -> dict[str, Any]:
    """Return a copy with secret-like keys removed."""

    def walk(obj: Any) -> Any:
        if isinstance(obj, dict):
            out: dict[str, Any] = {}
            for k, v in obj.items():
                if is_secret_key(k):
                    continue
                out[k] = walk(v)
            return out
        if isinstance(obj, list):
            return [walk(v) for v in obj]
        if isinstance(obj, str):
            for pat in SECRET_VALUE_PATTERNS:
                if pat.search(obj):
                    raise ValueError("request_identity contains secret-like value")
        return obj

    return walk(data)


def scan_object_for_secrets(obj: Any, path: str = "") -> list[str]:
    """Return dotted paths of secret-like keys (Phase 8 compatible)."""
    hits: list[str] = []

    def walk(value: Any, p: str) -> None:
        if isinstance(value, dict):
            for k, v in value.items():
                np = f"{p}.{k}" if p else k
                if is_secret_key(k):
                    hits.append(np)
                walk(v, np)
        elif isinstance(value, list):
            for i, v in enumerate(value):
                walk(v, f"{p}[{i}]")

    walk(obj, path)
    return hits
