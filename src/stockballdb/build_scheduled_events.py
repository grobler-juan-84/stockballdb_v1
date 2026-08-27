"""CLI: build scheduled_events occurrence calendar."""

from __future__ import annotations

import sys
from collections import Counter

from sqlalchemy import text

from stockballdb.config import ConfigError, load_settings
from stockballdb.db import get_engine, reset_engine
from stockballdb.events.build import sync_scheduled_events
from stockballdb.events.types import COVERAGE_NOTES
from stockballdb.events.validate import (
    ScheduledEventsValidationError,
    upsert_scheduled_events,
    validate_db,
    validate_events,
    validate_fomc_scheduled_only,
)
from stockballdb.logging_config import configure_logging, get_logger


def main() -> int:
    configure_logging()
    logger = get_logger("stockballdb.build_scheduled_events")
    logger.info("StockBallDB starting scheduled_events build")
    for k, note in COVERAGE_NOTES.items():
        logger.info("coverage %s: %s", k, note)

    try:
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
                      (SELECT COUNT(*) FROM macro_conditions),
                      (SELECT COALESCE(SUM(adj_close),0) FROM daily_market_data)
                    """
                )
            ).one()

        events = sync_scheduled_events(engine, settings.fred_api_key)
        validate_events(events)
        validate_fomc_scheduled_only(events)
        validate_db(engine, expected_count=len(events))

        n2 = upsert_scheduled_events(engine, events)
        if n2 != len(events):
            raise ScheduledEventsValidationError("idempotent upsert changed row count")
        validate_db(engine, expected_count=len(events))

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
                      (SELECT COALESCE(SUM(adj_close),0) FROM daily_market_data)
                    """
                )
            ).one()
            if fingerprint_before != fingerprint_after:
                raise ScheduledEventsValidationError(
                    "existing canonical tables mutated during scheduled_events build"
                )
            rows = conn.execute(
                text(
                    """
                    SELECT event_type, COUNT(*) AS n,
                           MIN(event_date) AS first_d, MAX(event_date) AS last_d
                    FROM scheduled_events
                    GROUP BY event_type
                    ORDER BY event_type
                    """
                )
            ).mappings().all()
            sessions = conn.execute(
                text(
                    """
                    SELECT release_session, COUNT(*) AS n
                    FROM scheduled_events
                    GROUP BY release_session
                    ORDER BY release_session
                    """
                )
            ).mappings().all()
            timed = conn.execute(
                text(
                    "SELECT COUNT(*) FROM scheduled_events "
                    "WHERE event_time_et IS NOT NULL"
                )
            ).scalar_one()
    except (ConfigError, ScheduledEventsValidationError) as exc:
        print("FAILURE")
        print("scheduled_events build failed.")
        print(str(exc))
        logger.error("build failed: %s", exc)
        return 1
    except Exception as exc:
        print("FAILURE")
        print("scheduled_events build failed.")
        print(str(exc))
        logger.error("build failed: %s", exc)
        return 1

    print("SUCCESS")
    print(f"scheduled_events rows={len(events)}")
    for r in rows:
        print(
            f"  {r['event_type']}: n={r['n']} "
            f"first={r['first_d']} last={r['last_d']}"
        )
    for r in sessions:
        print(f"  session {r['release_session']}: n={r['n']}")
    print(f"event_time_et non-null={timed}")
    type_counts = Counter(e.event_type for e in events)
    logger.info("pipeline completed scheduled_events rows=%s %s", len(events), dict(type_counts))
    return 0


if __name__ == "__main__":
    sys.exit(main())
