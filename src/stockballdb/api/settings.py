"""HTTP transport settings (development defaults)."""

from __future__ import annotations

import os


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765

# Vite / common React dev servers (P3). Narrow localhost origins only.
DEFAULT_CORS_ORIGINS = (
    "http://127.0.0.1:5173",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
    "http://localhost:3000",
)


def api_host() -> str:
    """Bind host — defaults to loopback only."""
    return os.getenv("STOCKBALLDB_API_HOST", DEFAULT_HOST).strip() or DEFAULT_HOST


def api_port() -> int:
    raw = os.getenv("STOCKBALLDB_API_PORT", str(DEFAULT_PORT)).strip()
    return int(raw) if raw else DEFAULT_PORT


def cors_origins() -> list[str]:
    raw = os.getenv("STOCKBALLDB_API_CORS_ORIGINS", "").strip()
    if raw:
        return [o.strip() for o in raw.split(",") if o.strip()]
    return list(DEFAULT_CORS_ORIGINS)
