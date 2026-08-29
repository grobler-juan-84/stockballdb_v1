"""Unit tests for scheduled_events IDs, parsers, and generators."""

from __future__ import annotations

import datetime as dt

import pytest

from stockballdb.events.elections import (
    acquire_election_events,
    election_kind,
    federal_election_day,
)
from stockballdb.events.fomc import (
    assert_fixture_exclusions,
    fomc_timing,
    parse_calendars_html,
    parse_historical_heading,
    parse_historical_html,
    to_canonical,
)
from stockballdb.events.releases import _bls_timing
from stockballdb.events.types import (
    BLS_TIME_CONFIDENT_FROM,
    FOMC_STATEMENT_TIME_CONFIDENT_FROM,
    CanonicalEvent,
    make_event_id,
    reference_month,
)
from stockballdb.events.validate import (
    ScheduledEventsValidationError,
    validate_events,
    validate_fomc_scheduled_only,
)
from stockballdb.macro.pit import VintageRow, first_print_events


def test_deterministic_event_id() -> None:
    assert (
        make_event_id("fomc", dt.date(2020, 4, 29), None, None)
        == "fomc:2020-04-29:NA:MARKET"
    )
    assert (
        make_event_id("cpi", dt.date(2020, 3, 11), "2020-02", None)
        == "cpi:2020-03-11:2020-02:MARKET"
    )
    assert (
        make_event_id(
            "employment_situation", dt.date(2020, 3, 6), "2020-02", None
        )
        == "employment_situation:2020-03-06:2020-02:MARKET"
    )
    assert (
        make_event_id("election", dt.date(2020, 11, 3), "presidential", None)
        == "election:2020-11-03:presidential:MARKET"
    )


def test_event_id_stable_and_unique() -> None:
    a = CanonicalEvent(
        "fomc", dt.date(2019, 1, 30), None, None, "during_session",
        dt.time(14, 0), "federal_reserve_fomc_historical",
    )
    b = CanonicalEvent(
        "fomc", dt.date(2019, 1, 30), None, None, "during_session",
        dt.time(14, 0), "federal_reserve_fomc_historical",
    )
    assert a.event_id == b.event_id
    c = CanonicalEvent(
        "cpi", dt.date(2019, 1, 30), None, "2018-12", "pre_open",
        dt.time(8, 30), "alfred_cpiaucsl_first_print",
    )
    assert a.event_id != c.event_id


def test_fomc_heading_fixtures() -> None:
    assert_fixture_exclusions()
    assert parse_historical_heading("January 8 Meeting - 1957") == dt.date(
        1957, 1, 8
    )
    # Multi-day -> final day only
    assert parse_historical_heading("January 28-29 Meeting - 2020") == dt.date(
        2020, 1, 29
    )


def test_fomc_html_excludes_unscheduled_2020() -> None:
    html = """
    <h5>January 28-29 Meeting - 2020</h5>
    <h5>March 2 (unscheduled) Meeting - 2020</h5>
    <h5>March 15 (unscheduled) Meeting - 2020</h5>
    <h5>March 17-18 (cancelled) Meeting - 2020</h5>
    <h5>March 19 (notation vote) - 2020</h5>
    <h5>April 28-29 Meeting - 2020</h5>
    """
    days = parse_historical_html(html)
    assert days == [dt.date(2020, 1, 29), dt.date(2020, 4, 29)]


def test_fomc_calendars_parser() -> None:
    html = """
    <a>2024 FOMC Meetings</a></h4>
    <div class="row fomc-meeting">
      <div class="fomc-meeting__month col-xs-5"><strong>January</strong></div>
      <div class="fomc-meeting__date col-xs-4">30-31</div>
    </div>
    <div class="row fomc-meeting">
      <div class="fomc-meeting__month col-xs-5"><strong>March</strong></div>
      <div class="fomc-meeting__date col-xs-4">19-20*</div>
    </div>
    <div class="row fomc-meeting">
      <div class="fomc-meeting__month col-xs-5"><strong>Apr/May</strong></div>
      <div class="fomc-meeting__date col-xs-4">30-1</div>
    </div>
    <a>2025 FOMC Meetings</a></h4>
    <div class="row fomc-meeting">
      <div class="fomc-meeting__month col-xs-5"><strong>January</strong></div>
      <div class="fomc-meeting__date col-xs-4">28-29</div>
    </div>
    """
    assert parse_calendars_html(html, years={2024}) == [
        dt.date(2024, 1, 31),
        dt.date(2024, 3, 20),
        dt.date(2024, 5, 1),
    ]
    assert parse_calendars_html(html, years={2025}) == [dt.date(2025, 1, 29)]


def test_fomc_timing_not_inferred_pre_2013() -> None:
    session, etime = fomc_timing(dt.date(2012, 12, 12))
    assert session == "unknown"
    assert etime is None
    session, etime = fomc_timing(FOMC_STATEMENT_TIME_CONFIDENT_FROM)
    assert session == "during_session"
    assert etime == dt.time(14, 0)


def test_validate_fomc_scheduled_only() -> None:
    events = [
        to_canonical(dt.date(2019, 1, 30)),
        to_canonical(dt.date(2019, 5, 1)),
        to_canonical(dt.date(2020, 1, 29)),
        to_canonical(dt.date(2020, 4, 29)),
    ]
    validate_fomc_scheduled_only(events)
    leaked = events + [to_canonical(dt.date(2020, 3, 15))]
    # Force type even though to_canonical would make it — simulate bad data
    bad = list(events) + [
        CanonicalEvent(
            "fomc",
            dt.date(2020, 3, 15),
            None,
            None,
            "unknown",
            None,
            "federal_reserve_fomc_historical",
        )
    ]
    with pytest.raises(ScheduledEventsValidationError):
        validate_fomc_scheduled_only(bad)
    del leaked


def test_cpi_first_print_ignores_revisions() -> None:
    vintages = [
        VintageRow(
            dt.date(2020, 1, 1), 258.0,
            dt.date(2020, 2, 13), dt.date(2020, 3, 10),
        ),
        VintageRow(
            dt.date(2020, 1, 1), 258.1,
            dt.date(2020, 3, 10), dt.date(9999, 12, 31),
        ),
        VintageRow(
            dt.date(2020, 2, 1), 259.0,
            dt.date(2020, 3, 11), dt.date(9999, 12, 31),
        ),
    ]
    events = first_print_events(vintages)
    assert len(events) == 2
    assert events[0][0] == dt.date(2020, 2, 13)
    assert events[0][1] == dt.date(2020, 1, 1)
    assert events[1][0] == dt.date(2020, 3, 11)
    # Revision date 2020-03-10 is not a first-print event for Jan
    assert all(rt != dt.date(2020, 3, 10) for rt, _, _ in events)


def test_reference_month_and_bls_timing() -> None:
    assert reference_month(dt.date(2020, 2, 1)) == "2020-02"
    s, t = _bls_timing(BLS_TIME_CONFIDENT_FROM)
    assert s == "pre_open" and t == dt.time(8, 30)
    s, t = _bls_timing(dt.date(1985, 1, 15))
    assert s == "pre_open" and t is None


def test_election_dates_and_classification() -> None:
    assert federal_election_day(2020) == dt.date(2020, 11, 3)
    assert federal_election_day(2022) == dt.date(2022, 11, 8)
    assert federal_election_day(1958) == dt.date(1958, 11, 4)
    assert election_kind(2020) == "presidential"
    assert election_kind(2022) == "midterm"
    with pytest.raises(ValueError):
        election_kind(2021)

    evs = acquire_election_events(
        start=dt.date(2019, 1, 1), end=dt.date(2023, 12, 31)
    )
    assert [e.reference_period for e in evs] == ["presidential", "midterm"]
    assert evs[0].event_date == dt.date(2020, 11, 3)
    assert evs[1].event_date == dt.date(2022, 11, 8)
    for e in evs:
        assert e.release_session == "unknown"
        assert e.event_time_et is None
        assert e.symbol is None


def test_validate_events_vocabulary_and_symbol() -> None:
    good = [
        to_canonical(dt.date(2020, 4, 29)),
        CanonicalEvent(
            "cpi",
            dt.date(2020, 3, 11),
            None,
            "2020-02",
            "pre_open",
            dt.time(8, 30),
            "alfred_cpiaucsl_first_print",
        ),
        CanonicalEvent(
            "employment_situation",
            dt.date(2020, 3, 6),
            None,
            "2020-02",
            "pre_open",
            dt.time(8, 30),
            "alfred_unrate_first_print",
        ),
        CanonicalEvent(
            "election",
            dt.date(2020, 11, 3),
            None,
            "presidential",
            "unknown",
            None,
            "us_statutory_election_day",
        ),
    ]
    validate_events(good)

    bad_symbol = [
        CanonicalEvent(
            "cpi",
            dt.date(2020, 3, 11),
            "SPY",
            "2020-02",
            "pre_open",
            dt.time(8, 30),
            "alfred_cpiaucsl_first_print",
        )
    ]
    with pytest.raises(ScheduledEventsValidationError):
        validate_events(bad_symbol)

    bad_type = [
        CanonicalEvent(
            "jobs",
            dt.date(2020, 3, 6),
            None,
            "2020-02",
            "pre_open",
            None,
            "x",
        )
    ]
    with pytest.raises(ScheduledEventsValidationError):
        validate_events(bad_type)
