"""Integration test for PostgreSQL connectivity."""

from __future__ import annotations

import pytest
from dotenv import load_dotenv

from stockballdb.config import ConfigError, load_settings
from stockballdb.db import check_connection, reset_engine


@pytest.fixture(autouse=True)
def _reset_engine() -> None:
    reset_engine()
    yield
    reset_engine()


def test_database_connection_select_1() -> None:
    """
    Integration check: SELECT 1 against local PostgreSQL.

    Skips intentionally when DATABASE_URL is missing or the server is unreachable.
    """
    load_dotenv()

    try:
        settings = load_settings(require_database_url=True)
    except ConfigError as exc:
        pytest.skip(
            f"DATABASE_URL is not set ({exc}). Copy .env.example to .env and "
            "configure local PostgreSQL to run this integration test."
        )

    try:
        check_connection(settings)
    except Exception as exc:
        pytest.skip(
            f"PostgreSQL unavailable ({type(exc).__name__}: {exc}). "
            "Start local PostgreSQL and verify DATABASE_URL, then re-run."
        )
