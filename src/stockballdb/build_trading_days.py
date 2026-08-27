"""CLI: build / update / validate the trading_days spine."""

from __future__ import annotations

import sys

import pandas_market_calendars as mcal

from stockballdb.calendar.trading_days_build import sync_trading_days
from stockballdb.calendar.validate import (
    TradingDaysValidationError,
    validate_trading_days_db,
    validate_trading_days_frame,
)
from stockballdb.db import get_engine, reset_engine
from stockballdb.logging_config import configure_logging, get_logger


def main() -> int:
    configure_logging()
    logger = get_logger("stockballdb.build_trading_days")
    logger.info("StockBallDB starting trading_days build")
    logger.info(
        "calendar authority=pandas_market_calendars==%s NYSE",
        mcal.__version__,
    )

    try:
        reset_engine()
        engine = get_engine()
        frame = sync_trading_days(engine)
        validate_trading_days_frame(frame)
        validate_trading_days_db(engine, expected_count=len(frame))
    except TradingDaysValidationError as exc:
        print("FAILURE")
        print("trading_days validation failed.")
        print(str(exc))
        logger.error("validation failed: %s", exc)
        return 1
    except Exception as exc:
        print("FAILURE")
        print("trading_days build failed.")
        print(str(exc))
        logger.error("build failed: %s", exc)
        return 1

    first = frame["date"].iloc[0]
    last = frame["date"].iloc[-1]
    print("SUCCESS")
    print(f"trading_days rows={len(frame)} from {first} to {last}")
    logger.info("pipeline completed trading_days rows=%s", len(frame))
    return 0


if __name__ == "__main__":
    sys.exit(main())
