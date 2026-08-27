"""CLI: build point-in-time asset_regimes from daily_market_data."""

from __future__ import annotations

import sys

from sqlalchemy import text

from stockballdb.config import ConfigError, load_settings
from stockballdb.db import get_engine, reset_engine
from stockballdb.logging_config import configure_logging, get_logger
from stockballdb.market_data.universe import PHASE_2A_ETF_SYMBOLS
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


def main() -> int:
    configure_logging()
    logger = get_logger("stockballdb.build_asset_regimes")
    logger.info("StockBallDB starting asset_regimes build")
    logger.info(
        "source=daily_market_data symbols=%s (PIT through date t; no market_outcomes)",
        ",".join(PHASE_2A_ETF_SYMBOLS),
    )

    try:
        settings = load_settings(require_database_url=True)
        reset_engine()
        engine = get_engine(settings)

        with engine.connect() as conn:
            fingerprint_before = conn.execute(
                text(
                    """
                    SELECT
                      (SELECT COUNT(*) FROM daily_market_data),
                      (SELECT COALESCE(SUM(close),0) FROM daily_market_data),
                      (SELECT COALESCE(SUM(adj_close),0) FROM daily_market_data),
                      (SELECT COUNT(*) FROM market_outcomes),
                      (SELECT COUNT(*) FROM trading_days)
                    """
                )
            ).one()

        frame = sync_asset_regimes(engine)
        validate_asset_regimes_frame(frame)
        validate_volatility_formula_sample(frame)
        assert_volatility_regime_is_point_in_time(frame)
        validate_asset_regimes_db(engine, expected_count=len(frame))

        frame2 = sync_asset_regimes(engine)
        if len(frame2) != len(frame):
            raise AssetRegimesValidationError("idempotent rebuild changed row count")

        with engine.connect() as conn:
            fingerprint_after = conn.execute(
                text(
                    """
                    SELECT
                      (SELECT COUNT(*) FROM daily_market_data),
                      (SELECT COALESCE(SUM(close),0) FROM daily_market_data),
                      (SELECT COALESCE(SUM(adj_close),0) FROM daily_market_data),
                      (SELECT COUNT(*) FROM market_outcomes),
                      (SELECT COUNT(*) FROM trading_days)
                    """
                )
            ).one()
            if fingerprint_before != fingerprint_after:
                raise AssetRegimesValidationError(
                    "source tables mutated during asset_regimes build"
                )
            stats = conn.execute(
                text(
                    """
                    SELECT
                      MIN(date) AS earliest,
                      MAX(date) AS latest,
                      COUNT(*) FILTER (WHERE return_5d IS NULL) AS null_r5,
                      COUNT(*) FILTER (WHERE volatility_20d IS NULL) AS null_vol,
                      COUNT(*) FILTER (WHERE trend_regime IS NULL) AS null_trend,
                      COUNT(*) FILTER (WHERE volatility_regime IS NULL) AS null_vreg
                    FROM asset_regimes
                    """
                )
            ).mappings().one()
    except (ConfigError, AssetRegimesValidationError) as exc:
        print("FAILURE")
        print("asset_regimes build failed.")
        print(str(exc))
        logger.error("build failed: %s", exc)
        return 1
    except Exception as exc:
        print("FAILURE")
        print("asset_regimes build failed.")
        print(str(exc))
        logger.error("build failed: %s", exc)
        return 1

    print("SUCCESS")
    print(
        f"asset_regimes rows={len(frame)} symbols={frame['symbol'].nunique()} "
        f"from {stats['earliest']} to {stats['latest']}"
    )
    print(
        f"nulls return_5d={stats['null_r5']} volatility_20d={stats['null_vol']} "
        f"trend_regime={stats['null_trend']} volatility_regime={stats['null_vreg']}"
    )
    logger.info("pipeline completed asset_regimes rows=%s", len(frame))
    return 0


if __name__ == "__main__":
    sys.exit(main())
