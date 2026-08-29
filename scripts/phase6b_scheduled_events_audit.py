"""Phase 6B scheduled_events audit queries and spot checks."""

from __future__ import annotations

import datetime as dt

from sqlalchemy import text

from stockballdb.config import load_settings
from stockballdb.db import get_engine, reset_engine
from stockballdb.events.types import make_event_id
from stockballdb.macro.pit import VintageRow, first_print_events, parse_alfred_rows
from stockballdb.providers.fred import fetch_all_vintages


def _print_section(title: str) -> None:
    print(f"\n=== {title} ===")


def main() -> None:
    settings = load_settings(require_database_url=True)
    reset_engine()
    engine = get_engine(settings)

    with engine.connect() as conn:
        total = conn.execute(text("SELECT COUNT(*) FROM scheduled_events")).scalar_one()
        print(f"total scheduled_events={total}")

        by_type = conn.execute(
            text(
                """
                SELECT event_type, COUNT(*) AS n,
                       MIN(event_date) AS first_d, MAX(event_date) AS last_d,
                       COUNT(event_time_et) AS timed,
                       COUNT(reference_period) AS with_ref
                FROM scheduled_events
                GROUP BY event_type ORDER BY event_type
                """
            )
        ).mappings().all()
        for r in by_type:
            print(dict(r))

        dup_id = conn.execute(
            text(
                """
                SELECT COUNT(*) FROM (
                  SELECT event_id FROM scheduled_events GROUP BY event_id HAVING COUNT(*)>1
                ) d
                """
            )
        ).scalar_one()
        dup_occ = conn.execute(
            text(
                """
                SELECT COUNT(*) FROM (
                  SELECT event_type, event_date, reference_period, symbol
                  FROM scheduled_events GROUP BY 1,2,3,4 HAVING COUNT(*)>1
                ) d
                """
            )
        ).scalar_one()
        print(f"duplicate event_id={dup_id} duplicate occurrences={dup_occ}")

        off_cal = conn.execute(
            text(
                """
                SELECT e.event_type, e.event_date, e.reference_period
                FROM scheduled_events e
                LEFT JOIN trading_days t ON t.date = e.event_date
                WHERE t.date IS NULL
                ORDER BY e.event_date
                LIMIT 15
                """
            )
        ).all()
        off_count = conn.execute(
            text(
                """
                SELECT COUNT(*) FROM scheduled_events e
                LEFT JOIN trading_days t ON t.date = e.event_date
                WHERE t.date IS NULL
                """
            )
        ).scalar_one()
        print(f"events on non-trading days: {off_count}")
        for row in off_cal[:10]:
            print("  off-calendar:", row)

        _print_section("FOMC spot checks")
        for label, d in [
            ("early 1957", dt.date(1957, 1, 8)),
            ("pre-2013", dt.date(2012, 12, 12)),
            ("modern 2020", dt.date(2020, 4, 29)),
            ("modern 2024", dt.date(2024, 12, 18)),
        ]:
            row = conn.execute(
                text(
                    """
                    SELECT event_id, event_date, event_time_et, release_session, source
                    FROM scheduled_events WHERE event_type='fomc' AND event_date=:d
                    """
                ),
                {"d": d},
            ).mappings().first()
            print(label, dict(row) if row else "MISSING")

        forbidden = conn.execute(
            text(
                """
                SELECT event_date FROM scheduled_events
                WHERE event_type='fomc' AND event_date IN (
                  '2020-03-02','2020-03-15','2020-03-19','2020-03-23','2020-03-31'
                )
                """
            )
        ).all()
        print("forbidden unscheduled FOMC dates present:", forbidden or "none")

        _print_section("CPI spot checks")
        for ref, d in [
            ("1985-06", dt.date(1985, 7, 23)),
            ("2008-07", dt.date(2008, 8, 14)),
            ("2020-02", dt.date(2020, 3, 11)),
        ]:
            row = conn.execute(
                text(
                    """
                    SELECT event_id, reference_period, event_date, event_time_et,
                           release_session, source
                    FROM scheduled_events
                    WHERE event_type='cpi' AND reference_period=:ref
                    """
                ),
                {"ref": ref},
            ).mappings().first()
            print(f"ref={ref} expected~{d}", dict(row) if row else "MISSING")

        _print_section("Employment spot checks")
        for ref, d in [
            ("1960-01", dt.date(1960, 3, 15)),
            ("2008-09", dt.date(2008, 10, 3)),
            ("2020-02", dt.date(2020, 3, 6)),
        ]:
            row = conn.execute(
                text(
                    """
                    SELECT event_id, reference_period, event_date, event_time_et,
                           release_session, source
                    FROM scheduled_events
                    WHERE event_type='employment_situation' AND reference_period=:ref
                    """
                ),
                {"ref": ref},
            ).mappings().first()
            print(f"ref={ref} expected~{d}", dict(row) if row else "MISSING")

        _print_section("Election spot checks")
        for year, kind in [(2008, "presidential"), (2010, "midterm"), (2020, "presidential")]:
            row = conn.execute(
                text(
                    """
                    SELECT event_id, event_date, reference_period, event_time_et,
                           release_session, source
                    FROM scheduled_events
                    WHERE event_type='election' AND reference_period=:kind
                      AND EXTRACT(YEAR FROM event_date)=:year
                    """
                ),
                {"kind": kind, "year": year},
            ).mappings().first()
            print(f"{year} {kind}", dict(row) if row else "MISSING")

        odd_elections = conn.execute(
            text(
                """
                SELECT COUNT(*) FROM scheduled_events
                WHERE event_type='election' AND EXTRACT(YEAR FROM event_date) % 2 = 1
                """
            )
        ).scalar_one()
        print("odd-year elections:", odd_elections)

        _print_section("Calendar context off-calendar effective session")
        if off_cal:
            etype, edate, _ = off_cal[0]
            eff = conn.execute(
                text(
                    """
                    SELECT MIN(t.date) FROM trading_days t WHERE t.date > :ed
                    """
                ),
                {"ed": edate},
            ).scalar_one()
            since = conn.execute(
                text(
                    f"""
                    SELECT date, days_since_last_{etype.replace('employment_situation','employment_situation')}
                    FROM calendar_context
                    WHERE date = :eff
                    """
                ),
                {"eff": eff},
            ).first()
            # use dynamic column name safely
            col = {
                "fomc": "days_since_last_fomc",
                "cpi": "days_since_last_cpi",
                "employment_situation": "days_since_last_employment_situation",
                "election": "days_since_last_election",
            }[etype]
            since = conn.execute(
                text(
                    f"SELECT date, {col}, is_{etype}_day FROM calendar_context WHERE date=:eff"
                ),
                {"eff": eff},
            ).mappings().first()
            print(f"off-calendar {etype} {edate} -> effective {eff}", dict(since))

    if settings.fred_api_key:
        _print_section("ALFRED cross-check CPI 2020-02")
        rows = fetch_all_vintages("CPIAUCSL", settings.fred_api_key)
        vintages = parse_alfred_rows(rows)
        fps = first_print_events(vintages)
        feb = [
            (rt, ref, val)
            for rt, ref, val in fps
            if ref == dt.date(2020, 2, 1)
        ]
        print("ALFRED first prints for 2020-02 ref:", feb[:3])

    _print_section("event_id determinism sample")
    eid = make_event_id("cpi", dt.date(2020, 3, 11), "2020-02", None)
    print("expected cpi id:", eid)


if __name__ == "__main__":
    main()
