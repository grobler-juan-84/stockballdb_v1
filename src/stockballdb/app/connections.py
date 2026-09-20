"""Thin connection helpers for the application façade.

P1 reuses existing configuration and Explorer read-only engine helpers.
No second configuration system is introduced.

Note: some reused V1 health helpers historically default to the shared
``db.get_engine()`` path. Status operations in this package pass the Explorer
read engine explicitly when calling those helpers.
"""

from __future__ import annotations

from sqlalchemy.engine import Engine

from stockballdb.app.errors import AppUnavailableError
from stockballdb.config import Settings
from stockballdb.explorer.db import check_explorer_connection, get_explorer_engine


def get_read_engine(settings: Settings | None = None) -> Engine:
    """Return the Explorer read engine (preferred read path for the façade)."""
    return get_explorer_engine(settings)


def ensure_database_available(settings: Settings | None = None) -> None:
    """Raise ``AppUnavailableError`` when the Explorer database cannot be reached."""
    try:
        check_explorer_connection(settings)
    except Exception as exc:  # noqa: BLE001 — surface as application unavailable
        raise AppUnavailableError(
            f"database unavailable: {exc}"
        ) from exc
