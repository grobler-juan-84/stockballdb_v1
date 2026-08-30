"""Preflight checks before an operational update."""

from __future__ import annotations

import os

import pandas_market_calendars as mcal
from sqlalchemy import text

from stockballdb.config import (
    ConfigError,
    Settings,
    database_name_from_url,
    load_settings,
)
from stockballdb.db import check_connection, get_engine, reset_engine
from stockballdb.health.provenance import reports_dir
from stockballdb.snapshots.store import SnapshotStore
from stockballdb.v1.preflight import REQUIRED_CALENDAR_VERSION, V1_ALEMBIC_HEAD


class UpdatePreflightError(Exception):
    """Raised when operational update preflight fails."""


def _rebuild_database_url() -> str | None:
    return os.getenv("STOCKBALLDB_REBUILD_DATABASE_URL", "").strip() or None


def _assert_primary_not_rebuild_target(settings: Settings) -> None:
    rebuild = _rebuild_database_url()
    if not rebuild:
        return
    primary_db = database_name_from_url(settings.database_url)
    rebuild_db = database_name_from_url(rebuild)
    if primary_db and rebuild_db and primary_db == rebuild_db:
        raise UpdatePreflightError(
            "DATABASE_URL and STOCKBALLDB_REBUILD_DATABASE_URL must not "
            "target the same database for operational update."
        )


def _assert_paths_writable() -> None:
    reports = reports_dir()
    try:
        reports.mkdir(parents=True, exist_ok=True)
        probe = reports / ".write_probe"
        probe.write_text("", encoding="utf-8")
        probe.unlink(missing_ok=True)
    except OSError as exc:
        raise UpdatePreflightError(f"build_reports not writable: {exc}") from exc
    try:
        SnapshotStore()
    except OSError as exc:
        raise UpdatePreflightError(f"snapshot store not writable: {exc}") from exc


def run_update_preflight(settings: Settings | None = None) -> Settings:
    """
    Cheap checks before expensive provider acquisition.

    Does not contact providers beyond database connectivity.
    """
    if mcal.__version__ != REQUIRED_CALENDAR_VERSION:
        raise UpdatePreflightError(
            f"pandas_market_calendars must be {REQUIRED_CALENDAR_VERSION}; "
            f"found {mcal.__version__}"
        )

    try:
        cfg = settings or load_settings(
            require_database_url=True,
            require_tiingo_api_key=True,
            require_fred_api_key=True,
        )
    except ConfigError as exc:
        raise UpdatePreflightError(str(exc)) from exc

    _assert_primary_not_rebuild_target(cfg)

    reset_engine()
    try:
        check_connection(cfg)
    except Exception as exc:
        raise UpdatePreflightError(f"database connection failed: {exc}") from exc

    engine = get_engine(cfg)
    with engine.connect() as conn:
        rev = conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        if rev != V1_ALEMBIC_HEAD:
            raise UpdatePreflightError(
                f"database Alembic revision {rev!r} != expected {V1_ALEMBIC_HEAD}; "
                "run migrations explicitly before update"
            )
        td_count = conn.execute(text("SELECT COUNT(*) FROM trading_days")).scalar_one()
        if td_count < 1:
            raise UpdatePreflightError(
                "trading_days is empty; bootstrap with python -m stockballdb.build_v1 "
                "before operational update"
            )

    _assert_paths_writable()
    return cfg
