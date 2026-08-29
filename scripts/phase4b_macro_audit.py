"""Phase 4B macro_conditions verification (read-only DB audit)."""

from __future__ import annotations

import datetime as dt
import sys

from dotenv import load_dotenv
from sqlalchemy import text

from stockballdb.config import load_settings
from stockballdb.db import get_engine, reset_engine
from stockballdb.macro.series import MACRO_SERIES

FIELDS = [
    "inflation_rate",
    "core_inflation_rate",
    "unemployment_rate",
    "jobless_claims",
    "fed_funds_rate",
    "treasury_2y_yield",
    "treasury_10y_yield",
    "yield_curve_10y_2y",
    "fed_balance_sheet",
    "credit_spread",
    "inflation_regime",
    "rate_regime",
]


def coverage(engine) -> None:
    td = engine.connect().execute(text("SELECT COUNT(*) FROM trading_days")).scalar_one()
    print("=== COVERAGE ===")
    print(f"trading_days={td}")
    with engine.connect() as conn:
        for f in FIELDS:
            row = conn.execute(
                text(
                    f"""
                    SELECT
                      MIN(date) FILTER (WHERE {f} IS NOT NULL) AS first_d,
                      MAX(date) FILTER (WHERE {f} IS NOT NULL) AS last_d,
                      COUNT(*) FILTER (WHERE {f} IS NOT NULL) AS nn,
                      COUNT(*) FILTER (WHERE {f} IS NULL) AS nnull
                    FROM macro_conditions
                    """
                )
            ).mappings().one()
            pct = 100.0 * row["nn"] / td if td else 0
            print(
                f"{f}: first={row['first_d']} last={row['last_d']} "
                f"non_null={row['nn']} null={row['nnull']} pct={pct:.1f}%"
            )


def grain(engine) -> None:
    print("\n=== GRAIN ===")
    with engine.connect() as conn:
        mc = conn.execute(text("SELECT COUNT(*) FROM macro_conditions")).scalar_one()
        td = conn.execute(text("SELECT COUNT(*) FROM trading_days")).scalar_one()
        dup = conn.execute(
            text("SELECT COUNT(*) - COUNT(DISTINCT date) FROM macro_conditions")
        ).scalar_one()
        orphan = conn.execute(
            text(
                """
                SELECT COUNT(*) FROM macro_conditions m
                LEFT JOIN trading_days t ON t.date = m.date
                WHERE t.date IS NULL
                """
            )
        ).scalar_one()
        outside = conn.execute(
            text(
                """
                SELECT COUNT(*) FROM macro_conditions m
                WHERE EXTRACT(DOW FROM m.date) IN (0, 6)
                """
            )
        ).scalar_one()
        min_d, max_d = conn.execute(
            text("SELECT MIN(date), MAX(date) FROM macro_conditions")
        ).one()
        has_pmi = conn.execute(
            text(
                """
                SELECT COUNT(*) FROM information_schema.columns
                WHERE table_name='macro_conditions' AND column_name='pmi'
                """
            )
        ).scalar_one()
    print(f"macro_rows={mc} trading_days={td} match={mc == td}")
    print(f"duplicate_dates={dup} orphan_dates={orphan} weekend_rows={outside}")
    print(f"date_range={min_d} -> {max_d} pmi_column={has_pmi > 0}")


def yield_curve(engine) -> None:
    print("\n=== YIELD CURVE ===")
    with engine.connect() as conn:
        bad = conn.execute(
            text(
                """
                SELECT COUNT(*) FROM macro_conditions
                WHERE treasury_10y_yield IS NOT NULL AND treasury_2y_yield IS NOT NULL
                  AND ABS(yield_curve_10y_2y - (treasury_10y_yield - treasury_2y_yield)) > 1e-9
                """
            )
        ).scalar_one()
        null_leg = conn.execute(
            text(
                """
                SELECT COUNT(*) FROM macro_conditions
                WHERE (treasury_10y_yield IS NULL OR treasury_2y_yield IS NULL)
                  AND yield_curve_10y_2y IS NOT NULL
                """
            )
        ).scalar_one()
        samples = conn.execute(
            text(
                """
                SELECT date, treasury_10y_yield, treasury_2y_yield, yield_curve_10y_2y
                FROM macro_conditions
                WHERE yield_curve_10y_2y IS NOT NULL
                ORDER BY yield_curve_10y_2y DESC NULLS LAST
                LIMIT 3
                """
            )
        ).fetchall()
        inv = conn.execute(
            text(
                """
                SELECT date, yield_curve_10y_2y FROM macro_conditions
                WHERE yield_curve_10y_2y < 0
                ORDER BY date DESC LIMIT 3
                """
            )
        ).fetchall()
    print(f"identity_mismatch={bad} null_leg_nonnull_curve={null_leg}")
    print("top_positive_spreads:", samples)
    print("recent_inverted:", inv)


def pit_cpi(engine) -> None:
    print("\n=== PIT CPI SPOT CHECKS ===")
    # Find CPI release dates from scheduled_events + compare macro before/after
    with engine.connect() as conn:
        releases = conn.execute(
            text(
                """
                SELECT e.event_date, e.reference_period
                FROM scheduled_events e
                WHERE e.event_type = 'cpi'
                  AND e.event_date >= '2020-01-01' AND e.event_date <= '2021-12-31'
                ORDER BY e.event_date
                LIMIT 4
                """
            )
        ).fetchall()
        for rel_date, ref in releases[:2]:
            prev_td = conn.execute(
                text(
                    """
                    SELECT MAX(t.date) FROM trading_days t
                    WHERE t.date < :d
                    """
                ),
                {"d": rel_date},
            ).scalar_one()
            on_td = conn.execute(
                text("SELECT 1 FROM trading_days WHERE date = :d"),
                {"d": rel_date},
            ).scalar_one_or_none()
            avail = rel_date if on_td else conn.execute(
                text(
                    "SELECT MIN(date) FROM trading_days WHERE date >= :d"
                ),
                {"d": rel_date},
            ).scalar_one()
            before = conn.execute(
                text(
                    "SELECT inflation_rate FROM macro_conditions WHERE date = :d"
                ),
                {"d": prev_td},
            ).scalar_one()
            after = conn.execute(
                text(
                    "SELECT inflation_rate FROM macro_conditions WHERE date = :d"
                ),
                {"d": avail},
            ).scalar_one()
            print(
                f"ref={ref} release_cal={rel_date} prev_td={prev_td} "
                f"avail_td={avail} inflation_before={before} inflation_after={after}"
            )


def pit_unemployment(engine) -> None:
    print("\n=== PIT UNEMPLOYMENT SPOT CHECKS ===")
    with engine.connect() as conn:
        releases = conn.execute(
            text(
                """
                SELECT event_date, reference_period FROM scheduled_events
                WHERE event_type = 'employment_situation'
                  AND event_date >= '2019-06-01' AND event_date <= '2020-06-30'
                ORDER BY event_date LIMIT 2
                """
            )
        ).fetchall()
        for rel_date, ref in releases:
            prev_td = conn.execute(
                text("SELECT MAX(date) FROM trading_days WHERE date < :d"),
                {"d": rel_date},
            ).scalar_one()
            avail = conn.execute(
                text(
                    """
                    SELECT COALESCE(
                      (SELECT date FROM trading_days WHERE date = :d),
                      (SELECT MIN(date) FROM trading_days WHERE date > :d)
                    )
                    """
                ),
                {"d": rel_date},
            ).scalar_one()
            before = conn.execute(
                text("SELECT unemployment_rate FROM macro_conditions WHERE date = :d"),
                {"d": prev_td},
            ).scalar_one()
            after = conn.execute(
                text("SELECT unemployment_rate FROM macro_conditions WHERE date = :d"),
                {"d": avail},
            ).scalar_one()
            print(
                f"ref={ref} release={rel_date} prev={prev_td} avail={avail} "
                f"unrate_before={before} unrate_after={after}"
            )


def walcl_example(engine) -> None:
    print("\n=== WALCL SPOT CHECK ===")
    with engine.connect() as conn:
        # Find a Wed with WALCL change and show Thu-after-close pattern
        row = conn.execute(
            text(
                """
                WITH w AS (
                  SELECT date, fed_balance_sheet,
                         LAG(fed_balance_sheet) OVER (ORDER BY date) AS prev
                  FROM macro_conditions
                  WHERE fed_balance_sheet IS NOT NULL
                )
                SELECT date, fed_balance_sheet, prev FROM w
                WHERE prev IS NOT NULL AND fed_balance_sheet <> prev
                  AND date >= '2024-01-01'
                ORDER BY date LIMIT 1
                """
            )
        ).mappings().first()
        if row:
            d = row["date"]
            prev = conn.execute(
                text(
                    "SELECT date, fed_balance_sheet FROM macro_conditions "
                    "WHERE date < :d ORDER BY date DESC LIMIT 3"
                ),
                {"d": d},
            ).fetchall()
            print(f"update_td={d} value={row['fed_balance_sheet']} prior_rows={prev}")
        else:
            print("no WALCL update sample found")


def daily_no_fill(engine) -> None:
    print("\n=== DAILY SERIES NO-FORWARD-FILL WINDOW ===")
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT date, fed_funds_rate, treasury_2y_yield, treasury_10y_yield, credit_spread
                FROM macro_conditions
                WHERE date BETWEEN '2024-07-04' AND '2024-07-10'
                ORDER BY date
                """
            )
        ).fetchall()
        for r in rows:
            print(r)
        # Count null gaps in short window for DFF
        gaps = conn.execute(
            text(
                """
                SELECT COUNT(*) FROM macro_conditions
                WHERE date BETWEEN '2024-01-02' AND '2024-01-31'
                  AND fed_funds_rate IS NULL
                """
            )
        ).scalar_one()
        print(f"DFF null days in Jan 2024 window: {gaps}")


def main() -> int:
    load_dotenv()
    settings = load_settings(require_database_url=True)
    reset_engine()
    engine = get_engine(settings)
    grain(engine)
    coverage(engine)
    yield_curve(engine)
    pit_cpi(engine)
    pit_unemployment(engine)
    walcl_example(engine)
    daily_no_fill(engine)
    return 0


if __name__ == "__main__":
    sys.exit(main())
