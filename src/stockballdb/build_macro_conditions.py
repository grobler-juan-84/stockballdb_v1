"""CLI: build point-in-time macro_conditions from FRED/ALFRED."""

from __future__ import annotations

import sys

from sqlalchemy import text

from stockballdb.config import ConfigError, load_settings
from stockballdb.db import get_engine, reset_engine
from stockballdb.logging_config import configure_logging, get_logger
from stockballdb.macro.build import sync_macro_conditions
from stockballdb.macro.derive import MacroConditionsValidationError
from stockballdb.macro.series import ICSA_VINTAGE_LIMITATION, MACRO_SERIES
from stockballdb.macro.validate import (
    assert_alignment_helpers,
    assert_inflation_regime_uses_distinct_releases,
    assert_no_future_inflation_release_leak,
    assert_rate_regime_lookback,
    validate_macro_db,
    validate_macro_frame,
)


def main() -> int:
    configure_logging()
    logger = get_logger("stockballdb.build_macro_conditions")
    logger.info("StockBallDB starting macro_conditions build")
    logger.info(
        "series=%s (pmi deferred)",
        ",".join(f"{s.field}:{s.series_id}" for s in MACRO_SERIES),
    )
    logger.info("limitation: %s", ICSA_VINTAGE_LIMITATION)

    try:
        assert_alignment_helpers()
        settings = load_settings(
            require_database_url=True, require_fred_api_key=True
        )
        reset_engine()
        engine = get_engine(settings)

        with engine.connect() as conn:
            fingerprint_before = conn.execute(
                text(
                    """
                    SELECT
                      (SELECT COUNT(*) FROM trading_days),
                      (SELECT COUNT(*) FROM daily_market_data),
                      (SELECT COUNT(*) FROM market_outcomes),
                      (SELECT COUNT(*) FROM asset_regimes),
                      (SELECT COALESCE(SUM(adj_close),0) FROM daily_market_data)
                    """
                )
            ).one()
            td_count = fingerprint_before[0]

        frame, releases = sync_macro_conditions(engine, settings.fred_api_key)
        validate_macro_frame(frame, expected_days=td_count)
        validate_macro_db(engine, expected_count=td_count)
        assert_inflation_regime_uses_distinct_releases(releases, frame)
        assert_no_future_inflation_release_leak(releases, frame)
        assert_rate_regime_lookback(frame)

        from stockballdb.macro.derive import upsert_macro_conditions

        n2 = upsert_macro_conditions(engine, frame)
        if n2 != len(frame):
            raise MacroConditionsValidationError("idempotent upsert changed row count")
        validate_macro_db(engine, expected_count=td_count)

        with engine.connect() as conn:
            fingerprint_after = conn.execute(
                text(
                    """
                    SELECT
                      (SELECT COUNT(*) FROM trading_days),
                      (SELECT COUNT(*) FROM daily_market_data),
                      (SELECT COUNT(*) FROM market_outcomes),
                      (SELECT COUNT(*) FROM asset_regimes),
                      (SELECT COALESCE(SUM(adj_close),0) FROM daily_market_data)
                    """
                )
            ).one()
            if fingerprint_before != fingerprint_after:
                raise MacroConditionsValidationError(
                    "existing canonical tables mutated during macro build"
                )
            nulls = conn.execute(
                text(
                    """
                    SELECT
                      COUNT(*) FILTER (WHERE inflation_rate IS NULL) AS n_inf,
                      COUNT(*) FILTER (WHERE unemployment_rate IS NULL) AS n_un,
                      COUNT(*) FILTER (WHERE fed_funds_rate IS NULL) AS n_ff,
                      COUNT(*) FILTER (WHERE inflation_regime IS NULL) AS n_ir,
                      COUNT(*) FILTER (WHERE rate_regime IS NULL) AS n_rr,
                      MIN(date) FILTER (WHERE inflation_rate IS NOT NULL) AS first_inf,
                      MIN(date) FILTER (WHERE fed_funds_rate IS NOT NULL) AS first_ff
                    FROM macro_conditions
                    """
                )
            ).mappings().one()
    except (ConfigError, MacroConditionsValidationError) as exc:
        print("FAILURE")
        print("macro_conditions build failed.")
        print(str(exc))
        logger.error("build failed: %s", exc)
        return 1
    except Exception as exc:
        print("FAILURE")
        print("macro_conditions build failed.")
        print(str(exc))
        logger.error("build failed: %s", exc)
        return 1

    print("SUCCESS")
    print(f"macro_conditions rows={len(frame)} (1:1 trading_days)")
    print(
        f"nulls inflation={nulls['n_inf']} unemployment={nulls['n_un']} "
        f"fed_funds={nulls['n_ff']} inflation_regime={nulls['n_ir']} "
        f"rate_regime={nulls['n_rr']}"
    )
    print(
        f"first_non_null inflation={nulls['first_inf']} "
        f"fed_funds={nulls['first_ff']}"
    )
    logger.info("pipeline completed macro_conditions rows=%s", len(frame))
    return 0


if __name__ == "__main__":
    sys.exit(main())
