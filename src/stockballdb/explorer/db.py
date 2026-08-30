"""Isolated read-only database access for Explorer."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection, Engine

from stockballdb.config import Settings, explorer_database_url, load_settings

_explorer_engine: Engine | None = None


def get_explorer_engine(settings: Settings | None = None) -> Engine:
    """Return a dedicated SQLAlchemy engine for Explorer (not shared with build/update)."""
    global _explorer_engine
    if _explorer_engine is None:
        url = explorer_database_url(settings)
        _explorer_engine = create_engine(url, pool_pre_ping=True)
    return _explorer_engine


@contextmanager
def readonly_connection(settings: Settings | None = None) -> Generator[Connection, None, None]:
    """Yield a read-only PostgreSQL connection."""
    engine = get_explorer_engine(settings)
    with engine.connect() as conn:
        try:
            conn.execute(text("SET TRANSACTION READ ONLY"))
        except Exception:
            pass
        yield conn


def reset_explorer_engine() -> None:
    """Dispose Explorer engine (tests)."""
    global _explorer_engine
    if _explorer_engine is not None:
        _explorer_engine.dispose()
    _explorer_engine = None


def check_explorer_connection(settings: Settings | None = None) -> None:
    """Verify Explorer database connectivity."""
    cfg = settings or load_settings(require_database_url=True)
    engine = create_engine(explorer_database_url(cfg), pool_pre_ping=True)
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    engine.dispose()
