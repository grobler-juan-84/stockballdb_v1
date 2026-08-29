"""Phase 8A whole-DB health audit — live PostgreSQL inspection for contract evidence."""

from __future__ import annotations

import datetime as dt
import json
import sys

from sqlalchemy import text

from stockballdb.config import load_settings
from stockballdb.db import get_engine, reset_engine
from stockballdb.market_data.universe import (
    CLOSE_ONLY_SYMBOLS,
    PHASE_2A_ETF_SYMBOLS,
    V1_MARKET_SYMBOLS,
)
from stockballdb.macro.series import MACRO_SERIES
from stockballdb.v1.preflight import V1_ALEMBIC_HEAD


def _section(title: str) -> None:
    print(f"\n=== {title} ===")


def main() -> int:
    settings = load_settings(require_database_url=True)
    reset_engine()
    engine = get_engine(settings)
    today = dt.date.today()
    warnings: list[str] = []
    infos: list[str] = []

    with engine.connect() as conn:
        _section("Seven-table inventory")
        tables = [
            "trading_days",
            "daily_market_data",
            "market_outcomes",
            "asset_regimes",
            "macro_conditions",
            "scheduled_events",
            "calendar_context",
        ]
        for t in tables:
            if t == "scheduled_events":
                row = conn.execute(
                    text(
                        """
                        SELECT COUNT(*) AS n,
                               MIN(event_date) AS first_d,
                               MAX(event_date) AS last_d
                        FROM scheduled_events
                        """
                    )
                ).mappings().first()
            else:
                row = conn.execute(
                    text(
                        f"""
                        SELECT COUNT(*) AS n,
                               MIN(date) AS first_d,
                               MAX(date) AS last_d
                        FROM {t}
                        """
                    )
                ).mappings().first()
            print(f"{t}: rows={row['n']} first={row['first_d']} last={row['last_d']}")

        rev = conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        print(f"alembic_head={rev} expected={V1_ALEMBIC_HEAD} match={rev == V1_ALEMBIC_HEAD}")

        td_max = conn.execute(text("SELECT MAX(date) FROM trading_days")).scalar_one()
        cal_n = conn.execute(text("SELECT COUNT(*) FROM calendar_context")).scalar_one()
        td_n = conn.execute(text("SELECT COUNT(*) FROM trading_days")).scalar_one()
        macro_n = conn.execute(text("SELECT COUNT(*) FROM macro_conditions")).scalar_one()
        print(f"spine_1to1: trading_days={td_n} macro={macro_n} calendar={cal_n}")

        _section("Market data per symbol")
        per_sym = conn.execute(
            text(
                """
                SELECT symbol,
                       MIN(date) AS first_d,
                       MAX(date) AS last_d,
                       COUNT(*) AS n
                FROM daily_market_data
                GROUP BY symbol
                ORDER BY symbol
                """
            )
        ).mappings().all()
        dmd_max = conn.execute(text("SELECT MAX(date) FROM daily_market_data")).scalar_one()
        for r in per_sym:
            sym = r["symbol"]
            eligible = conn.execute(
                text(
                    """
                    SELECT COUNT(*) FROM trading_days t
                    WHERE t.date >= :start AND t.date <= :end
                    """
                ),
                {"start": r["first_d"], "end": r["last_d"]},
            ).scalar_one()
            cov_pct = 100.0 * r["n"] / eligible if eligible else 0.0
            lag = (dmd_max - r["last_d"]).days if r["last_d"] and dmd_max else None
            print(
                f"  {sym}: rows={r['n']} {r['first_d']}->{r['last_d']} "
                f"coverage_in_span={cov_pct:.1f}% eligible_td={eligible}"
            )
            if sym in CLOSE_ONLY_SYMBOLS and lag and lag > 0:
                infos.append(f"{sym} last date {r['last_d']} lags spine max {dmd_max} by {lag} calendar days")
            if sym not in CLOSE_ONLY_SYMBOLS and r["n"] < eligible:
                gap = eligible - r["n"]
                if gap > 5:
                    warnings.append(f"{sym} missing {gap} sessions inside active span")

        _section("Macro field coverage")
        macro_fields = [
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
        ]
        macro_max = conn.execute(text("SELECT MAX(date) FROM macro_conditions")).scalar_one()
        for f in macro_fields:
            stats = conn.execute(
                text(
                    f"""
                    SELECT COUNT(*) FILTER (WHERE {f} IS NOT NULL) AS nn,
                           MIN(date) FILTER (WHERE {f} IS NOT NULL) AS first_nn,
                           MAX(date) FILTER (WHERE {f} IS NOT NULL) AS last_nn
                    FROM macro_conditions
                    """
                )
            ).mappings().first()
            pct = 100.0 * stats["nn"] / td_n if td_n else 0
            print(
                f"  {f}: non_null={stats['nn']} ({pct:.1f}%) "
                f"first={stats['first_nn']} last={stats['last_nn']}"
            )

        _section("Scheduled events by family")
        ev = conn.execute(
            text(
                """
                SELECT event_type,
                       COUNT(*) AS total,
                       MIN(event_date) AS first_d,
                       MAX(event_date) AS last_d,
                       COUNT(*) FILTER (WHERE event_time_et IS NOT NULL) AS timed,
                       COUNT(DISTINCT event_date) AS distinct_dates
                FROM scheduled_events
                GROUP BY event_type ORDER BY event_type
                """
            )
        ).mappings().all()
        for r in ev:
            on_cal = conn.execute(
                text(
                    """
                    SELECT COUNT(DISTINCT e.event_date)
                    FROM scheduled_events e
                    JOIN trading_days t ON t.date = e.event_date
                    WHERE e.event_type = :t
                    """
                ),
                {"t": r["event_type"]},
            ).scalar_one()
            off = r["total"] - conn.execute(
                text(
                    """
                    SELECT COUNT(*) FROM scheduled_events e
                    JOIN trading_days t ON t.date = e.event_date
                    WHERE e.event_type = :t
                    """
                ),
                {"t": r["event_type"]},
            ).scalar_one()
            future = conn.execute(
                text(
                    """
                    SELECT COUNT(*) FROM scheduled_events
                    WHERE event_type = :t AND event_date > :today
                    """
                ),
                {"t": r["event_type"], "today": today},
            ).scalar_one()
            print(
                f"  {r['event_type']}: total={r['total']} distinct_dates={r['distinct_dates']} "
                f"on_cal_flags={on_cal} off_cal_rows={off} timed={r['timed']} "
                f"future={future} last={r['last_d']}"
            )
            if future:
                infos.append(
                    f"scheduled_events.{r['event_type']} includes {future} future-dated rows (by design for FOMC calendar)"
                )

        off_all = conn.execute(
            text(
                """
                SELECT COUNT(*) FROM scheduled_events e
                LEFT JOIN trading_days t ON t.date = e.event_date
                WHERE t.date IS NULL
                """
            )
        ).scalar_one()
        print(f"total off-calendar event rows={off_all}")

        _section("Derived table alignment")
        dmd_n = conn.execute(text("SELECT COUNT(*) FROM daily_market_data")).scalar_one()
        mo_n = conn.execute(text("SELECT COUNT(*) FROM market_outcomes")).scalar_one()
        ar_n = conn.execute(text("SELECT COUNT(*) FROM asset_regimes")).scalar_one()
        print(f"daily_market_data={dmd_n} market_outcomes={mo_n} asset_regimes={ar_n} aligned={dmd_n == mo_n == ar_n}")

        _section("Cross-table integrity quick checks")
        checks = {
            "orphan_outcomes": """
                SELECT COUNT(*) FROM market_outcomes o
                LEFT JOIN daily_market_data d ON d.date=o.date AND d.symbol=o.symbol
                WHERE d.date IS NULL
            """,
            "orphan_regimes": """
                SELECT COUNT(*) FROM asset_regimes a
                LEFT JOIN daily_market_data d ON d.date=a.date AND d.symbol=a.symbol
                WHERE d.date IS NULL
            """,
            "dmd_outside_td": """
                SELECT COUNT(*) FROM daily_market_data d
                LEFT JOIN trading_days t ON t.date=d.date WHERE t.date IS NULL
            """,
            "malformed_etf": """
                SELECT COUNT(*) FROM daily_market_data
                WHERE symbol <> ALL(:close_only)
                  AND (open IS NULL OR adj_close IS NULL OR volume IS NULL)
            """,
            "malformed_wti": """
                SELECT COUNT(*) FROM daily_market_data
                WHERE symbol = ANY(:close_only)
                  AND (open IS NOT NULL OR adj_close IS NOT NULL OR close IS NULL)
            """,
        }
        params = {"close_only": list(CLOSE_ONLY_SYMBOLS)}
        for name, sql in checks.items():
            n = conn.execute(text(sql), params).scalar_one()
            status = "PASS" if n == 0 else "FAIL"
            print(f"  {name}: {n} [{status}]")
            if n:
                warnings.append(f"{name}={n}")

        _section("Freshness vs trading spine")
        print(f"trading_days max={td_max} (today={today})")
        for label, sql in [
            ("etf_max", "SELECT MAX(date) FROM daily_market_data WHERE symbol <> ALL(:co)"),
            ("wti_max", "SELECT MAX(date) FROM daily_market_data WHERE symbol = ANY(:co)"),
            ("macro_max", "SELECT MAX(date) FROM macro_conditions"),
            ("events_max", "SELECT MAX(event_date) FROM scheduled_events"),
        ]:
            v = conn.execute(text(sql), {"co": list(CLOSE_ONLY_SYMBOLS)}).scalar_one()
            print(f"  {label}={v}")

        _section("Provenance persistence audit")
        provenance_cols = conn.execute(
            text(
                """
                SELECT table_name, column_name
                FROM information_schema.columns
                WHERE table_schema = current_schema()
                  AND column_name IN (
                    'source', 'updated_at', 'created_at', 'retrieved_at',
                    'build_id', 'provider', 'series_id'
                  )
                ORDER BY table_name, column_name
                """
            )
        ).all()
        print("DB columns with provenance-like names:", provenance_cols or "none beyond scheduled_events.source")

        _section("Multi-family calendar days")
        multi = conn.execute(
            text(
                """
                SELECT COUNT(*) FROM calendar_context
                WHERE (is_fomc_day::int + is_cpi_release_day::int
                       + is_employment_situation_day::int + is_election_day::int) > 1
                """
            )
        ).scalar_one()
        print(f"multi_family_trading_days={multi}")

    _section("Summary classification")
    print("EXPECTED INFOS:")
    for i in infos:
        print(f"  INFO: {i}")
    print("WARNINGS:")
    if warnings:
        for w in warnings:
            print(f"  WARNING: {w}")
    else:
        print("  (none)")
    health = "HEALTHY WITH WARNINGS" if warnings else "HEALTHY"
    print(f"\nOVERALL: {health}")
    return 1 if any("FAIL" in w for w in warnings) else 0


if __name__ == "__main__":
    sys.exit(main())
