"""Phase 5B WTI audit queries."""

from __future__ import annotations

from sqlalchemy import text

from stockballdb.config import load_settings
from stockballdb.db import get_engine, reset_engine
from stockballdb.providers.fred import fetch_current_observations


def main() -> None:
    settings = load_settings(require_database_url=True)
    reset_engine()
    engine = get_engine(settings)
    with engine.connect() as conn:
        summary = conn.execute(
            text(
                """
                SELECT COUNT(*) AS rows, MIN(date) AS first_date, MAX(date) AS last_date,
                  COUNT(open) AS open_nn, COUNT(high) AS high_nn, COUNT(close) AS close_nn,
                  COUNT(return_1d) AS return_1d_nn, COUNT(gap_pct) AS gap_nn,
                  COUNT(intraday_return) AS intraday_nn, COUNT(range_pct) AS range_nn,
                  COUNT(drawdown_from_high) AS dd_nn
                FROM daily_market_data WHERE symbol='WTI'
                """
            )
        ).mappings().one()
        print("WTI summary:", dict(summary))

        for label, sql in [
            (
                "normal 2024",
                "SELECT date, close FROM daily_market_data WHERE symbol='WTI' "
                "AND date BETWEEN '2024-06-03' AND '2024-06-07' ORDER BY date",
            ),
            (
                "2008",
                "SELECT date, close FROM daily_market_data WHERE symbol='WTI' "
                "AND date BETWEEN '2008-07-01' AND '2008-07-05' ORDER BY date",
            ),
            (
                "apr2020",
                "SELECT date, close FROM daily_market_data WHERE symbol='WTI' "
                "AND date BETWEEN '2020-04-17' AND '2020-04-22' ORDER BY date",
            ),
            (
                "recent",
                "SELECT date, close FROM daily_market_data WHERE symbol='WTI' "
                "ORDER BY date DESC LIMIT 5",
            ),
        ]:
            rows = conn.execute(text(sql)).all()
            print(label, rows)

        neg = conn.execute(
            text(
                "SELECT date, close FROM daily_market_data "
                "WHERE symbol='WTI' AND close < 0"
            )
        ).all()
        print("negative rows", neg)

        etf_bad = conn.execute(
            text(
                """
                SELECT COUNT(*) FROM daily_market_data
                WHERE symbol <> 'WTI' AND (
                  open IS NULL OR high IS NULL OR low IS NULL OR volume IS NULL
                  OR adj_open IS NULL OR adj_close IS NULL OR split_factor IS NULL
                )
                """
            )
        ).scalar_one()
        print("malformed ETF rows", etf_bad)

    fred_neg = [
        r
        for r in fetch_current_observations("DCOILWTICO", settings.fred_api_key)
        if r.get("date") == "2020-04-20"
    ]
    print("FRED 2020-04-20", fred_neg)


if __name__ == "__main__":
    main()
