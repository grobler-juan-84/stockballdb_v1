"""Phase 7B calendar_context audit — all locked Phase 7A invariants."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import sys

from sqlalchemy import text

from stockballdb.calendar_context.derive import effective_session
from stockballdb.calendar_context.holidays import early_close_dates
from stockballdb.config import load_settings
from stockballdb.db import get_engine, reset_engine

TRADING_DAYS_OWNED = frozenset(
    {
        "weekday",
        "month",
        "quarter",
        "year",
        "day_of_month",
        "week_of_year",
        "trading_day_of_month",
        "trading_day_of_year",
        "days_to_month_end",
        "is_month_end",
        "is_quarter_end",
        "is_year_end",
        "prev_trading_date",
        "next_trading_date",
    }
)

FLAG_MAP = {
    "fomc": "is_fomc_day",
    "cpi": "is_cpi_release_day",
    "employment_situation": "is_employment_situation_day",
    "election": "is_election_day",
}
SINCE_MAP = {
    "fomc": "days_since_last_fomc",
    "cpi": "days_since_last_cpi",
    "employment_situation": "days_since_last_employment_situation",
    "election": "days_since_last_election",
}

FORWARD_PREFIXES = ("days_until_next_", "days_to_next_", "next_event_")


def _section(title: str) -> None:
    print(f"\n=== {title} ===")


def _pass(msg: str) -> None:
    print(f"PASS: {msg}")


def _fail(msg: str) -> None:
    print(f"FAIL: {msg}")


def main() -> int:
    settings = load_settings(require_database_url=True)
    reset_engine()
    engine = get_engine(settings)
    failures: list[str] = []
    invariant: dict[str, str] = {}

    def check(inv: str, ok: bool, detail: str) -> None:
        invariant[inv] = "PASS" if ok else "FAIL"
        if ok:
            _pass(f"[{inv}] {detail}")
        else:
            _fail(f"[{inv}] {detail}")
            failures.append(f"{inv}: {detail}")

    with engine.connect() as conn:
        # --- schema ---
        _section("Schema")
        cc_cols = [
            r[0]
            for r in conn.execute(
                text(
                    """
                    SELECT column_name FROM information_schema.columns
                    WHERE table_schema = current_schema()
                      AND table_name = 'calendar_context'
                    ORDER BY ordinal_position
                    """
                )
            ).all()
        ]
        print(f"calendar_context columns ({len(cc_cols)}): {cc_cols}")
        expected_n = 19
        check(
            "inv2-schema",
            len(cc_cols) == expected_n,
            f"{len(cc_cols)} columns match locked inventory (expected {expected_n})",
        )
        forward_cols = [
            c for c in cc_cols if any(c.startswith(p) for p in FORWARD_PREFIXES)
        ]
        check("inv17", not forward_cols, f"no forward columns ({forward_cols or 'none'})")
        dup_td = [c for c in cc_cols if c in TRADING_DAYS_OWNED]
        check("inv2", not dup_td, f"no duplicated trading_days fields ({dup_td or 'none'})")

        # --- grain ---
        _section("Invariant 1 — Grain")
        td_count = conn.execute(text("SELECT COUNT(*) FROM trading_days")).scalar_one()
        cc_count = conn.execute(text("SELECT COUNT(*) FROM calendar_context")).scalar_one()
        td_first = conn.execute(text("SELECT MIN(date) FROM trading_days")).scalar_one()
        td_last = conn.execute(text("SELECT MAX(date) FROM trading_days")).scalar_one()
        cc_first = conn.execute(text("SELECT MIN(date) FROM calendar_context")).scalar_one()
        cc_last = conn.execute(text("SELECT MAX(date) FROM calendar_context")).scalar_one()
        print(f"calendar_context rows={cc_count} range {cc_first} -> {cc_last}")
        missing = conn.execute(
            text(
                """
                SELECT COUNT(*) FROM trading_days t
                LEFT JOIN calendar_context c ON c.date = t.date
                WHERE c.date IS NULL
                """
            )
        ).scalar_one()
        orphans = conn.execute(
            text(
                """
                SELECT COUNT(*) FROM calendar_context c
                LEFT JOIN trading_days t ON t.date = c.date
                WHERE t.date IS NULL
                """
            )
        ).scalar_one()
        dups = conn.execute(
            text(
                """
                SELECT COUNT(*) FROM (
                  SELECT date FROM calendar_context GROUP BY date HAVING COUNT(*)>1
                ) d
                """
            )
        ).scalar_one()
        check(
            "inv1",
            cc_count == td_count
            and cc_first == td_first
            and cc_last == td_last
            and missing == 0
            and orphans == 0
            and dups == 0,
            f"1:1 grain count={cc_count} missing={missing} orphans={orphans} dups={dups}",
        )

        trading_days = [
            r[0]
            for r in conn.execute(text("SELECT date FROM trading_days ORDER BY date")).all()
        ]
        trading_set = set(trading_days)
        day_index = {d: i for i, d in enumerate(trading_days)}

        # --- holiday metadata ---
        _section("Invariant 4 — Holiday metadata consistency")
        bad_name = conn.execute(
            text(
                """
                SELECT COUNT(*) FROM calendar_context
                WHERE holiday_name IS NOT NULL
                  AND NOT is_day_before_holiday
                  AND NOT is_day_after_holiday
                """
            )
        ).scalar_one()
        bad_null = conn.execute(
            text(
                """
                SELECT COUNT(*) FROM calendar_context
                WHERE holiday_name IS NULL
                  AND (is_day_before_holiday OR is_day_after_holiday)
                """
            )
        ).scalar_one()
        bad_type = conn.execute(
            text(
                """
                SELECT COUNT(*) FROM calendar_context
                WHERE holiday_type IS NOT NULL
                  AND holiday_type NOT IN ('regular','exceptional')
                """
            )
        ).scalar_one()
        check(
            "inv4",
            bad_name == 0 and bad_null == 0 and bad_type == 0,
            f"name_without_flag={bad_name} flag_without_name={bad_null} bad_type={bad_type}",
        )

        # --- shortened week identity ---
        _section("Invariant 6 — ISO week geometry")
        bad_short = conn.execute(
            text(
                """
                SELECT COUNT(*) FROM calendar_context
                WHERE is_shortened_week != (trading_days_in_week < 5)
                """
            )
        ).scalar_one()
        bad_range = conn.execute(
            text(
                """
                SELECT COUNT(*) FROM calendar_context
                WHERE trading_days_in_week < 1 OR trading_days_in_week > 5
                """
            )
        ).scalar_one()
        check(
            "inv6",
            bad_short == 0 and bad_range == 0,
            f"shortened_week_identity={bad_short} range_violations={bad_range}",
        )

        # --- transitions ---
        _section("Invariants 7-9 — Period transitions")
        bad_tom = conn.execute(
            text(
                """
                SELECT COUNT(*) FROM calendar_context c
                JOIN trading_days t ON t.date = c.date
                WHERE c.is_turn_of_month != (
                  t.is_month_end OR t.trading_day_of_month = 1
                )
                """
            )
        ).scalar_one()
        check("inv7", bad_tom == 0, f"is_turn_of_month mismatches={bad_tom}")

        # quarter/year first sessions via SQL window
        bad_q = conn.execute(
            text(
                """
                WITH first_q AS (
                  SELECT DISTINCT ON (year, quarter) date AS d
                  FROM trading_days ORDER BY year, quarter, date
                ),
                last_q AS (
                  SELECT DISTINCT ON (year, quarter) date AS d
                  FROM trading_days ORDER BY year, quarter, date DESC
                )
                SELECT COUNT(*) FROM calendar_context c
                WHERE c.is_quarter_transition != (
                  c.date IN (SELECT d FROM first_q)
                  OR c.date IN (SELECT d FROM last_q)
                )
                """
            )
        ).scalar_one()
        bad_y = conn.execute(
            text(
                """
                WITH first_y AS (
                  SELECT DISTINCT ON (year) date AS d
                  FROM trading_days ORDER BY year, date
                ),
                last_y AS (
                  SELECT DISTINCT ON (year) date AS d
                  FROM trading_days ORDER BY year, date DESC
                )
                SELECT COUNT(*) FROM calendar_context c
                WHERE c.is_year_transition != (
                  c.date IN (SELECT d FROM first_y)
                  OR c.date IN (SELECT d FROM last_y)
                )
                """
            )
        ).scalar_one()
        check("inv8", bad_q == 0, f"is_quarter_transition mismatches={bad_q}")
        check("inv9", bad_y == 0, f"is_year_transition mismatches={bad_y}")

        # --- event flags ---
        _section("Invariants 10-11 — Event same-day flags")
        for etype, flag in FLAG_MAP.items():
            db_true = conn.execute(
                text(f"SELECT COUNT(*) FROM calendar_context WHERE {flag} IS TRUE")
            ).scalar_one()
            on_cal = conn.execute(
                text(
                    """
                    SELECT COUNT(DISTINCT e.event_date)
                    FROM scheduled_events e
                    JOIN trading_days t ON t.date = e.event_date
                    WHERE e.event_type = :etype
                    """
                ),
                {"etype": etype},
            ).scalar_one()
            mismatch = conn.execute(
                text(
                    f"""
                    SELECT COUNT(*) FROM calendar_context c
                    WHERE c.{flag} != EXISTS (
                      SELECT 1 FROM scheduled_events e
                      WHERE e.event_type = :etype AND e.event_date = c.date
                    )
                    """
                ),
                {"etype": etype},
            ).scalar_one()
            print(f"  {etype}: flag_true={db_true} on_calendar_events={on_cal}")
            check(
                f"inv10-{etype}",
                mismatch == 0,
                f"{flag} IFF on-calendar {etype} events (mismatch rows={mismatch})",
            )
            check(
                f"inv11-{etype}",
                db_true == on_cal,
                f"{flag} count {db_true} == on-calendar {on_cal}",
            )

        # --- off-calendar effective session ---
        _section("Invariant 12 — Effective session")
        off_total = conn.execute(
            text(
                """
                SELECT COUNT(*) FROM scheduled_events e
                LEFT JOIN trading_days t ON t.date = e.event_date
                WHERE t.date IS NULL
                """
            )
        ).scalar_one()
        print(f"total off-calendar scheduled_events={off_total}")

        election_row = conn.execute(
            text(
                """
                SELECT date, is_election_day, days_since_last_election
                FROM calendar_context WHERE date IN ('1958-11-04','1958-11-05','1958-11-06')
                ORDER BY date
                """
            )
        ).all()
        print("1958 election context:", election_row)
        nov5 = conn.execute(
            text(
                """
                SELECT is_election_day, days_since_last_election
                FROM calendar_context WHERE date='1958-11-05'
                """
            )
        ).one()
        check(
            "inv12-election",
            nov5[0] is False and nov5[1] == 0,
            "1958-11-05 is_election_day=FALSE days_since=0",
        )

        # additional off-calendar per family
        for etype in FLAG_MAP:
            off_dates = conn.execute(
                text(
                    """
                    SELECT e.event_date FROM scheduled_events e
                    LEFT JOIN trading_days t ON t.date = e.event_date
                    WHERE e.event_type = :etype AND t.date IS NULL
                    ORDER BY e.event_date LIMIT 1
                    """
                ),
                {"etype": etype},
            ).scalar_one_or_none()
            if off_dates is None:
                print(f"  {etype}: no off-calendar sample")
                continue
            eff = effective_session(off_dates, trading_set, trading_days)
            since_col = SINCE_MAP[etype]
            flag = FLAG_MAP[etype]
            eff_row = conn.execute(
                text(
                    f"SELECT {flag}, {since_col} FROM calendar_context WHERE date=:d"
                ),
                {"d": eff},
            ).one()
            print(f"  {etype} off-calendar {off_dates} -> eff {eff}: {eff_row}")
            check(
                f"inv12-{etype}",
                eff_row[1] == 0 and eff_row[0] is False,
                f"effective session {eff} days_since=0 flag=FALSE",
            )

        # --- days_since semantics sample ---
        _section("Invariant 13 — Days since (on-calendar sample)")
        fomc_on = conn.execute(
            text(
                """
                SELECT e.event_date FROM scheduled_events e
                JOIN trading_days t ON t.date = e.event_date
                WHERE e.event_type='fomc' AND e.event_date='2020-04-29'
                """
            )
        ).scalar_one_or_none()
        if fomc_on:
            rows = conn.execute(
                text(
                    """
                    SELECT date, days_since_last_fomc FROM calendar_context
                    WHERE date IN ('2020-04-28','2020-04-29','2020-04-30','2020-05-01')
                    ORDER BY date
                    """
                )
            ).all()
            print("FOMC 2020-04-29 window:", rows)
            expected = {
                dt.date(2020, 4, 29): 0,
                dt.date(2020, 4, 30): 1,
                dt.date(2020, 5, 1): 2,
            }
            ok13 = all(
                dict(rows).get(d) == v for d, v in expected.items() if d in dict(rows)
            )
            check("inv13", ok13, "FOMC T=0 T+1=1 T+2=2 on-calendar")

        # --- history floors ---
        _section("Invariant 14 — History floors")
        floors = {
            "cpi": (dt.date(1972, 7, 21), "days_since_last_cpi"),
            "employment_situation": (dt.date(1960, 3, 15), "days_since_last_employment_situation"),
            "election": (dt.date(1958, 11, 5), "days_since_last_election"),
        }
        for etype, (first_eff, col) in floors.items():
            before = conn.execute(
                text(
                    f"""
                    SELECT COUNT(*) FROM calendar_context
                    WHERE date < :d AND {col} IS NOT NULL
                    """
                ),
                {"d": first_eff},
            ).scalar_one()
            at = conn.execute(
                text(f"SELECT {col} FROM calendar_context WHERE date=:d"),
                {"d": first_eff},
            ).scalar_one()
            print(f"  {etype}: before {first_eff} non-null={before}; at {first_eff}={at}")
            check(
                f"inv14-{etype}",
                before == 0 and at == 0,
                f"NULL before floor; days_since=0 at first effective anchor",
            )

        pre_cpi = conn.execute(
            text(
                "SELECT days_since_last_cpi, is_cpi_release_day "
                "FROM calendar_context WHERE date='1957-01-02'"
            )
        ).one()
        check(
            "inv14-cpi-spine",
            pre_cpi[0] is None and pre_cpi[1] is False,
            "1957-01-02 CPI NULL/FALSE",
        )

        # --- multi-family ---
        _section("Invariant 15 — Multi-family dates")
        multi = conn.execute(
            text(
                """
                SELECT COUNT(*) FROM calendar_context
                WHERE (is_fomc_day::int + is_cpi_release_day::int
                       + is_employment_situation_day::int + is_election_day::int) > 1
                """
            )
        ).scalar_one()
        samples = conn.execute(
            text(
                """
                SELECT date, is_fomc_day, is_cpi_release_day,
                       is_employment_situation_day, is_election_day
                FROM calendar_context
                WHERE (is_fomc_day::int + is_cpi_release_day::int
                       + is_employment_situation_day::int + is_election_day::int) > 1
                ORDER BY date LIMIT 3
                """
            )
        ).all()
        print(f"multi-family count={multi} samples={samples}")
        check("inv15", multi >= 1, f"multi-family trading days={multi}")

        # --- release session independence (inv16) ---
        _section("Invariant 16 — Release session independence")
        # Derivation code does not read release_session — document + sanity check
        pre_open_cpi = conn.execute(
            text(
                """
                SELECT c.date, c.is_cpi_release_day, c.days_since_last_cpi,
                       e.release_session
                FROM calendar_context c
                JOIN scheduled_events e ON e.event_date = c.date AND e.event_type='cpi'
                WHERE e.release_session = 'pre_open'
                LIMIT 1
                """
            )
        ).mappings().first()
        during_fomc = conn.execute(
            text(
                """
                SELECT c.date, c.is_fomc_day, c.days_since_last_fomc,
                       e.release_session
                FROM calendar_context c
                JOIN scheduled_events e ON e.event_date = c.date AND e.event_type='fomc'
                WHERE e.release_session = 'during_session'
                LIMIT 1
                """
            )
        ).mappings().first()
        print("pre_open CPI sample:", dict(pre_open_cpi) if pre_open_cpi else None)
        print("during_session FOMC sample:", dict(during_fomc) if during_fomc else None)
        check(
            "inv16",
            pre_open_cpi is not None
            and pre_open_cpi["is_cpi_release_day"]
            and pre_open_cpi["days_since_last_cpi"] == 0,
            "release_session does not suppress same-day flag/distance",
        )

        # --- shortened trading days ---
        _section("Invariant 5 — Shortened trading days")
        ec = early_close_dates(trading_days[0], trading_days[-1])
        flagged = conn.execute(
            text(
                "SELECT date FROM calendar_context WHERE is_shortened_trading_day ORDER BY date"
            )
        ).all()
        flagged_set = {r[0] for r in flagged}
        expected_ec = ec.intersection(trading_set)
        check(
            "inv5",
            flagged_set == expected_ec,
            f"early_close flagged={len(flagged_set)} nyse_intersect_spine={len(expected_ec)}",
        )

        # --- holiday adjacency (inv3) ---
        _section("Invariant 3 — Holiday adjacency")
        # Normal weekend Fri->Mon must not set holiday flags
        wknd = conn.execute(
            text(
                """
                SELECT c.is_day_before_holiday, c.is_day_after_holiday, c.holiday_name
                FROM calendar_context c
                WHERE c.date = '2024-03-22'
                """
            )
        ).one()
        check(
            "inv3-weekend",
            wknd[0] is False and wknd[1] is False and wknd[2] is None,
            "2024-03-22 Fri->Mon weekend-only: no holiday flags",
        )
        # Good Friday: closed weekday between sessions
        gf_before = conn.execute(
            text(
                """
                SELECT is_day_before_holiday, holiday_name, holiday_type
                FROM calendar_context WHERE date = '2024-03-28'
                """
            )
        ).one()
        gf_after = conn.execute(
            text(
                """
                SELECT is_day_after_holiday, holiday_name, holiday_type
                FROM calendar_context WHERE date = '2024-04-01'
                """
            )
        ).one()
        check(
            "inv3-regular",
            gf_before[0] is True
            and gf_after[0] is True
            and gf_before[2] == "regular",
            "Good Friday 2024 adjacency regular holiday",
        )
        exc = conn.execute(
            text(
                """
                SELECT is_day_before_holiday, holiday_type
                FROM calendar_context WHERE date = '2001-09-10'
                """
            )
        ).one()
        check(
            "inv3-exceptional",
            exc[0] is True and exc[1] == "exceptional",
            "9/11 week exceptional closure adjacency",
        )

        # --- event coverage cross-check ---
        _section("Event coverage cross-check")
        for etype in FLAG_MAP:
            total = conn.execute(
                text("SELECT COUNT(*) FROM scheduled_events WHERE event_type=:t"),
                {"t": etype},
            ).scalar_one()
            on_cal = conn.execute(
                text(
                    """
                    SELECT COUNT(*) FROM scheduled_events e
                    JOIN trading_days t ON t.date = e.event_date
                    WHERE e.event_type = :t
                    """
                ),
                {"t": etype},
            ).scalar_one()
            print(
                f"  {etype}: total={total} on_calendar={on_cal} "
                f"off_calendar={total - on_cal} flags={conn.execute(text(f'SELECT COUNT(*) FROM calendar_context WHERE {FLAG_MAP[etype]}')).scalar_one()}"
            )

        # --- deterministic hash ---
        _section("Invariant 18 — Deterministic snapshot hash")
        rows = conn.execute(
            text(
                """
                SELECT * FROM calendar_context ORDER BY date
                """
            )
        ).mappings().all()
        payload = json.dumps([dict(r) for r in rows], default=str, sort_keys=True)
        digest = hashlib.sha256(payload.encode()).hexdigest()
        print(f"row_hash_sha256={digest[:16]}... (full {len(digest)} chars)")
        invariant["inv18"] = "PASS (snapshot recorded; compare after rebuild)"

        # --- spot checks ---
        _section("Historical edge-case spot checks")
        # Good Friday 2024
        gf = conn.execute(
            text(
                """
                SELECT date, is_day_before_holiday, is_day_after_holiday,
                       holiday_name, holiday_type
                FROM calendar_context
                WHERE date IN ('2024-03-28','2024-04-01')
                ORDER BY date
                """
            )
        ).all()
        print("Good Friday 2024:", gf)

        # 9/11 exceptional
        exc = conn.execute(
            text(
                """
                SELECT date, is_day_before_holiday, is_day_after_holiday,
                       holiday_type, trading_days_in_week
                FROM calendar_context
                WHERE date IN ('2001-09-10','2001-09-17')
                ORDER BY date
                """
            )
        ).all()
        print("9/11 closure:", exc)

        # Thanksgiving early close 2023
        tg = conn.execute(
            text(
                """
                SELECT date, is_shortened_trading_day, trading_days_in_week,
                       is_shortened_week
                FROM calendar_context
                WHERE date IN ('2023-11-22','2023-11-24','2023-11-27')
                ORDER BY date
                """
            )
        ).all()
        print("Thanksgiving 2023 week:", tg)

        # Leap year Feb 2024
        leap = conn.execute(
            text(
                """
                SELECT c.date, c.is_turn_of_month, t.is_month_end, t.trading_day_of_month
                FROM calendar_context c
                JOIN trading_days t ON t.date = c.date
                WHERE c.date IN ('2024-02-29','2024-03-01')
                ORDER BY c.date
                """
            )
        ).all()
        print("Leap Feb 2024 boundary:", leap)

        # Weekend month end: Jan 2022 ends Monday 31; last trading day Jan 31
        wme = conn.execute(
            text(
                """
                SELECT c.date, c.is_turn_of_month, t.is_month_end
                FROM calendar_context c
                JOIN trading_days t ON t.date = c.date
                WHERE c.date IN ('2022-01-31','2022-02-01')
                ORDER BY c.date
                """
            )
        ).all()
        print("Jan 2022 month boundary:", wme)

        # Multi-family example with distances
        if samples:
            d0 = samples[0][0]
            mf = conn.execute(
                text(
                    """
                    SELECT date, is_fomc_day, is_cpi_release_day,
                           is_employment_situation_day, days_since_last_fomc,
                           days_since_last_cpi, days_since_last_employment_situation
                    FROM calendar_context WHERE date=:d
                    """
                ),
                {"d": d0},
            ).mappings().first()
            print("Multi-family detail:", dict(mf))

    _section("Invariant summary")
    for k in sorted(invariant):
        print(f"  {k}: {invariant[k]}")

    if failures:
        print(f"\nAUDIT FAILED ({len(failures)} issues)")
        for f in failures:
            print(f"  - {f}")
        return 1

    print("\nAUDIT PASS — all checked invariants satisfied")
    return 0


if __name__ == "__main__":
    sys.exit(main())
