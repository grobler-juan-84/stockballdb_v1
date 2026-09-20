"""Tests for stockballdb.app P1 Catalog + Status façade."""

from __future__ import annotations

from dataclasses import fields, is_dataclass
from unittest.mock import MagicMock, patch

import pytest

from stockballdb.app import catalog, status
from stockballdb.app.errors import AppNotFoundError, AppUnavailableError
from stockballdb.app.results import (
    ApplicationStatus,
    DataDomainInfo,
    FieldInfo,
    FingerprintResult,
    InstrumentInfo,
    ValidateResult,
)
from stockballdb.market_data.universe import (
    PHASE_2A_ETF_SYMBOLS,
    V1_MARKET_SYMBOLS,
    WTI_SYMBOL,
)


def test_list_instruments_matches_v1_universe() -> None:
    instruments = catalog.list_instruments()
    assert len(instruments) == len(V1_MARKET_SYMBOLS)
    assert tuple(i.symbol for i in instruments) == V1_MARKET_SYMBOLS
    assert all(isinstance(i, InstrumentInfo) for i in instruments)
    assert all(is_dataclass(i) for i in instruments)


def test_list_instruments_preserves_wti_commodity_close_only() -> None:
    by_symbol = {i.symbol: i for i in catalog.list_instruments()}
    wti = by_symbol[WTI_SYMBOL]
    assert wti.asset_type == "commodity"
    assert wti.close_only is True
    for symbol in PHASE_2A_ETF_SYMBOLS:
        assert by_symbol[symbol].asset_type == "etf"
        assert by_symbol[symbol].close_only is False


def test_list_data_domains_exposes_seven_tables_without_models() -> None:
    domains = catalog.list_data_domains()
    keys = {d.key for d in domains}
    assert keys == {
        "trading_days",
        "daily_market_data",
        "market_outcomes",
        "asset_regimes",
        "macro_conditions",
        "scheduled_events",
        "calendar_context",
    }
    assert all(isinstance(d, DataDomainInfo) for d in domains)
    for domain in domains:
        assert "model" not in {f.name for f in fields(domain)}
        assert domain.display_name
        assert domain.date_column


def test_get_fields_daily_market_data() -> None:
    field_list = catalog.get_fields("daily_market_data")
    names = {f.name for f in field_list}
    assert "symbol" in names
    assert "adj_close" in names
    assert "date" in names
    assert all(isinstance(f, FieldInfo) for f in field_list)
    sortable = {f.name for f in field_list if f.sortable}
    assert "close" in sortable
    assert "adj_close" in sortable


def test_get_fields_unknown_domain_raises() -> None:
    with pytest.raises(AppNotFoundError, match="unknown data domain"):
        catalog.get_fields("not_a_real_table")


def test_catalog_results_are_plain_application_types() -> None:
    instruments = catalog.list_instruments()
    domains = catalog.list_data_domains()
    fields_list = catalog.get_fields("trading_days")
    for obj in (*instruments, *domains, *fields_list):
        assert type(obj).__module__.startswith("stockballdb.app.")
        assert "streamlit" not in type(obj).__module__
        assert "sqlalchemy" not in type(obj).__module__


def test_get_status_unavailable_returns_structured_failure() -> None:
    with patch(
        "stockballdb.app.read.status.ensure_database_available",
        side_effect=AppUnavailableError("database unavailable: boom"),
    ):
        result = status.get_status()
    assert isinstance(result, ApplicationStatus)
    assert result.available is False
    assert result.database_connected is False
    assert result.error_message is not None
    assert "unavailable" in result.error_message


def test_get_status_maps_health_report() -> None:
    fake_report = MagicMock()
    fake_report.database_connected = True
    fake_report.status.value = "HEALTHY"
    fake_report.validate_v1_pass = True
    fake_report.alembic_head = "a8f3c2d1b4e5"
    fake_report.expected_alembic_head = "a8f3c2d1b4e5"
    fake_report.calendar_version = "5.4.0"
    fake_report.finding_counts.return_value = {"INFO": 1, "WARNING": 0, "ERROR": 0, "FATAL": 0}

    with (
        patch("stockballdb.app.read.status.ensure_database_available"),
        patch("stockballdb.app.read.status.get_read_engine", return_value=MagicMock()),
        patch("stockballdb.app.read.status.run_health", return_value=fake_report),
    ):
        result = status.get_status()

    assert result.available is True
    assert result.database_connected is True
    assert result.health_status == "HEALTHY"
    assert result.validate_v1_pass is True
    assert result.alembic_head == "a8f3c2d1b4e5"
    assert result.finding_counts["INFO"] == 1
    assert result.error_message is None


def test_run_validate_v1_pass_and_fail() -> None:
    with (
        patch("stockballdb.app.read.status.ensure_database_available"),
        patch("stockballdb.app.read.status.get_read_engine", return_value=MagicMock()),
        patch(
            "stockballdb.app.read.status.validate_v1_database",
            return_value=["ok"],
        ),
    ):
        ok = status.run_validate_v1()
    assert isinstance(ok, ValidateResult)
    assert ok.passed is True
    assert ok.diagnostics == ("ok",)

    from stockballdb.validate_v1 import ValidateV1Error

    with (
        patch("stockballdb.app.read.status.ensure_database_available"),
        patch("stockballdb.app.read.status.get_read_engine", return_value=MagicMock()),
        patch(
            "stockballdb.app.read.status.validate_v1_database",
            side_effect=ValidateV1Error("bad"),
        ),
    ):
        bad = status.run_validate_v1()
    assert bad.passed is False
    assert bad.error_message == "bad"


def test_get_fingerprint_maps_result() -> None:
    fake_fp = MagicMock()
    fake_fp.database_fingerprint = "sha256:abc"
    fake_fp.fingerprint_schema_version = "1"
    table = MagicMock()
    table.as_dict.return_value = {"table": "trading_days", "sha256": "x", "row_count": 1}
    fake_fp.table_fingerprints = (table,)

    with (
        patch("stockballdb.app.read.status.ensure_database_available"),
        patch("stockballdb.app.read.status.get_read_engine", return_value=MagicMock()),
        patch(
            "stockballdb.app.read.status.compute_database_fingerprint",
            return_value=fake_fp,
        ),
    ):
        result = status.get_fingerprint()

    assert isinstance(result, FingerprintResult)
    assert result.database_fingerprint == "sha256:abc"
    assert result.table_fingerprints[0]["table"] == "trading_days"


def test_get_status_live_when_database_configured() -> None:
    """Optional live check — skips when DATABASE_URL is unset."""
    import os

    if not os.getenv("DATABASE_URL", "").strip():
        pytest.skip("DATABASE_URL not set")
    result = status.get_status()
    assert isinstance(result, ApplicationStatus)
    assert result.available in (True, False)
    if result.available:
        assert result.database_connected is True
        assert result.health_status is not None
