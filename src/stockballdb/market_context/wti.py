"""Build and persist WTI close-only market context from FRED DCOILWTICO."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

import requests
from sqlalchemy.engine import Engine

from stockballdb.market_data.build import load_trading_day_dates, upsert_daily_market_data
from stockballdb.market_data.derive import sync_derived_market_data
from stockballdb.market_data.normalize import normalize_fred_close_only_observations
from stockballdb.market_data.universe import WTI_SYMBOL
from stockballdb.market_data.validate import (
    DailyMarketDataValidationError,
    validate_daily_market_data_frame,
)
from stockballdb.outcomes.derive import sync_market_outcomes
from stockballdb.providers.fred import FredError, fetch_current_observations
from stockballdb.regimes.derive import sync_asset_regimes

WTI_FRED_SERIES_ID = "DCOILWTICO"
WTI_PROVIDER = "fred"
WTI_NATIVE_UNITS = "USD/barrel"


@dataclass(frozen=True)
class WtiBuildReport:
    symbol: str
    provider: str
    series_id: str
    retrieval_timestamp: dt.datetime
    row_count: int
    first_date: dt.date | None
    last_date: dt.date | None
    observations_outside_trading_days: int
    example_outside_trading_day: dt.date | None


def sync_wti_market_data(
    engine: Engine,
    api_key: str,
    *,
    retrieval_timestamp: dt.datetime | None = None,
) -> tuple:
    """
    Fetch DCOILWTICO, normalize to close-only rows, validate, upsert.

    Returns (frame, WtiBuildReport).
    """
    retrieved_at = retrieval_timestamp or dt.datetime.now(dt.timezone.utc)
    trading_days = load_trading_day_dates(engine)
    session = requests.Session()
    try:
        observations = fetch_current_observations(
            WTI_FRED_SERIES_ID,
            api_key,
            session=session,
        )
    except FredError as exc:
        raise DailyMarketDataValidationError(str(exc)) from exc
    finally:
        session.close()

    frame = normalize_fred_close_only_observations(
        WTI_SYMBOL,
        observations,
        trading_days=trading_days,
    )
    outside = frame.attrs.get("fred_dates_outside_trading_days", [])
    if frame.empty:
        raise DailyMarketDataValidationError(
            f"{WTI_SYMBOL}: no observations remain after trading_days filter"
        )

    validate_daily_market_data_frame(
        frame,
        trading_days=trading_days,
        required_symbols=(WTI_SYMBOL,),
    )
    upsert_daily_market_data(engine, frame)

    report = WtiBuildReport(
        symbol=WTI_SYMBOL,
        provider=WTI_PROVIDER,
        series_id=WTI_FRED_SERIES_ID,
        retrieval_timestamp=retrieved_at,
        row_count=len(frame),
        first_date=frame["date"].min(),
        last_date=frame["date"].max(),
        observations_outside_trading_days=len(outside),
        example_outside_trading_day=outside[0] if outside else None,
    )
    return frame, report


def sync_wti_pipeline(engine: Engine, api_key: str) -> WtiBuildReport:
    """Ingest WTI and refresh derived market/outcome/regime rows for WTI."""
    _, report = sync_wti_market_data(engine, api_key)
    sync_derived_market_data(engine, symbols=(WTI_SYMBOL,))
    sync_market_outcomes(engine, symbols=(WTI_SYMBOL,))
    sync_asset_regimes(engine, symbols=(WTI_SYMBOL,))
    return report
