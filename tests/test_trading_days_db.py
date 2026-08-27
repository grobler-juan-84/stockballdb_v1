"""Database integration tests for trading_days."""

from __future__ import annotations

import datetime as dt

import pytest
from dotenv import load_dotenv
from sqlalchemy import text

from stockballdb.calendar.nyse import today_ny
from stockballdb.calendar.trading_days_build import sync_trading_days
from stockballdb.calendar.validate import (
    TradingDaysValidationError,
    validate_trading_days_db,
    validate_trading_days_frame,
)
from stockballdb.config import ConfigError, load_settings
from stockballdb.db import get_engine, reset_engine


@pytest.fixture(autouse=True)
def _reset_engine() -> None:
    reset_engine()
    yield
    reset_engine()


def test_trading_days_sync_and_idempotent() -> None:
    load_dotenv()
    try:
        settings = load_settings(require_database_url=True)
        engine = get_engine(settings)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1 FROM trading_days LIMIT 1"))
    except ConfigError as exc:
        pytest.skip(f"DATABASE_URL not set: {exc}")
    except Exception as exc:
        pytest.skip(
            f"trading_days table or PostgreSQL unavailable ({type(exc).__name__}: {exc})"
        )

    end = today_ny()
    frame = sync_trading_days(engine, start=dt.date(1957, 1, 1), end=end)
    try:
        validate_trading_days_frame(frame)
        validate_trading_days_db(engine, expected_count=len(frame))
    except TradingDaysValidationError as exc:
        pytest.fail(str(exc))

    frame2 = sync_trading_days(engine, start=dt.date(1957, 1, 1), end=end)
    assert len(frame2) == len(frame)
    validate_trading_days_db(engine, expected_count=len(frame2))

    with engine.connect() as conn:
        first = conn.execute(
            text("SELECT date FROM trading_days ORDER BY date ASC LIMIT 1")
        ).scalar_one()
        last = conn.execute(
            text("SELECT date FROM trading_days ORDER BY date DESC LIMIT 1")
        ).scalar_one()
        null_prev = conn.execute(
            text(
                "SELECT COUNT(*) FROM trading_days WHERE prev_trading_date IS NULL"
            )
        ).scalar_one()
    assert first == dt.date(1957, 1, 2)
    assert last <= end
    assert null_prev == 1
