"""Whole-database V1 validation (no external providers)."""

from __future__ import annotations

import sys

import pandas_market_calendars as mcal
from sqlalchemy import text
from sqlalchemy.engine import Engine

from stockballdb.config import ConfigError, load_settings
from stockballdb.db import get_engine, reset_engine
from stockballdb.logging_config import configure_logging, get_logger
from stockballdb.v1.preflight import REQUIRED_CALENDAR_VERSION, V1_ALEMBIC_HEAD
from stockballdb.v1.report import _pad
from stockballdb.v1.stages import collect_diagnostics


class ValidateV1Error(Exception):
    """Raised when whole-database V1 validation fails."""


def validate_v1_database(engine: Engine) -> list[str]:
    """
    Run hard whole-DB invariants. Returns diagnostic lines.

    Raises ValidateV1Error on the first hard failure.
    """
    diagnostics: list[str] = []

    if mcal.__version__ != REQUIRED_CALENDAR_VERSION:
        raise ValidateV1Error(
            f"pandas_market_calendars must be {REQUIRED_CALENDAR_VERSION}; "
            f"found {mcal.__version__}"
        )
    diagnostics.append(f"calendar={mcal.__version__}")

    with engine.connect() as conn:
        rev = conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        if rev != V1_ALEMBIC_HEAD:
            raise ValidateV1Error(
                f"alembic revision {rev!r} != expected {V1_ALEMBIC_HEAD}"
            )
        diagnostics.append(f"alembic={rev}")

        td = conn.execute(text("SELECT COUNT(*) FROM trading_days")).scalar_one()
        macro = conn.execute(text("SELECT COUNT(*) FROM macro_conditions")).scalar_one()
        cal = conn.execute(text("SELECT COUNT(*) FROM calendar_context")).scalar_one()
        if macro != td:
            raise ValidateV1Error(f"macro_conditions {macro} != trading_days {td}")
        if cal != td:
            raise ValidateV1Error(f"calendar_context {cal} != trading_days {td}")

        missing_macro = conn.execute(
            text(
                """
                SELECT COUNT(*) FROM trading_days t
                LEFT JOIN macro_conditions m ON m.date = t.date
                WHERE m.date IS NULL
                """
            )
        ).scalar_one()
        if missing_macro:
            raise ValidateV1Error("macro_conditions missing trading_days dates")

        missing_cal = conn.execute(
            text(
                """
                SELECT COUNT(*) FROM trading_days t
                LEFT JOIN calendar_context c ON c.date = t.date
                WHERE c.date IS NULL
                """
            )
        ).scalar_one()
        if missing_cal:
            raise ValidateV1Error("calendar_context missing trading_days dates")

        dmd = conn.execute(text("SELECT COUNT(*) FROM daily_market_data")).scalar_one()
        mo = conn.execute(text("SELECT COUNT(*) FROM market_outcomes")).scalar_one()
        ar = conn.execute(text("SELECT COUNT(*) FROM asset_regimes")).scalar_one()
        if mo != dmd:
            raise ValidateV1Error(f"market_outcomes {mo} != daily_market_data {dmd}")
        if ar != dmd:
            raise ValidateV1Error(f"asset_regimes {ar} != daily_market_data {dmd}")

        for child in ("market_outcomes", "asset_regimes"):
            orphans = conn.execute(
                text(
                    f"""
                    SELECT COUNT(*) FROM {child} c
                    LEFT JOIN daily_market_data d
                      ON d.date = c.date AND d.symbol = c.symbol
                    WHERE d.date IS NULL
                    """
                )
            ).scalar_one()
            if orphans:
                raise ValidateV1Error(f"{child} not 1:1 with daily_market_data")

        for table in ("daily_market_data", "market_outcomes", "asset_regimes"):
            outside = conn.execute(
                text(
                    f"""
                    SELECT COUNT(*) FROM {table} x
                    LEFT JOIN trading_days t ON t.date = x.date
                    WHERE t.date IS NULL
                    """
                )
            ).scalar_one()
            if outside:
                raise ValidateV1Error(f"{table} has dates outside trading_days")

        dd_bad = conn.execute(
            text(
                """
                SELECT COUNT(*)
                FROM asset_regimes a
                JOIN daily_market_data d
                  ON d.date = a.date AND d.symbol = a.symbol
                WHERE (
                    a.drawdown_pct IS NULL AND d.drawdown_from_high IS NOT NULL
                ) OR (
                    a.drawdown_pct IS NOT NULL AND d.drawdown_from_high IS NULL
                ) OR (
                    a.drawdown_pct IS NOT NULL AND d.drawdown_from_high IS NOT NULL
                    AND ABS(a.drawdown_pct - d.drawdown_from_high) > 1e-9
                )
                """
            )
        ).scalar_one()
        if dd_bad:
            raise ValidateV1Error(f"drawdown identity mismatches: {dd_bad}")

        r1_bad = conn.execute(
            text(
                """
                WITH nxt AS (
                  SELECT date, symbol, return_1d,
                         LEAD(return_1d) OVER (
                           PARTITION BY symbol ORDER BY date
                         ) AS next_dmd_return_1d
                  FROM daily_market_data
                )
                SELECT COUNT(*)
                FROM market_outcomes o
                JOIN nxt n ON n.date = o.date AND n.symbol = o.symbol
                WHERE o.return_1d IS NOT NULL
                  AND n.next_dmd_return_1d IS NOT NULL
                  AND ABS(o.return_1d - n.next_dmd_return_1d) > 1e-9
                """
            )
        ).scalar_one()
        if r1_bad:
            raise ValidateV1Error(
                f"market_outcomes.return_1d vs next dmd.return_1d mismatches: {r1_bad}"
            )

        flag_map = {
            "fomc": "is_fomc_day",
            "cpi": "is_cpi_release_day",
            "employment_situation": "is_employment_situation_day",
            "election": "is_election_day",
        }
        for etype, flag in flag_map.items():
            true_n = conn.execute(
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
            if true_n != on_cal:
                raise ValidateV1Error(
                    f"{flag} count {true_n} != on-calendar {etype} events {on_cal}"
                )

        null_dd = conn.execute(
            text(
                "SELECT COUNT(*) FROM daily_market_data "
                "WHERE drawdown_from_high IS NULL"
            )
        ).scalar_one()
        if null_dd:
            raise ValidateV1Error(
                f"daily_market_data.drawdown_from_high NULL count={null_dd} "
                "(derive may not have run)"
            )

        first_null_r1 = conn.execute(
            text(
                """
                SELECT COUNT(*) FROM (
                  SELECT symbol, MIN(date) AS d0
                  FROM daily_market_data
                  GROUP BY symbol
                ) f
                JOIN daily_market_data d ON d.symbol = f.symbol AND d.date = f.d0
                WHERE d.return_1d IS NOT NULL
                """
            )
        ).scalar_one()
        if first_null_r1:
            raise ValidateV1Error(
                "first observation per symbol should have NULL return_1d"
            )

        symbols = conn.execute(
            text("SELECT COUNT(DISTINCT symbol) FROM daily_market_data")
        ).scalar_one()
        if symbols != 14:
            raise ValidateV1Error(f"expected 14 symbols; found {symbols}")

        diag = collect_diagnostics(engine)
        for k, v in diag.items():
            diagnostics.append(f"{k}={v}")

    return diagnostics


def main() -> int:
    configure_logging()
    logger = get_logger("stockballdb.validate_v1")
    logger.info("StockBallDB starting validate_v1")
    print("StockBallDB V1 Validation", flush=True)
    print(flush=True)

    try:
        settings = load_settings(require_database_url=True)
        reset_engine()
        engine = get_engine(settings)
        diagnostics = validate_v1_database(engine)
    except (ConfigError, ValidateV1Error) as exc:
        print(f"{_pad('validate_v1')} FAIL", flush=True)
        print(flush=True)
        print("STATUS: FAILED", flush=True)
        print(f"REASON: {exc}", flush=True)
        logger.error("validate_v1 failed: %s", exc)
        return 1
    except Exception as exc:
        print(f"{_pad('validate_v1')} FAIL", flush=True)
        print(flush=True)
        print("STATUS: FAILED", flush=True)
        print(f"REASON: {exc}", flush=True)
        logger.error("validate_v1 failed: %s", exc)
        return 1

    print(f"{_pad('validate_v1')} PASS", flush=True)
    for line in diagnostics[:8]:
        print(f"  {line}", flush=True)
    if len(diagnostics) > 8:
        print(f"  ... ({len(diagnostics)} diagnostic lines)", flush=True)
    print(flush=True)
    print("STATUS: V1 VALID", flush=True)
    logger.info("validate_v1 PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
