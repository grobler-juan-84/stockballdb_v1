"""CLI: build retrospective market_outcomes from daily_market_data."""

from __future__ import annotations

import sys

from sqlalchemy import text

from stockballdb.config import ConfigError, load_settings
from stockballdb.db import get_engine, reset_engine
from stockballdb.logging_config import configure_logging, get_logger
from stockballdb.market_data.universe import PHASE_2A_ETF_SYMBOLS
from stockballdb.outcomes.derive import (
    MarketOutcomesValidationError,
    sync_market_outcomes,
)
from stockballdb.outcomes.validate import (
    validate_market_outcomes_db,
    validate_market_outcomes_frame,
)


def main() -> int:
    configure_logging()
    logger = get_logger("stockballdb.build_market_outcomes")
    logger.info("StockBallDB starting market_outcomes build")
    logger.info(
        "source=daily_market_data symbols=%s (retrospective labels; not PIT)",
        ",".join(PHASE_2A_ETF_SYMBOLS),
    )

    try:
        settings = load_settings(require_database_url=True)
        reset_engine()
        engine = get_engine(settings)

        with engine.connect() as conn:
            fingerprint_before = conn.execute(
                text(
                    "SELECT COUNT(*), COALESCE(SUM(close),0), COALESCE(SUM(adj_close),0) "
                    "FROM daily_market_data"
                )
            ).one()

        frame = sync_market_outcomes(engine)
        validate_market_outcomes_frame(frame)
        validate_market_outcomes_db(engine, expected_count=len(frame))

        frame2 = sync_market_outcomes(engine)
        if len(frame2) != len(frame):
            raise MarketOutcomesValidationError("idempotent rebuild changed row count")

        with engine.connect() as conn:
            fingerprint_after = conn.execute(
                text(
                    "SELECT COUNT(*), COALESCE(SUM(close),0), COALESCE(SUM(adj_close),0) "
                    "FROM daily_market_data"
                )
            ).one()
            if fingerprint_before != fingerprint_after:
                raise MarketOutcomesValidationError(
                    "daily_market_data mutated during outcomes build"
                )
            nulls = conn.execute(
                text(
                    """
                    SELECT
                      COUNT(*) FILTER (WHERE return_1d IS NULL) AS r1,
                      COUNT(*) FILTER (WHERE return_5d IS NULL) AS r5,
                      COUNT(*) FILTER (WHERE return_20d IS NULL) AS r20,
                      COUNT(*) FILTER (WHERE max_up_5d IS NULL) AS u5,
                      COUNT(*) FILTER (WHERE max_up_20d IS NULL) AS u20,
                      MIN(date) AS earliest,
                      MAX(date) AS latest
                    FROM market_outcomes
                    """
                )
            ).mappings().one()
    except (ConfigError, MarketOutcomesValidationError) as exc:
        print("FAILURE")
        print("market_outcomes build failed.")
        print(str(exc))
        logger.error("build failed: %s", exc)
        return 1
    except Exception as exc:
        print("FAILURE")
        print("market_outcomes build failed.")
        print(str(exc))
        logger.error("build failed: %s", exc)
        return 1

    print("SUCCESS")
    print(
        f"market_outcomes rows={len(frame)} symbols={frame['symbol'].nunique()} "
        f"from {nulls['earliest']} to {nulls['latest']}"
    )
    print(
        f"nulls return_1d={nulls['r1']} return_5d={nulls['r5']} "
        f"return_20d={nulls['r20']} max_up_5d={nulls['u5']} max_up_20d={nulls['u20']}"
    )
    logger.info("pipeline completed market_outcomes rows=%s", len(frame))
    return 0


if __name__ == "__main__":
    sys.exit(main())
