"""Scheduled-event constants, IDs, and canonical row type."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

EVENT_TYPES = frozenset(
    {"fomc", "cpi", "employment_situation", "election"}
)

RELEASE_SESSIONS = frozenset(
    {"pre_open", "during_session", "after_close", "unknown"}
)

ELECTION_REFERENCE_PERIODS = frozenset({"presidential", "midterm"})

# Fed: statement release standardized at 2:00 p.m. ET from March 2013 onward
# (Federal Reserve Board press release, 2013-03-13).
FOMC_STATEMENT_TIME_CONFIDENT_FROM = dt.date(2013, 3, 20)
FOMC_STATEMENT_TIME_ET = dt.time(14, 0)

# BLS major statistical releases use 8:30 a.m. Eastern on current schedules;
# applied only where we treat the convention as historically justified for V1.
BLS_RELEASE_TIME_ET = dt.time(8, 30)
BLS_TIME_CONFIDENT_FROM = dt.date(1990, 1, 1)

COVERAGE_START = dt.date(1957, 1, 1)

SOURCE_FOMC = "federal_reserve_fomc_historical"
SOURCE_CPI = "alfred_cpiaucsl_first_print"
SOURCE_EMPLOYMENT = "alfred_unrate_first_print"
SOURCE_ELECTION = "us_statutory_election_day"

COVERAGE_NOTES = {
    "fomc": (
        "Scheduled FOMC meeting statement/decision days from Federal Reserve "
        "historical materials (1957-2020 year pages) and fomccalendars.htm "
        "(2021+). Unscheduled/emergency meetings, conference calls, notation "
        "votes, and cancelled meetings excluded. event_time_et only from "
        f"{FOMC_STATEMENT_TIME_CONFIDENT_FROM.isoformat()} onward (14:00 ET)."
    ),
    "cpi": (
        "BLS CPI release occurrences from ALFRED CPIAUCSL first-print "
        "realtime_start per reference month. Revision-only vintage dates are "
        "not separate events. Values live in macro_conditions, not here."
    ),
    "employment_situation": (
        "BLS Employment Situation release occurrences from ALFRED UNRATE "
        "first-print realtime_start per reference month. ICSA/jobless claims "
        "are a different release and are not included."
    ),
    "election": (
        "U.S. presidential and midterm general Election Days only "
        "(first Tuesday after first Monday in November of even years). "
        "release_session=unknown; event_time_et=NULL."
    ),
}


@dataclass(frozen=True)
class CanonicalEvent:
    """Normalized scheduled-event occurrence facts."""

    event_type: str
    event_date: dt.date
    symbol: str | None
    reference_period: str | None
    release_session: str
    event_time_et: dt.time | None
    source: str

    @property
    def event_id(self) -> str:
        return make_event_id(
            self.event_type,
            self.event_date,
            self.reference_period,
            self.symbol,
        )

    def as_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "event_date": self.event_date,
            "symbol": self.symbol,
            "reference_period": self.reference_period,
            "release_session": self.release_session,
            "event_time_et": self.event_time_et,
            "source": self.source,
        }


def make_event_id(
    event_type: str,
    event_date: dt.date,
    reference_period: str | None,
    symbol: str | None,
) -> str:
    """
    Deterministic ID: {type}:{date}:{reference_period_or_NA}:{symbol_or_MARKET}
    """
    ref = reference_period if reference_period else "NA"
    sym = symbol if symbol else "MARKET"
    return f"{event_type}:{event_date.isoformat()}:{ref}:{sym}"


def reference_month(ref_date: dt.date) -> str:
    """YYYY-MM reference period for monthly macro releases."""
    return f"{ref_date.year:04d}-{ref_date.month:02d}"
