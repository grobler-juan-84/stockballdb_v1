"""SQLAlchemy database connection infrastructure for StockBallDB."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from stockballdb.config import Settings, load_settings

_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


def get_engine(settings: Settings | None = None) -> Engine:
    """Return a shared SQLAlchemy engine for the configured database."""
    global _engine, _SessionLocal
    if _engine is None:
        cfg = settings or load_settings()
        _engine = create_engine(cfg.database_url, pool_pre_ping=True)
        _SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False)
    return _engine


def get_session_factory(settings: Settings | None = None) -> sessionmaker[Session]:
    """Return a session factory bound to the shared engine."""
    get_engine(settings)
    assert _SessionLocal is not None
    return _SessionLocal


@contextmanager
def session_scope(settings: Settings | None = None) -> Generator[Session, None, None]:
    """Provide a transactional session scope that closes on exit."""
    factory = get_session_factory(settings)
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def check_connection(settings: Settings | None = None) -> None:
    """
    Verify PostgreSQL connectivity with ``SELECT 1``.

    Raises the underlying SQLAlchemy/DBAPI error on failure.
    Does not log or return credentials.
    """
    engine = get_engine(settings)
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))


def reset_engine() -> None:
    """Dispose the shared engine (useful for tests)."""
    global _engine, _SessionLocal
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _SessionLocal = None
