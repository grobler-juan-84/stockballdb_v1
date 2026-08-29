"""Live coverage reporting."""

from __future__ import annotations

import datetime as dt

from sqlalchemy import text
from sqlalchemy.engine import Connection

from stockballdb.health.models import SymbolCoverage, TableCoverage
from stockballdb.market_data.universe import (
    asset_type_for_symbol,
    is_close_only_symbol,
    V1_MARKET_SYMBOLS,
)

TABLE_GRAINS = {
    "trading_days": "trading day",
    "daily_market_data": "date × symbol",
    "market_outcomes": "date × symbol",
    "asset_regimes": "date × symbol",
    "macro_conditions": "trading day",
    "scheduled_events": "event",
    "calendar_context": "trading day",
}


def collect_table_coverage(conn: Connection) -> list[TableCoverage]:
    out: list[TableCoverage] = []
    for table in TABLE_GRAINS:
        if table == "scheduled_events":
            row = conn.execute(
                text(
                    """
                    SELECT COUNT(*) AS n,
                           MIN(event_date) AS first_d,
                           MAX(event_date) AS last_d
                    FROM scheduled_events
                    """
                )
            ).one()
        else:
            row = conn.execute(
                text(
                    f"""
                    SELECT COUNT(*) AS n,
                           MIN(date) AS first_d,
                           MAX(date) AS last_d
                    FROM {table}
                    """
                )
            ).one()
        out.append(
            TableCoverage(
                table=table,
                grain=TABLE_GRAINS[table],
                row_count=int(row[0]),
                first_date=row[1],
                last_date=row[2],
            )
        )
    return out


def _max_run_trading_gap(missing: list[dt.date], trading_days: list[dt.date]) -> int:
    if not missing:
        return 0
    idx = {d: i for i, d in enumerate(trading_days)}
    missing_sorted = sorted(d for d in missing if d in idx)
    if not missing_sorted:
        return len(missing)
    best = run = 1
    for i in range(1, len(missing_sorted)):
        if idx[missing_sorted[i]] == idx[missing_sorted[i - 1]] + 1:
            run += 1
        else:
            run = 1
        best = max(best, run)
    return best


def collect_symbol_coverage(
    conn: Connection,
    trading_days: list[dt.date],
) -> list[SymbolCoverage]:
    rows = conn.execute(
        text(
            """
            SELECT symbol, MIN(date) AS first_d, MAX(date) AS last_d, COUNT(*) AS n
            FROM daily_market_data
            GROUP BY symbol
            ORDER BY symbol
            """
        )
    ).mappings().all()
    by_symbol = {r["symbol"]: r for r in rows}
    out: list[SymbolCoverage] = []

    for symbol in V1_MARKET_SYMBOLS:
        r = by_symbol.get(symbol)
        if r is None:
            continue
        first_d, last_d = r["first_d"], r["last_d"]
        eligible = [d for d in trading_days if first_d <= d <= last_d]
        present = conn.execute(
            text(
                """
                SELECT date FROM daily_market_data
                WHERE symbol = :sym AND date >= :start AND date <= :end
                """
            ),
            {"sym": symbol, "start": first_d, "end": last_d},
        ).scalars().all()
        present_set = set(present)
        missing = [d for d in eligible if d not in present_set]
        eligible_n = len(eligible)
        row_count = int(r["n"])
        cov = 100.0 * row_count / eligible_n if eligible_n else 0.0
        max_run = _max_run_trading_gap(missing, trading_days)
        samples = [d.isoformat() for d in sorted(missing)[:5]]
        out.append(
            SymbolCoverage(
                symbol=symbol,
                asset_type=asset_type_for_symbol(symbol),
                first_date=first_d,
                last_date=last_d,
                row_count=row_count,
                eligible_sessions=eligible_n,
                coverage_pct=round(cov, 2),
                internal_missing_sessions=len(missing),
                max_consecutive_missing=max_run,
                sample_missing_dates=samples,
            )
        )
    return out


def load_trading_days(conn: Connection) -> list[dt.date]:
    return list(conn.execute(text("SELECT date FROM trading_days ORDER BY date")).scalars())
