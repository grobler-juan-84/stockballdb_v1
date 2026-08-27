"""CLI: build / update / validate daily_market_data for Phase 2A ETFs."""

from __future__ import annotations

import sys

from stockballdb.config import ConfigError, load_settings
from stockballdb.db import get_engine, reset_engine
from stockballdb.logging_config import configure_logging, get_logger
from stockballdb.market_data.build import coverage_summary, sync_daily_market_data
from stockballdb.market_data.universe import PHASE_2A_ETF_SYMBOLS
from stockballdb.market_data.validate import (
    DailyMarketDataValidationError,
    validate_daily_market_data_db,
)


def main() -> int:
    configure_logging()
    logger = get_logger("stockballdb.build_daily_market_data")
    logger.info("StockBallDB starting daily_market_data build")
    logger.info(
        "provider=Tiingo symbols=%s",
        ",".join(PHASE_2A_ETF_SYMBOLS),
    )

    try:
        settings = load_settings(
            require_database_url=True,
            require_tiingo_api_key=True,
        )
        assert settings.tiingo_api_key is not None
        reset_engine()
        engine = get_engine(settings)
        frame = sync_daily_market_data(engine, settings.tiingo_api_key)
        validate_daily_market_data_db(engine, expected_count=len(frame))
        summary = coverage_summary(engine)
    except (ConfigError, DailyMarketDataValidationError) as exc:
        print("FAILURE")
        print("daily_market_data build failed.")
        print(str(exc))
        logger.error("build failed: %s", exc)
        return 1
    except Exception as exc:
        print("FAILURE")
        print("daily_market_data build failed.")
        print(str(exc))
        logger.error("build failed: %s", exc)
        return 1

    outside = frame.attrs.get("tiingo_dates_outside_trading_days_count", 0)
    print("SUCCESS")
    print(
        f"daily_market_data rows={len(frame)} symbols={frame['symbol'].nunique()} "
        f"from {frame['date'].min()} to {frame['date'].max()}"
    )
    for row in summary.itertuples(index=False):
        print(f"  {row.symbol}: rows={row.rows} {row.earliest} -> {row.latest}")
    logger.info("pipeline completed daily_market_data rows=%s", len(frame))
    return 0


if __name__ == "__main__":
    sys.exit(main())
