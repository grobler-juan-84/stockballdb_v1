"""Ordered V1 build stages calling existing pipelines."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.engine import Engine

from stockballdb.calendar.trading_days_build import sync_trading_days
from stockballdb.calendar.validate import (
    TradingDaysValidationError,
    validate_trading_days_db,
    validate_trading_days_frame,
)
from stockballdb.calendar_context.derive import (
    CalendarContextValidationError,
    sync_calendar_context,
)
from stockballdb.calendar_context.validate import (
    assert_no_forward_dependency,
    assert_shortened_matches_nyse,
    validate_db as validate_calendar_db,
    validate_frame as validate_calendar_frame,
)
from stockballdb.config import ConfigError, Settings
from stockballdb.db import get_engine, reset_engine
from stockballdb.snapshots.context import is_snapshot_mode
from stockballdb.events.build import sync_scheduled_events
from stockballdb.events.validate import (
    ScheduledEventsValidationError,
    validate_db as validate_events_db,
    validate_events,
    validate_fomc_scheduled_only,
)
from stockballdb.macro.build import sync_macro_conditions
from stockballdb.macro.validate import (
    assert_alignment_helpers,
    assert_inflation_regime_uses_distinct_releases,
    assert_no_future_inflation_release_leak,
    assert_rate_regime_lookback,
    validate_macro_db,
    validate_macro_frame,
)
from stockballdb.macro.derive import MacroConditionsValidationError
from stockballdb.market_context.wti import sync_wti_pipeline
from stockballdb.market_data.build import sync_daily_market_data
from stockballdb.market_data.derive import sync_derived_market_data
from stockballdb.market_data.universe import PHASE_2A_ETF_SYMBOLS, WTI_SYMBOL
from stockballdb.market_data.validate import (
    DailyMarketDataValidationError,
    validate_daily_market_data_db,
    validate_derived_market_data_frame,
)
from stockballdb.outcomes.derive import (
    MarketOutcomesValidationError,
    sync_market_outcomes,
)
from stockballdb.outcomes.validate import (
    validate_market_outcomes_db,
    validate_market_outcomes_frame,
)
from stockballdb.regimes.derive import (
    AssetRegimesValidationError,
    sync_asset_regimes,
)
from stockballdb.regimes.validate import (
    assert_volatility_regime_is_point_in_time,
    validate_asset_regimes_db,
    validate_asset_regimes_frame,
    validate_volatility_formula_sample,
)
from stockballdb.v1.preflight import V1_ALEMBIC_HEAD


class StageError(Exception):
    """Raised when a V1 build stage fails."""


@dataclass(frozen=True)
class Stage:
    key: str
    label: str
    run: Callable[[Settings], str]


def _repo_root() -> Path:
    # src/stockballdb/v1/stages.py -> repo root
    return Path(__file__).resolve().parents[3]


def stage_migrate(settings: Settings) -> str:
    reset_engine()
    cfg = Config(str(_repo_root() / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", settings.database_url)
    command.upgrade(cfg, "head")
    engine = get_engine(settings)
    with engine.connect() as conn:
        rev = conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
    if rev != V1_ALEMBIC_HEAD:
        raise StageError(f"expected alembic head {V1_ALEMBIC_HEAD}; found {rev}")
    return f"revision={rev}"


def stage_trading_days(settings: Settings) -> str:
    reset_engine()
    engine = get_engine(settings)
    try:
        frame = sync_trading_days(engine)
        validate_trading_days_frame(frame)
        validate_trading_days_db(engine, expected_count=len(frame))
    except TradingDaysValidationError as exc:
        raise StageError(str(exc)) from exc
    return f"rows={len(frame)} {frame['date'].iloc[0]}->{frame['date'].iloc[-1]}"


def stage_daily_market_data(settings: Settings) -> str:
    reset_engine()
    engine = get_engine(settings)
    if not is_snapshot_mode():
        assert settings.tiingo_api_key
    try:
        frame = sync_daily_market_data(engine, settings.tiingo_api_key)
        validate_daily_market_data_db(
            engine,
            expected_count=len(frame),
            symbols=PHASE_2A_ETF_SYMBOLS,
        )
    except DailyMarketDataValidationError as exc:
        raise StageError(str(exc)) from exc
    return (
        f"rows={len(frame)} symbols={frame['symbol'].nunique()} "
        f"{frame['date'].min()}->{frame['date'].max()}"
    )


def stage_derive_market_data(settings: Settings) -> str:
    reset_engine()
    engine = get_engine(settings)
    try:
        frame = sync_derived_market_data(engine)
        validate_derived_market_data_frame(frame)
        validate_daily_market_data_db(
            engine,
            expected_count=len(frame),
            require_derived=True,
            symbols=PHASE_2A_ETF_SYMBOLS,
        )
    except DailyMarketDataValidationError as exc:
        raise StageError(str(exc)) from exc
    return f"derived rows={len(frame)}"


def stage_market_outcomes(settings: Settings) -> str:
    reset_engine()
    engine = get_engine(settings)
    try:
        frame = sync_market_outcomes(engine)
        validate_market_outcomes_frame(frame)
        validate_market_outcomes_db(
            engine,
            expected_count=len(frame),
            symbols=PHASE_2A_ETF_SYMBOLS,
        )
    except MarketOutcomesValidationError as exc:
        raise StageError(str(exc)) from exc
    return f"rows={len(frame)} symbols={frame['symbol'].nunique()}"


def stage_asset_regimes(settings: Settings) -> str:
    reset_engine()
    engine = get_engine(settings)
    try:
        frame = sync_asset_regimes(engine)
        validate_asset_regimes_frame(frame)
        validate_volatility_formula_sample(frame)
        assert_volatility_regime_is_point_in_time(frame)
        validate_asset_regimes_db(
            engine,
            expected_count=len(frame),
            symbols=PHASE_2A_ETF_SYMBOLS,
        )
    except AssetRegimesValidationError as exc:
        raise StageError(str(exc)) from exc
    return f"rows={len(frame)} symbols={frame['symbol'].nunique()}"


def stage_wti_context(settings: Settings) -> str:
    reset_engine()
    engine = get_engine(settings)
    if not is_snapshot_mode():
        assert settings.fred_api_key
    try:
        report = sync_wti_pipeline(engine, settings.fred_api_key)
        validate_daily_market_data_db(
            engine,
            expected_count=report.row_count,
            required_symbols=(WTI_SYMBOL,),
            symbol_scope=WTI_SYMBOL,
        )
        validate_daily_market_data_db(
            engine,
            expected_count=report.row_count,
            required_symbols=(WTI_SYMBOL,),
            require_derived=True,
            symbol_scope=WTI_SYMBOL,
        )
        validate_market_outcomes_db(
            engine,
            expected_count=report.row_count,
            required_symbols=(WTI_SYMBOL,),
            symbol_scope=WTI_SYMBOL,
        )
        validate_asset_regimes_db(
            engine,
            expected_count=report.row_count,
            required_symbols=(WTI_SYMBOL,),
            symbol_scope=WTI_SYMBOL,
        )
    except DailyMarketDataValidationError as exc:
        raise StageError(str(exc)) from exc
    return (
        f"rows={report.row_count} {report.first_date}->{report.last_date}"
    )


def stage_macro_conditions(settings: Settings) -> str:
    reset_engine()
    engine = get_engine(settings)
    if not is_snapshot_mode():
        assert settings.fred_api_key
    try:
        assert_alignment_helpers()
        with engine.connect() as conn:
            td_count = conn.execute(text("SELECT COUNT(*) FROM trading_days")).scalar_one()
        frame, releases = sync_macro_conditions(engine, settings.fred_api_key)
        validate_macro_frame(frame, expected_days=td_count)
        validate_macro_db(engine, expected_count=td_count)
        assert_inflation_regime_uses_distinct_releases(releases, frame)
        assert_no_future_inflation_release_leak(releases, frame)
        assert_rate_regime_lookback(frame)
    except MacroConditionsValidationError as exc:
        raise StageError(str(exc)) from exc
    return f"rows={len(frame)} (1:1 trading_days)"


def stage_scheduled_events(settings: Settings) -> str:
    reset_engine()
    engine = get_engine(settings)
    if not is_snapshot_mode():
        assert settings.fred_api_key
    try:
        events = sync_scheduled_events(engine, settings.fred_api_key)
        validate_events(events)
        validate_fomc_scheduled_only(events)
        validate_events_db(engine, expected_count=len(events))
    except ScheduledEventsValidationError as exc:
        raise StageError(str(exc)) from exc
    return f"rows={len(events)}"


def stage_calendar_context(settings: Settings) -> str:
    reset_engine()
    engine = get_engine(settings)
    try:
        with engine.connect() as conn:
            trading_days = [
                r[0]
                for r in conn.execute(
                    text("SELECT date FROM trading_days ORDER BY date")
                )
            ]
        frame = sync_calendar_context(engine)
        validate_calendar_frame(frame, trading_days)
        assert_shortened_matches_nyse(frame)
        assert_no_forward_dependency(frame)
        validate_calendar_db(engine, expected_count=len(trading_days))
    except CalendarContextValidationError as exc:
        raise StageError(str(exc)) from exc
    return f"rows={len(frame)} (1:1 trading_days)"


BUILD_STAGES: tuple[Stage, ...] = (
    Stage("migrate", "migrate", stage_migrate),
    Stage("trading_days", "1/9 trading_days", stage_trading_days),
    Stage("daily_market_data", "2/9 daily_market_data", stage_daily_market_data),
    Stage("derive_market_data", "3/9 derive_market_data", stage_derive_market_data),
    Stage("market_outcomes", "4/9 market_outcomes", stage_market_outcomes),
    Stage("asset_regimes", "5/9 asset_regimes", stage_asset_regimes),
    Stage("wti_context", "5b/9 wti_context", stage_wti_context),
    Stage("macro_conditions", "6/9 macro_conditions", stage_macro_conditions),
    Stage("scheduled_events", "7/9 scheduled_events", stage_scheduled_events),
    Stage("calendar_context", "8/9 calendar_context", stage_calendar_context),
)


def collect_diagnostics(engine: Engine) -> dict:
    """Snapshot diagnostics for the build report (not hard invariants)."""
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT
                  (SELECT COUNT(*) FROM trading_days) AS trading_days,
                  (SELECT MIN(date) FROM trading_days) AS td_min,
                  (SELECT MAX(date) FROM trading_days) AS td_max,
                  (SELECT COUNT(*) FROM daily_market_data) AS daily_market_data,
                  (SELECT MIN(date) FROM daily_market_data) AS dmd_min,
                  (SELECT MAX(date) FROM daily_market_data) AS dmd_max,
                  (SELECT COUNT(DISTINCT symbol) FROM daily_market_data) AS symbols,
                  (SELECT COUNT(*) FROM market_outcomes) AS market_outcomes,
                  (SELECT COUNT(*) FROM asset_regimes) AS asset_regimes,
                  (SELECT COUNT(*) FROM macro_conditions) AS macro_conditions,
                  (SELECT COUNT(*) FROM scheduled_events) AS scheduled_events,
                  (SELECT COUNT(*) FROM calendar_context) AS calendar_context,
                  (SELECT version_num FROM alembic_version) AS alembic_revision
                """
            )
        ).mappings().one()
    return dict(rows)
