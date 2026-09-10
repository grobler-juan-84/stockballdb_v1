"""Database integration tests for daily_market_data (mutating — requires test DB)."""

from __future__ import annotations

import datetime as dt

import pytest
from sqlalchemy import text

from stockballdb.db import reset_engine
from stockballdb.market_data.build import (
    load_trading_day_dates,
    upsert_daily_market_data,
)
from stockballdb.market_data.normalize import normalize_tiingo_bars
from stockballdb.providers.tiingo import fetch_daily_prices
from stockballdb.testing import require_mutable_test_settings


@pytest.fixture(autouse=True)
def _reset_engine() -> None:
    reset_engine()
    yield
    reset_engine()


def test_upsert_idempotent_for_single_symbol_window() -> None:
    """Fetch a short SPY window, upsert twice, assert stable row count."""
    settings = require_mutable_test_settings(require_tiingo_api_key=True)
    from stockballdb.db import get_engine

    engine = get_engine(settings)
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1 FROM daily_market_data LIMIT 1"))
            conn.execute(text("SELECT 1 FROM trading_days LIMIT 1"))
    except Exception as exc:
        pytest.skip(f"DB/table unavailable: {type(exc).__name__}: {exc}")

    assert settings.tiingo_api_key is not None
    trading_days = load_trading_day_dates(engine)
    bars = fetch_daily_prices(
        "SPY",
        settings.tiingo_api_key,
        start_date="2024-01-02",
        end_date="2024-01-10",
    )
    frame = normalize_tiingo_bars("SPY", bars, trading_days=trading_days)
    assert not frame.empty

    n1 = upsert_daily_market_data(engine, frame)
    n2 = upsert_daily_market_data(engine, frame)
    assert n1 == n2 == len(frame)

    with engine.connect() as conn:
        count = conn.execute(
            text(
                "SELECT COUNT(*) FROM daily_market_data "
                "WHERE symbol = 'SPY' AND date BETWEEN :a AND :b"
            ),
            {"a": dt.date(2024, 1, 2), "b": dt.date(2024, 1, 10)},
        ).scalar_one()
    assert count == len(frame)
