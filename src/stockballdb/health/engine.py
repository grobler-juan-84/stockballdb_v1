"""Whole-database health engine."""

from __future__ import annotations

import datetime as dt
import time

import pandas_market_calendars as mcal
from sqlalchemy import text
from sqlalchemy.engine import Engine

from stockballdb.config import load_settings
from stockballdb.db import get_engine, reset_engine
from stockballdb.health.coverage import (
    collect_symbol_coverage,
    collect_table_coverage,
    load_trading_days,
)
from stockballdb.health.freshness import collect_freshness
from stockballdb.health.gaps import gap_findings
from stockballdb.health.integrity import run_integrity
from stockballdb.health.limitations import EXPECTED_LIMITATIONS
from stockballdb.health.models import Finding, HealthReport, Severity
from stockballdb.health.provenance import git_provenance
from stockballdb.v1.preflight import REQUIRED_CALENDAR_VERSION, V1_ALEMBIC_HEAD


def run_health(engine: Engine | None = None) -> HealthReport:
    started = time.perf_counter()
    generated_at = dt.datetime.now(dt.timezone.utc)

    settings = load_settings(require_database_url=True)
    reset_engine()
    eng = engine or get_engine(settings)

    findings: list[Finding] = []
    database_connected = False
    alembic_head: str | None = None

    try:
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
            database_connected = True
            alembic_head = conn.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one()

            if alembic_head != V1_ALEMBIC_HEAD:
                findings.append(
                    Finding(
                        severity=Severity.FATAL,
                        code="SCHEMA_MISMATCH",
                        dataset="migration",
                        message=f"alembic {alembic_head} != expected {V1_ALEMBIC_HEAD}",
                        details={},
                    )
                )

            if mcal.__version__ != REQUIRED_CALENDAR_VERSION:
                findings.append(
                    Finding(
                        severity=Severity.FATAL,
                        code="CALENDAR_PIN_MISMATCH",
                        dataset="trading_days",
                        message=(
                            f"pandas_market_calendars {mcal.__version__} != "
                            f"{REQUIRED_CALENDAR_VERSION}"
                        ),
                        details={},
                    )
                )

            trading_days = load_trading_days(conn)
            tables = collect_table_coverage(conn)
            symbols = collect_symbol_coverage(conn, trading_days)
            freshness, fresh_findings = collect_freshness(conn)
            findings.extend(fresh_findings)
            findings.extend(gap_findings(symbols))
    except Exception as exc:
        findings.append(
            Finding(
                severity=Severity.FATAL,
                code="DATABASE_CONNECT_FAIL",
                dataset="database",
                message=str(exc),
                details={},
            )
        )
        runtime_ms = (time.perf_counter() - started) * 1000
        report = HealthReport(
            status=HealthReport.aggregate_status(findings),
            generated_at=generated_at,
            runtime_ms=runtime_ms,
            database_connected=False,
            alembic_head=alembic_head,
            expected_alembic_head=V1_ALEMBIC_HEAD,
            calendar_version=mcal.__version__,
            validate_v1_pass=False,
            findings=findings,
            provenance={"git": git_provenance(), "limitations": list(EXPECTED_LIMITATIONS)},
        )
        return report

    validate_pass, diagnostics, integrity_findings = run_integrity(eng)
    findings.extend(integrity_findings)

    integrity_summary = {
        "validate_v1": "PASS" if validate_pass else "FAIL",
        "diagnostics": diagnostics[:12],
    }

    runtime_ms = (time.perf_counter() - started) * 1000
    status = HealthReport.aggregate_status(findings)

    return HealthReport(
        status=status,
        generated_at=generated_at,
        runtime_ms=runtime_ms,
        database_connected=database_connected,
        alembic_head=alembic_head,
        expected_alembic_head=V1_ALEMBIC_HEAD,
        calendar_version=mcal.__version__,
        validate_v1_pass=validate_pass,
        tables=tables,
        symbols=symbols,
        freshness=freshness,
        findings=findings,
        provenance={"git": git_provenance(), "limitations": list(EXPECTED_LIMITATIONS)},
        integrity=integrity_summary,
    )
