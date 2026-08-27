"""Validate and upsert scheduled_events."""

from __future__ import annotations

import datetime as dt
import re
from collections import Counter

from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import Engine

from stockballdb.events.types import (
    ELECTION_REFERENCE_PERIODS,
    EVENT_TYPES,
    RELEASE_SESSIONS,
    CanonicalEvent,
)
from stockballdb.models.scheduled_events import ScheduledEvent

REF_MONTH_RE = re.compile(r"^\d{4}-\d{2}$")


class ScheduledEventsValidationError(Exception):
    """Raised when scheduled_events validation fails."""


def validate_events(events: list[CanonicalEvent]) -> None:
    if not events:
        raise ScheduledEventsValidationError("no scheduled events produced")

    ids = [e.event_id for e in events]
    if len(ids) != len(set(ids)):
        dupes = [i for i, c in Counter(ids).items() if c > 1]
        raise ScheduledEventsValidationError(f"duplicate event_id: {dupes[:5]}")

    # Canonical occurrence uniqueness (type, date, reference_period, symbol)
    keys = [
        (e.event_type, e.event_date, e.reference_period, e.symbol) for e in events
    ]
    if len(keys) != len(set(keys)):
        raise ScheduledEventsValidationError("duplicate canonical event occurrence")

    for e in events:
        if e.event_type not in EVENT_TYPES:
            raise ScheduledEventsValidationError(f"bad event_type={e.event_type}")
        if e.release_session not in RELEASE_SESSIONS:
            raise ScheduledEventsValidationError(
                f"bad release_session={e.release_session}"
            )
        if e.symbol is not None:
            raise ScheduledEventsValidationError(
                f"V1 events must be market-wide; got symbol={e.symbol}"
            )
        if not e.source:
            raise ScheduledEventsValidationError(f"empty source for {e.event_id}")

        if e.event_time_et is not None and e.release_session == "unknown":
            raise ScheduledEventsValidationError(
                f"event_time_et set with unknown session: {e.event_id}"
            )

        if e.event_type in {"cpi", "employment_situation"}:
            if not e.reference_period or not REF_MONTH_RE.match(e.reference_period):
                raise ScheduledEventsValidationError(
                    f"bad reference_period for {e.event_id}"
                )
        elif e.event_type == "election":
            if e.reference_period not in ELECTION_REFERENCE_PERIODS:
                raise ScheduledEventsValidationError(
                    f"bad election reference_period for {e.event_id}"
                )
            if e.release_session != "unknown" or e.event_time_et is not None:
                raise ScheduledEventsValidationError(
                    f"election timing must be unknown/NULL: {e.event_id}"
                )
        elif e.event_type == "fomc":
            if e.reference_period is not None:
                raise ScheduledEventsValidationError(
                    f"fomc reference_period must be NULL: {e.event_id}"
                )


def validate_fomc_scheduled_only(events: list[CanonicalEvent]) -> None:
    """Fixture checks that known unscheduled 2020 dates are absent."""
    fomc_dates = {e.event_date for e in events if e.event_type == "fomc"}
    forbidden = {
        dt.date(2020, 3, 2),
        dt.date(2020, 3, 15),
        dt.date(2020, 3, 19),
        dt.date(2020, 3, 23),
        dt.date(2020, 3, 31),
        dt.date(2019, 10, 4),
        dt.date(2008, 1, 9),
        dt.date(2008, 1, 21),
    }
    leaked = sorted(fomc_dates & forbidden)
    if leaked:
        raise ScheduledEventsValidationError(
            f"unscheduled/non-meeting Fed dates present as fomc: {leaked}"
        )
    # Known scheduled multi-day finals must be present when coverage includes them
    required = {
        dt.date(2019, 1, 30),
        dt.date(2019, 5, 1),
        dt.date(2020, 1, 29),
        dt.date(2020, 4, 29),
    }
    missing = sorted(required - fomc_dates)
    # Only enforce if the build covers those years (end >= required)
    if fomc_dates and max(fomc_dates) >= dt.date(2020, 4, 29) and missing:
        raise ScheduledEventsValidationError(
            f"expected scheduled FOMC finals missing: {missing}"
        )


def validate_db(engine: Engine, expected_count: int) -> None:
    with engine.connect() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM scheduled_events")).scalar_one()
        if count != expected_count:
            raise ScheduledEventsValidationError(
                f"scheduled_events count {count} != {expected_count}"
            )
        bad_type = conn.execute(
            text(
                """
                SELECT COUNT(*) FROM scheduled_events
                WHERE event_type NOT IN
                  ('fomc','cpi','employment_situation','election')
                """
            )
        ).scalar_one()
        if bad_type:
            raise ScheduledEventsValidationError("DB has invalid event_type values")
        bad_session = conn.execute(
            text(
                """
                SELECT COUNT(*) FROM scheduled_events
                WHERE release_session NOT IN
                  ('pre_open','during_session','after_close','unknown')
                """
            )
        ).scalar_one()
        if bad_session:
            raise ScheduledEventsValidationError("DB has invalid release_session")
        non_null_symbol = conn.execute(
            text("SELECT COUNT(*) FROM scheduled_events WHERE symbol IS NOT NULL")
        ).scalar_one()
        if non_null_symbol:
            raise ScheduledEventsValidationError("V1 DB rows must have symbol NULL")
        dup = conn.execute(
            text(
                """
                SELECT COUNT(*) FROM (
                  SELECT event_type, event_date, reference_period, symbol, COUNT(*)
                  FROM scheduled_events
                  GROUP BY 1,2,3,4
                  HAVING COUNT(*) > 1
                ) d
                """
            )
        ).scalar_one()
        if dup:
            raise ScheduledEventsValidationError("DB duplicate occurrences")


def upsert_scheduled_events(
    engine: Engine,
    events: list[CanonicalEvent],
    *,
    batch_size: int = 500,
) -> int:
    records = [e.as_dict() for e in events]
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM scheduled_events"))
        for offset in range(0, len(records), batch_size):
            batch = records[offset : offset + batch_size]
            conn.execute(insert(ScheduledEvent).values(batch))
    return len(records)
