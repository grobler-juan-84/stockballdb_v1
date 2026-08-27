"""CLI: build calendar_context from trading_days + NYSE + scheduled_events."""

from __future__ import annotations

import sys

from sqlalchemy import text

from stockballdb.calendar_context.derive import (
    CalendarContextValidationError,
    sync_calendar_context,
    upsert_calendar_context,
)
from stockballdb.calendar_context.validate import (
    assert_no_forward_dependency,
    assert_shortened_matches_nyse,
    validate_db,
    validate_frame,
)
from stockballdb.config import ConfigError, load_settings
from stockballdb.db import get_engine, reset_engine
from stockballdb.logging_config import configure_logging, get_logger


def main() -> int:
    configure_logging()
    logger = get_logger("stockballdb.build_calendar_context")
    logger.info("StockBallDB starting calendar_context build")

    try:
        settings = load_settings(require_database_url=True)
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
                      (SELECT COUNT(*) FROM macro_conditions),
                      (SELECT COUNT(*) FROM scheduled_events),
                      (SELECT COALESCE(SUM(adj_close),0) FROM daily_market_data)
                    """
                )
            ).one()
            td_count = fingerprint_before[0]
            trading_days = [
                r[0]
                for r in conn.execute(
                    text("SELECT date FROM trading_days ORDER BY date")
                )
            ]

        frame = sync_calendar_context(engine)
        validate_frame(frame, trading_days)
        assert_shortened_matches_nyse(frame)
        assert_no_forward_dependency(frame)
        validate_db(engine, expected_count=td_count)

        n2 = upsert_calendar_context(engine, frame)
        if n2 != len(frame):
            raise CalendarContextValidationError("idempotent upsert changed row count")
        validate_db(engine, expected_count=td_count)

        with engine.connect() as conn:
            fingerprint_after = conn.execute(
                text(
                    """
                    SELECT
                      (SELECT COUNT(*) FROM trading_days),
                      (SELECT COUNT(*) FROM daily_market_data),
                      (SELECT COUNT(*) FROM market_outcomes),
                      (SELECT COUNT(*) FROM asset_regimes),
                      (SELECT COUNT(*) FROM macro_conditions),
                      (SELECT COUNT(*) FROM scheduled_events),
                      (SELECT COALESCE(SUM(adj_close),0) FROM daily_market_data)
                    """
                )
            ).one()
            if fingerprint_before != fingerprint_after:
                raise CalendarContextValidationError(
                    "existing canonical tables mutated during calendar_context build"
                )
            stats = conn.execute(
                text(
                    """
                    SELECT
                      MIN(date) AS first_d,
                      MAX(date) AS last_d,
                      COUNT(*) FILTER (WHERE is_day_before_holiday) AS n_before,
                      COUNT(*) FILTER (WHERE is_day_after_holiday) AS n_after,
                      COUNT(*) FILTER (WHERE holiday_type = 'regular') AS n_reg,
                      COUNT(*) FILTER (WHERE holiday_type = 'exceptional') AS n_exc,
                      COUNT(*) FILTER (WHERE is_shortened_trading_day) AS n_short,
                      COUNT(*) FILTER (WHERE is_shortened_week) AS n_short_week,
                      COUNT(*) FILTER (WHERE is_turn_of_month) AS n_tom,
                      COUNT(*) FILTER (WHERE is_quarter_transition) AS n_q,
                      COUNT(*) FILTER (WHERE is_year_transition) AS n_y,
                      COUNT(*) FILTER (WHERE is_fomc_day) AS n_fomc,
                      COUNT(*) FILTER (WHERE is_cpi_release_day) AS n_cpi,
                      COUNT(*) FILTER (WHERE is_employment_situation_day) AS n_emp,
                      COUNT(*) FILTER (WHERE is_election_day) AS n_elec
                    FROM calendar_context
                    """
                )
            ).mappings().one()
            week_dist = conn.execute(
                text(
                    """
                    SELECT trading_days_in_week, COUNT(*) AS n
                    FROM calendar_context
                    GROUP BY 1 ORDER BY 1
                    """
                )
            ).all()
    except (ConfigError, CalendarContextValidationError) as exc:
        print("FAILURE")
        print("calendar_context build failed.")
        print(str(exc))
        logger.error("build failed: %s", exc)
        return 1
    except Exception as exc:
        print("FAILURE")
        print("calendar_context build failed.")
        print(str(exc))
        logger.error("build failed: %s", exc)
        return 1

    print("SUCCESS")
    print(f"calendar_context rows={len(frame)} (1:1 trading_days)")
    print(f"range {stats['first_d']} -> {stats['last_d']}")
    print(
        f"before_holiday={stats['n_before']} after_holiday={stats['n_after']} "
        f"holiday_regular={stats['n_reg']} holiday_exceptional={stats['n_exc']}"
    )
    print(
        f"shortened_session={stats['n_short']} shortened_week={stats['n_short_week']}"
    )
    print(
        f"turn_of_month={stats['n_tom']} quarter_transition={stats['n_q']} "
        f"year_transition={stats['n_y']}"
    )
    print(
        f"event_days fomc={stats['n_fomc']} cpi={stats['n_cpi']} "
        f"employment={stats['n_emp']} election={stats['n_elec']}"
    )
    print(f"trading_days_in_week dist={week_dist}")
    logger.info("pipeline completed calendar_context rows=%s", len(frame))
    return 0


if __name__ == "__main__":
    sys.exit(main())
