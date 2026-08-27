"""Build scheduled_events from official / ALFRED sources."""

from __future__ import annotations

import datetime as dt
from zoneinfo import ZoneInfo

import requests
from sqlalchemy import text
from sqlalchemy.engine import Engine

from stockballdb.events.elections import acquire_election_events
from stockballdb.events.fomc import acquire_fomc_events
from stockballdb.events.releases import (
    acquire_cpi_events,
    acquire_employment_situation_events,
)
from stockballdb.events.types import COVERAGE_START, CanonicalEvent
from stockballdb.events.validate import (
    ScheduledEventsValidationError,
    upsert_scheduled_events,
    validate_events,
    validate_fomc_scheduled_only,
)


def _as_of_end(engine: Engine) -> dt.date:
    """Use latest trading_days date, capped at today ET."""
    today = dt.datetime.now(ZoneInfo("America/New_York")).date()
    with engine.connect() as conn:
        max_td = conn.execute(text("SELECT MAX(date) FROM trading_days")).scalar_one()
    if max_td is None:
        raise ScheduledEventsValidationError("trading_days is empty")
    return min(max_td, today)


def collect_scheduled_events(
    engine: Engine,
    fred_api_key: str,
    *,
    start: dt.date = COVERAGE_START,
    end: dt.date | None = None,
    session: requests.Session | None = None,
) -> list[CanonicalEvent]:
    end = end or _as_of_end(engine)
    http = session or requests.Session()

    events: list[CanonicalEvent] = []
    events.extend(acquire_fomc_events(start=start, end=end, session=http))
    events.extend(
        acquire_cpi_events(fred_api_key, start=start, end=end, session=http)
    )
    events.extend(
        acquire_employment_situation_events(
            fred_api_key, start=start, end=end, session=http
        )
    )
    events.extend(acquire_election_events(start=start, end=end))

    events.sort(key=lambda e: (e.event_date, e.event_type, e.event_id))
    validate_events(events)
    validate_fomc_scheduled_only(events)
    return events


def sync_scheduled_events(
    engine: Engine,
    fred_api_key: str,
    *,
    start: dt.date = COVERAGE_START,
    end: dt.date | None = None,
) -> list[CanonicalEvent]:
    events = collect_scheduled_events(
        engine, fred_api_key, start=start, end=end
    )
    upsert_scheduled_events(engine, events)
    return events
