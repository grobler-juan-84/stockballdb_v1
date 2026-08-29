"""Tests for StockBallDB health engine."""

from __future__ import annotations

import datetime as dt
import json
from types import SimpleNamespace

import pytest

from stockballdb.health.gaps import gap_findings, session_lag, wti_session_lag
from stockballdb.health.models import (
    Finding,
    FreshnessClass,
    HealthReport,
    HealthStatus,
    Severity,
    SymbolCoverage,
)
from stockballdb.health.provenance import build_manifest_payload, scan_secrets
from stockballdb.health.render import render_json, report_to_dict


def test_aggregate_status_healthy() -> None:
    findings = [
        Finding(Severity.INFO, "ETF_EXPECTED_LAG", "etf", "lag ok", {}),
    ]
    assert HealthReport.aggregate_status(findings) == HealthStatus.HEALTHY


def test_aggregate_status_warnings() -> None:
    findings = [
        Finding(Severity.WARNING, "MARKET_INTERNAL_GAP", "SPY", "gap", {}),
    ]
    assert HealthReport.aggregate_status(findings) == HealthStatus.HEALTHY_WITH_WARNINGS


def test_aggregate_status_unhealthy() -> None:
    findings = [
        Finding(Severity.ERROR, "VALIDATE_V1_FAIL", "db", "fail", {}),
    ]
    assert HealthReport.aggregate_status(findings) == HealthStatus.UNHEALTHY


def test_exit_codes() -> None:
    healthy = HealthReport(
        status=HealthStatus.HEALTHY,
        generated_at=dt.datetime.now(dt.timezone.utc),
        runtime_ms=1.0,
        database_connected=True,
        alembic_head="x",
        expected_alembic_head="x",
        calendar_version="5.4.0",
        validate_v1_pass=True,
    )
    assert healthy.exit_code() == 0
    assert healthy.exit_code(strict=True) == 0

    warned = HealthReport(
        status=HealthStatus.HEALTHY_WITH_WARNINGS,
        generated_at=dt.datetime.now(dt.timezone.utc),
        runtime_ms=1.0,
        database_connected=True,
        alembic_head="x",
        expected_alembic_head="x",
        calendar_version="5.4.0",
        validate_v1_pass=True,
    )
    assert warned.exit_code() == 0
    assert warned.exit_code(strict=True) == 1

    bad = HealthReport(
        status=HealthStatus.UNHEALTHY,
        generated_at=dt.datetime.now(dt.timezone.utc),
        runtime_ms=1.0,
        database_connected=True,
        alembic_head="x",
        expected_alembic_head="x",
        calendar_version="5.4.0",
        validate_v1_pass=False,
    )
    assert bad.exit_code() == 1


def test_etf_freshness_lag_classification() -> None:
    sev, cls = session_lag("spine", "etf", 2)
    assert sev == Severity.INFO
    assert cls == FreshnessClass.EXPECTED_LAG

    sev2, cls2 = session_lag("spine", "etf", 0)
    assert cls2 == FreshnessClass.CURRENT


def test_wti_expected_lag_classification() -> None:
    sev, cls = wti_session_lag(1)
    assert sev == Severity.INFO
    assert cls == FreshnessClass.EXPECTED_LAG


def test_gap_findings_wti_provider_gap() -> None:
    sym = SymbolCoverage(
        symbol="WTI",
        asset_type="commodity",
        first_date=dt.date(1986, 1, 2),
        last_date=dt.date(2026, 1, 1),
        row_count=100,
        eligible_sessions=102,
        coverage_pct=98.0,
        internal_missing_sessions=2,
        max_consecutive_missing=1,
        sample_missing_dates=["2020-01-01"],
    )
    findings = gap_findings([sym])
    assert len(findings) == 1
    assert findings[0].code == "WTI_PROVIDER_GAP"
    assert findings[0].severity == Severity.INFO


def test_gap_findings_etf_consecutive_error() -> None:
    sym = SymbolCoverage(
        symbol="SPY",
        asset_type="etf",
        first_date=dt.date(2000, 1, 1),
        last_date=dt.date(2020, 1, 1),
        row_count=100,
        eligible_sessions=120,
        coverage_pct=83.0,
        internal_missing_sessions=20,
        max_consecutive_missing=10,
        sample_missing_dates=[],
    )
    findings = gap_findings([sym])
    assert findings[0].severity == Severity.ERROR
    assert findings[0].code == "MARKET_INTERNAL_GAP"


def test_json_output_valid() -> None:
    report = HealthReport(
        status=HealthStatus.HEALTHY,
        generated_at=dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc),
        runtime_ms=12.5,
        database_connected=True,
        alembic_head="a8f3c2d1b4e5",
        expected_alembic_head="a8f3c2d1b4e5",
        calendar_version="5.4.0",
        validate_v1_pass=True,
        findings=[
            Finding(Severity.INFO, "ETF_EXPECTED_LAG", "etf", "ok", {"lag_sessions": 2}),
        ],
    )
    data = json.loads(render_json(report))
    assert data["status"] == "HEALTHY"
    assert data["finding_counts"]["INFO"] == 1
    assert "database" in data


def test_manifest_schema_no_secrets() -> None:
    started = dt.datetime(2026, 1, 1, 12, 0, 0, tzinfo=dt.timezone.utc)
    finished = dt.datetime(2026, 1, 1, 12, 5, 0, tzinfo=dt.timezone.utc)
    payload = build_manifest_payload(
        command="test",
        started_at=started,
        finished_at=finished,
        success=True,
        datasets=[{"dataset": "trading_days", "row_count": 1}],
        validation_result="PASS",
        alembic_head="a8f3c2d1b4e5",
    )
    assert payload["schema_version"] == "1.0"
    assert "build_id" in payload
    assert scan_secrets(payload) == []

    bad = {"api_key": "secret"}
    assert scan_secrets(bad) == ["api_key"]


def test_report_to_dict_finding_counts() -> None:
    report = HealthReport(
        status=HealthStatus.HEALTHY,
        generated_at=dt.datetime.now(dt.timezone.utc),
        runtime_ms=1.0,
        database_connected=True,
        alembic_head="x",
        expected_alembic_head="x",
        calendar_version="5.4.0",
        validate_v1_pass=True,
        findings=[
            Finding(Severity.PASS, "VALIDATE_V1_PASS", "db", "ok", {}),
            Finding(Severity.INFO, "ETF_EXPECTED_LAG", "etf", "ok", {}),
        ],
    )
    d = report_to_dict(report)
    assert d["finding_counts"]["INFO"] == 1
    assert len(d["findings"]) == 1
