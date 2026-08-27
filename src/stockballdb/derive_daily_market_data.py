"""CLI: derive Phase 2B behavioral fields for daily_market_data."""

from __future__ import annotations

import sys

from stockballdb.config import ConfigError, load_settings
from stockballdb.db import get_engine, reset_engine
from stockballdb.logging_config import configure_logging, get_logger
from stockballdb.market_data.derive import (
    derived_coverage_summary,
    sync_derived_market_data,
)
from stockballdb.market_data.universe import PHASE_2A_ETF_SYMBOLS
from stockballdb.market_data.validate import (
    DailyMarketDataValidationError,
    validate_daily_market_data_db,
    validate_derived_market_data_frame,
)


def main() -> int:
    configure_logging()
    logger = get_logger("stockballdb.derive_daily_market_data")
    logger.info("StockBallDB starting daily_market_data derivation")
    logger.info("symbols=%s", ",".join(PHASE_2A_ETF_SYMBOLS))

    try:
        settings = load_settings(require_database_url=True)
        reset_engine()
        engine = get_engine(settings)
        frame = sync_derived_market_data(engine)
        validate_derived_market_data_frame(frame)
        validate_daily_market_data_db(
            engine,
            expected_count=len(frame),
            require_derived=True,
        )
        # Idempotency: second sync must leave counts unchanged
        frame2 = sync_derived_market_data(engine)
        if len(frame2) != len(frame):
            raise DailyMarketDataValidationError("idempotent derive changed row count")
        coverage = derived_coverage_summary(engine)
    except (ConfigError, DailyMarketDataValidationError) as exc:
        print("FAILURE")
        print("daily_market_data derivation failed.")
        print(str(exc))
        logger.error("derive failed: %s", exc)
        return 1
    except Exception as exc:
        print("FAILURE")
        print("daily_market_data derivation failed.")
        print(str(exc))
        logger.error("derive failed: %s", exc)
        return 1

    print("SUCCESS")
    print(
        f"derived rows={coverage['rows']} symbols={coverage['symbols']} "
        f"return_1d_nn={coverage['return_1d_nn']} "
        f"gap_pct_nn={coverage['gap_pct_nn']} "
        f"intraday_nn={coverage['intraday_return_nn']} "
        f"range_nn={coverage['range_pct_nn']} "
        f"drawdown_nn={coverage['drawdown_from_high_nn']}"
    )
    logger.info("pipeline completed derivation rows=%s", coverage["rows"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
