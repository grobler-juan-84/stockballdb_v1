"""Helpers for integration tests that mutate canonical database state."""

from __future__ import annotations

import os

from dotenv import load_dotenv

from stockballdb.config import (
    ConfigError,
    Settings,
    load_settings,
    same_database_url,
)
from stockballdb.db import get_engine

TEST_DATABASE_URL_ENV = "STOCKBALLDB_TEST_DATABASE_URL"


class MutableTestDatabaseError(Exception):
    """Raised when a mutating test cannot safely resolve a separate test DB."""


def mutable_test_database_url_from_env() -> str:
    """Return ``STOCKBALLDB_TEST_DATABASE_URL`` (empty string if unset)."""
    load_dotenv()
    return os.getenv(TEST_DATABASE_URL_ENV, "").strip()


def resolve_mutable_test_database_url(
    *,
    primary_database_url: str | None = None,
) -> str:
    """
    Resolve a disposable test database URL for mutating integration tests.

    Never falls back to ``DATABASE_URL``. Rejects a test URL that identifies
    the same host/port/database as the primary URL when primary is available.
    """
    test_url = mutable_test_database_url_from_env()
    if not test_url:
        raise MutableTestDatabaseError(
            f"{TEST_DATABASE_URL_ENV} is required for mutating database "
            "integration tests. Set it to a disposable PostgreSQL database "
            "separate from DATABASE_URL (primary StockBallDB). Mutating tests "
            "never fall back to DATABASE_URL."
        )

    primary = (primary_database_url or "").strip()
    if not primary:
        load_dotenv()
        primary = os.getenv("DATABASE_URL", "").strip()

    if primary and same_database_url(test_url, primary):
        raise MutableTestDatabaseError(
            f"{TEST_DATABASE_URL_ENV} must identify a different database than "
            "DATABASE_URL (host/port/database compared; credentials ignored). "
            "Mutating integration tests must not target the primary StockBallDB."
        )

    return test_url


def require_mutable_test_settings(
    *,
    require_tiingo_api_key: bool = False,
    require_fred_api_key: bool = False,
) -> Settings:
    """
    Return Settings bound to ``STOCKBALLDB_TEST_DATABASE_URL``.

    Skips when the test DB URL is unset. Fails when the test URL targets the
    same database as ``DATABASE_URL``.
    """
    import pytest

    try:
        primary = load_settings(require_database_url=False).database_url
    except ConfigError:
        primary = ""

    try:
        test_url = resolve_mutable_test_database_url(primary_database_url=primary)
    except MutableTestDatabaseError as exc:
        message = str(exc)
        if "is required" in message:
            pytest.skip(message)
        pytest.fail(message)

    base = load_settings(
        require_database_url=False,
        require_tiingo_api_key=require_tiingo_api_key,
        require_fred_api_key=require_fred_api_key,
    )
    return Settings(
        database_url=test_url,
        tiingo_api_key=base.tiingo_api_key,
        fred_api_key=base.fred_api_key,
        eia_api_key=base.eia_api_key,
        run_as_of=base.run_as_of,
    )


def require_mutable_test_engine(
    *,
    require_tiingo_api_key: bool = False,
    require_fred_api_key: bool = False,
):
    """Return ``(engine, settings)`` for the guarded mutable test database."""
    settings = require_mutable_test_settings(
        require_tiingo_api_key=require_tiingo_api_key,
        require_fred_api_key=require_fred_api_key,
    )
    return get_engine(settings), settings
