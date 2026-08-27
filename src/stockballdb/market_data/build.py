"""Build and persist daily_market_data for Phase 2A ETFs."""

from __future__ import annotations

import datetime as dt

import pandas as pd
from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import Engine

from stockballdb.market_data.normalize import OBSERVED_COLUMNS, normalize_tiingo_bars
from stockballdb.market_data.universe import PHASE_2A_ETF_SYMBOLS
from stockballdb.market_data.validate import (
    DailyMarketDataValidationError,
    validate_daily_market_data_frame,
)
from stockballdb.models.daily_market_data import DailyMarketData
from stockballdb.models.trading_days import TradingDay
from stockballdb.providers.tiingo import TiingoError, fetch_daily_prices

UPSERT_COLUMNS = tuple(c for c in OBSERVED_COLUMNS if c not in ("date", "symbol"))


def load_trading_day_dates(engine: Engine) -> set[dt.date]:
    """Load the set of dates from trading_days."""
    with engine.connect() as conn:
        rows = conn.execute(select(TradingDay.date)).scalars().all()
    if not rows:
        raise DailyMarketDataValidationError(
            "trading_days is empty; build the trading calendar before market data"
        )
    return set(rows)


def upsert_daily_market_data(
    engine: Engine,
    frame: pd.DataFrame,
    *,
    batch_size: int = 500,
) -> int:
    """Idempotently upsert observed daily_market_data columns."""
    if frame.empty:
        return 0

    records = frame[list(OBSERVED_COLUMNS)].to_dict(orient="records")
    with engine.begin() as conn:
        for offset in range(0, len(records), batch_size):
            batch = records[offset : offset + batch_size]
            stmt = insert(DailyMarketData).values(batch)
            stmt = stmt.on_conflict_do_update(
                index_elements=[DailyMarketData.date, DailyMarketData.symbol],
                set_={col: getattr(stmt.excluded, col) for col in UPSERT_COLUMNS},
            )
            conn.execute(stmt)
    return len(records)


def sync_daily_market_data(
    engine: Engine,
    api_key: str,
    *,
    symbols: tuple[str, ...] = PHASE_2A_ETF_SYMBOLS,
) -> pd.DataFrame:
    """
    Fetch, normalize, validate, and upsert Phase 2A ETF market data.

    Does not delete existing rows. Derived fields are not written.
    """
    trading_days = load_trading_day_dates(engine)
    frames: list[pd.DataFrame] = []

    for symbol in symbols:
        try:
            bars = fetch_daily_prices(symbol, api_key)
        except TiingoError as exc:
            raise DailyMarketDataValidationError(str(exc)) from exc

        frame = normalize_tiingo_bars(symbol, bars, trading_days=trading_days)
        outside = frame.attrs.get("tiingo_dates_outside_trading_days", [])
        if outside:
            raise DailyMarketDataValidationError(
                f"{symbol}: {len(outside)} Tiingo dates not in trading_days "
                f"(example={outside[0]}); refusing to insert"
            )
        if frame.empty:
            raise DailyMarketDataValidationError(
                f"{symbol}: no observations remain after trading_days filter"
            )
        frames.append(frame)

    combined = pd.concat(frames, ignore_index=True)
    validate_daily_market_data_frame(
        combined,
        trading_days=trading_days,
        required_symbols=symbols,
    )
    upsert_daily_market_data(engine, combined)
    return combined


def coverage_summary(engine: Engine) -> pd.DataFrame:
    """Return per-symbol min/max date and row counts from the database."""
    with engine.connect() as conn:
        result = conn.execute(
            text(
                "SELECT symbol, COUNT(*) AS rows, MIN(date) AS earliest, "
                "MAX(date) AS latest "
                "FROM daily_market_data GROUP BY symbol ORDER BY symbol"
            )
        )
        rows = result.mappings().all()
    return pd.DataFrame(rows)
