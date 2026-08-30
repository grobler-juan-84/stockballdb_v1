"""PostgreSQL advisory lock for operational updates."""

from __future__ import annotations

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.pool import NullPool

# Stable StockBallDB operational update lock key (arbitrary fixed int64).
STOCKBALLDB_UPDATE_LOCK_KEY = 0x53544F434B4244  # "STOCKBD" in hex-ish


class AdvisoryLockError(Exception):
    """Advisory lock could not be acquired or released."""


class AdvisoryLock:
    """
    Session-scoped PostgreSQL advisory lock on a dedicated connection.

    The connection must remain open for the lock lifetime; stage code may use
    separate pooled connections without releasing this lock.
    """

    def __init__(self, database_url: str) -> None:
        self._engine: Engine = create_engine(database_url, poolclass=NullPool)
        self._conn: Connection | None = None
        self.acquired = False

    def try_acquire(self) -> bool:
        if self.acquired:
            return True
        self._conn = self._engine.connect()
        ok = self._conn.execute(
            text("SELECT pg_try_advisory_lock(:key)"),
            {"key": STOCKBALLDB_UPDATE_LOCK_KEY},
        ).scalar_one()
        self.acquired = bool(ok)
        if not self.acquired:
            self._conn.close()
            self._conn = None
        return self.acquired

    def release(self) -> None:
        if self._conn is None:
            return
        try:
            if self.acquired:
                self._conn.execute(
                    text("SELECT pg_advisory_unlock(:key)"),
                    {"key": STOCKBALLDB_UPDATE_LOCK_KEY},
                )
        finally:
            self._conn.close()
            self._conn = None
            self.acquired = False
            self._engine.dispose()
