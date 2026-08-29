"""CLI: ingest WTI spot crude from FRED DCOILWTICO."""

from __future__ import annotations

import sys

from sqlalchemy import text

from stockballdb.config import ConfigError, load_settings
from stockballdb.db import get_engine, reset_engine
from stockballdb.logging_config import configure_logging, get_logger
from stockballdb.market_context.wti import sync_wti_pipeline
from stockballdb.snapshots.context import live_build_context, reset_context
from stockballdb.market_data.validate import (
    DailyMarketDataValidationError,
    validate_daily_market_data_db,
    validate_derived_market_data_frame,
)
from stockballdb.market_data.derive import load_observed_market_data, derive_daily_market_fields
from stockballdb.market_data.universe import WTI_SYMBOL
from stockballdb.outcomes.validate import validate_market_outcomes_db, validate_market_outcomes_frame
from stockballdb.outcomes.derive import load_daily_market_for_outcomes, derive_market_outcomes
from stockballdb.regimes.validate import validate_asset_regimes_db, validate_asset_regimes_frame
from stockballdb.regimes.derive import load_daily_market_for_regimes, derive_asset_regimes


def main() -> int:
    configure_logging()
    logger = get_logger("stockballdb.build_wti")
    logger.info("StockBallDB starting WTI build (FRED DCOILWTICO)")

    try:
        settings = load_settings(require_database_url=True)
        if not settings.fred_api_key:
            raise ConfigError("FRED_API_KEY is required for WTI ingestion")
        reset_engine()
        engine = get_engine(settings)

        reset_context()
        with live_build_context():
            report = sync_wti_pipeline(engine, settings.fred_api_key)
        reset_context()

        observed = load_observed_market_data(engine, symbols=(WTI_SYMBOL,))
        derived = derive_daily_market_fields(observed)
        validate_derived_market_data_frame(derived)

        outcomes_src = load_daily_market_for_outcomes(engine, symbols=(WTI_SYMBOL,))
        outcomes = derive_market_outcomes(outcomes_src)
        validate_market_outcomes_frame(outcomes)

        regimes_src = load_daily_market_for_regimes(engine, symbols=(WTI_SYMBOL,))
        regimes = derive_asset_regimes(regimes_src)
        validate_asset_regimes_frame(regimes)

        wti_count = len(observed)
        with engine.connect() as conn:
            db_wti = conn.execute(
                text("SELECT COUNT(*) FROM daily_market_data WHERE symbol = :symbol"),
                {"symbol": WTI_SYMBOL},
            ).scalar_one()
        if db_wti != wti_count:
            raise DailyMarketDataValidationError(
                f"WTI row count {db_wti} != expected {wti_count}"
            )

        validate_daily_market_data_db(
            engine,
            expected_count=db_wti,
            required_symbols=(WTI_SYMBOL,),
            require_derived=True,
            symbol_scope=WTI_SYMBOL,
        )
        validate_market_outcomes_db(
            engine,
            expected_count=db_wti,
            required_symbols=(WTI_SYMBOL,),
            symbol_scope=WTI_SYMBOL,
        )
        validate_asset_regimes_db(
            engine,
            expected_count=db_wti,
            required_symbols=(WTI_SYMBOL,),
            symbol_scope=WTI_SYMBOL,
        )
    except (ConfigError, DailyMarketDataValidationError) as exc:
        print("FAILURE")
        print("WTI build failed.")
        print(str(exc))
        logger.error("WTI build failed: %s", exc)
        return 1
    except Exception as exc:
        print("FAILURE")
        print("WTI build failed.")
        print(str(exc))
        logger.error("WTI build failed: %s", exc)
        return 1

    print("SUCCESS")
    print(
        f"symbol={report.symbol} provider={report.provider} "
        f"series={report.series_id} rows={report.row_count} "
        f"{report.first_date}->{report.last_date} "
        f"outside_trading_days={report.observations_outside_trading_days}"
    )
    logger.info("WTI build completed rows=%s", report.row_count)
    return 0


if __name__ == "__main__":
    sys.exit(main())
