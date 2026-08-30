"""Tests for StockBallDB Explorer (Phase 11B)."""

from __future__ import annotations

import datetime as dt
import json
import re
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from sqlalchemy.engine import Engine

from stockballdb.config import Settings, explorer_database_url
from stockballdb.explorer import config as explorer_config
from stockballdb.explorer.artifacts import discover_manifests, discover_run_reports
from stockballdb.explorer.config import CSV_EXPORT_MAX_ROWS, DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from stockballdb.explorer.db import reset_explorer_engine
from stockballdb.explorer.definitions import definition_for, field_definitions
from stockballdb.explorer.formatting import NULL_DISPLAY, format_cell, format_hash, rows_to_display_dicts
from stockballdb.explorer.queries import (
    ExplorerQueryError,
    PageRequest,
    TableFilters,
    export_query,
    fetch_trading_day,
    nearest_trading_sessions,
    query_table_page,
)
from stockballdb.explorer.registry import TABLE_REGISTRY, ExplorerQueryError as RegistryError, get_table_spec, list_table_keys
from stockballdb.explorer.services import day as day_service
from stockballdb.explorer.services import validation as validation_service
from stockballdb.explorer.services.control import load_control_center, manifest_summary
from stockballdb.explorer.services.coverage import load_coverage
from stockballdb.explorer.services.provenance import manifest_detail, resolve_snapshot_path, snapshot_metadata_list
from stockballdb.explorer.services.tables import browse_table, list_tables
from stockballdb.fingerprint.compute import DatabaseFingerprint, TableFingerprint
from stockballdb.health.models import HealthReport, HealthStatus
from stockballdb.validate_v1 import ValidateV1Error


EXPLORER_ROOT = Path(__file__).resolve().parents[1] / "src" / "stockballdb" / "explorer"
DML_PATTERN = re.compile(r"\b(INSERT|UPDATE|DELETE|TRUNCATE|DROP|ALTER)\b")


class _ScalarResult:
    def __init__(self, value):
        self._value = value

    def scalar_one(self):
        return self._value


class _Row:
    def __init__(self, mapping: dict):
        self._mapping = mapping


class _RowsResult:
    def __init__(self, rows: list):
        self._rows = rows

    def all(self):
        return self._rows

    def first(self):
        return self._rows[0] if self._rows else None


def _scripted_conn(responses: list):
    conn = MagicMock()
    it = iter(responses)

    def _execute(*_a, **_k):
        try:
            return next(it)
        except StopIteration as exc:
            raise AssertionError("unexpected extra SQL execute") from exc

    conn.execute.side_effect = _execute
    return conn


@pytest.fixture(autouse=True)
def _reset_explorer_engine() -> None:
    reset_explorer_engine()
    yield
    reset_explorer_engine()


# --- Registry ---


def test_registry_has_seven_tables() -> None:
    keys = list_table_keys()
    assert len(keys) == 7
    assert set(keys) == set(TABLE_REGISTRY.keys())


@pytest.mark.parametrize(
    "table_key",
    [
        "trading_days",
        "daily_market_data",
        "market_outcomes",
        "asset_regimes",
        "macro_conditions",
        "scheduled_events",
        "calendar_context",
    ],
)
def test_registry_table_spec(table_key: str) -> None:
    spec = get_table_spec(table_key)
    assert spec.key == table_key
    assert spec.model is not None
    assert spec.date_column
    assert spec.default_sort


def test_registry_rejects_unknown_table() -> None:
    with pytest.raises(RegistryError, match="unknown table"):
        get_table_spec("not_a_table")


def test_registry_default_sort_columns_allowed() -> None:
    for spec in TABLE_REGISTRY.values():
        for col, direction in spec.default_sort:
            assert col in spec.sortable_columns
            assert direction in {"asc", "desc"}


# --- Queries ---


def test_query_rejects_invalid_sort_column() -> None:
    conn = MagicMock()
    with pytest.raises(ExplorerQueryError, match="sort column not allowed"):
        query_table_page(
            conn,
            "trading_days",
            page=PageRequest(sort_column="not_a_column"),
        )


def test_query_rejects_invalid_sort_direction() -> None:
    conn = MagicMock()
    with pytest.raises(ExplorerQueryError, match="invalid sort direction"):
        query_table_page(
            conn,
            "trading_days",
            page=PageRequest(sort_direction="sideways"),
        )


def test_query_rejects_invalid_page_size() -> None:
    conn = MagicMock()
    with pytest.raises(ExplorerQueryError, match="page_size"):
        query_table_page(conn, "trading_days", page=PageRequest(page_size=0))


def test_query_clamps_page_size_to_max() -> None:
    conn = _scripted_conn([_ScalarResult(0), _RowsResult([])])
    result = query_table_page(
        conn,
        "trading_days",
        page=PageRequest(page_size=9999),
    )
    assert result.page_size == MAX_PAGE_SIZE


def test_query_default_page_size() -> None:
    conn = _scripted_conn([_ScalarResult(0), _RowsResult([])])
    result = query_table_page(conn, "trading_days")
    assert result.page_size == DEFAULT_PAGE_SIZE


def test_query_applies_boolean_filter_allowlist() -> None:
    conn = MagicMock()
    with pytest.raises(ExplorerQueryError, match="boolean filter not allowed"):
        query_table_page(
            conn,
            "calendar_context",
            filters=TableFilters(boolean_flags={"is_election_day": True, "evil_flag": True}),
        )


def test_query_table_page_returns_metadata() -> None:
    conn = _scripted_conn([_ScalarResult(2), _RowsResult([_Row({"date": dt.date(2020, 1, 2)})])])
    result = query_table_page(
        conn,
        "trading_days",
        filters=TableFilters(date_from=dt.date(2020, 1, 1)),
        page=PageRequest(page=2, page_size=1, sort_column="date"),
    )
    assert result.total_count == 2
    assert result.page == 2
    assert result.table_key == "trading_days"
    assert len(result.rows) == 1


def test_export_query_respects_max_rows() -> None:
    conn = _scripted_conn([_RowsResult([])])
    export_query(conn, "trading_days", max_rows=CSV_EXPORT_MAX_ROWS)
    conn.execute.assert_called_once()


def test_fetch_trading_day_none_when_missing() -> None:
    conn = _scripted_conn([_RowsResult([])])
    assert fetch_trading_day(conn, dt.date(1958, 11, 4)) is None


def test_nearest_trading_sessions() -> None:
    prev = _Row({"date": dt.date(1958, 11, 3)})
    nxt = _Row({"date": dt.date(1958, 11, 5)})
    conn = _scripted_conn([_RowsResult([prev]), _RowsResult([nxt])])
    previous, next_ = nearest_trading_sessions(conn, dt.date(1958, 11, 4))
    assert previous["date"] == dt.date(1958, 11, 3)
    assert next_["date"] == dt.date(1958, 11, 5)


# --- Day Inspector ---


def test_inspect_day_non_trading_election(monkeypatch: pytest.MonkeyPatch) -> None:
    election = dt.date(1958, 11, 4)
    conn = MagicMock()
    monkeypatch.setattr(day_service, "fetch_trading_day", lambda _c, _d: None)
    monkeypatch.setattr(
        day_service,
        "nearest_trading_sessions",
        lambda _c, _d: ({"date": dt.date(1958, 11, 3)}, {"date": dt.date(1958, 11, 5)}),
    )
    monkeypatch.setattr(
        day_service,
        "fetch_scheduled_events_for_date",
        lambda _c, _d: [{"event_type": "election_day", "event_date": election}],
    )
    monkeypatch.setattr(day_service, "fetch_row_by_date", lambda *_a, **_k: None)
    monkeypatch.setattr(day_service, "fetch_rows_for_date", lambda *_a, **_k: [])
    result = day_service.inspect_day(conn, election)
    assert not result.is_trading_day
    assert result.trading_day is None
    assert any("Trading session: none" in m for m in result.messages)
    assert len(result.scheduled_events) == 1
    assert result.next_session["date"] == dt.date(1958, 11, 5)


def test_inspect_day_unknown_symbol_message(monkeypatch: pytest.MonkeyPatch) -> None:
    conn = MagicMock()
    monkeypatch.setattr(
        day_service,
        "fetch_trading_day",
        lambda _c, _d: {"date": dt.date(2020, 1, 2)},
    )
    monkeypatch.setattr(day_service, "nearest_trading_sessions", lambda _c, _d: (None, None))
    monkeypatch.setattr(day_service, "fetch_scheduled_events_for_date", lambda _c, _d: [])
    monkeypatch.setattr(day_service, "fetch_row_by_date", lambda *_a, **_k: None)
    monkeypatch.setattr(day_service, "fetch_rows_for_date", lambda *_a, **_k: [])
    result = day_service.inspect_day(conn, dt.date(2020, 1, 2), symbol="NOTREAL")
    assert any("Unknown symbol" in m for m in result.messages)


# --- Formatting ---


def test_format_cell_null_and_bool() -> None:
    assert format_cell(None) == NULL_DISPLAY
    assert format_cell(True) == "Yes"
    assert format_cell(False) == "No"


def test_format_cell_date_and_decimal() -> None:
    assert format_cell(dt.date(2020, 1, 2)) == "2020-01-02"
    assert format_cell(Decimal("1.2300")) == "1.23"


def test_format_hash_truncates() -> None:
    digest = "sha256:" + "a" * 64
    assert "…" in format_hash(digest)


def test_rows_to_display_dicts() -> None:
    out = rows_to_display_dicts([{"x": None, "y": 1}])
    assert out[0]["x"] == NULL_DISPLAY


# --- Definitions ---


def test_definitions_include_key_fields() -> None:
    defs = field_definitions()
    assert "return_1d" in defs
    assert "fed_funds_rate" in defs
    assert "return_5d" in defs
    assert definition_for("return_1d")


# --- Artifacts ---


def test_discover_manifests_newest_first(tmp_path: Path) -> None:
    old = tmp_path / "manifest_old.json"
    new = tmp_path / "manifest_new.json"
    old.write_text(json.dumps({"build_id": "old", "build_started_at": "2020-01-01T00:00:00Z"}), encoding="utf-8")
    new.write_text(json.dumps({"build_id": "new", "build_started_at": "2026-01-01T00:00:00Z"}), encoding="utf-8")
    records = discover_manifests(tmp_path)
    assert len(records) == 2
    assert records[0].artifact_id == "new"


def test_discover_manifests_skips_malformed_json(tmp_path: Path) -> None:
    bad = tmp_path / "manifest_bad.json"
    bad.write_text("{not json", encoding="utf-8")
    records = discover_manifests(tmp_path)
    assert len(records) == 1
    assert records[0].error is not None
    assert records[0].payload is None


def test_discover_manifests_skips_secrets(tmp_path: Path) -> None:
    secret = tmp_path / "manifest_secret.json"
    secret.write_text(json.dumps({"build_id": "x", "api_key": "secret"}), encoding="utf-8")
    records = discover_manifests(tmp_path)
    assert records[0].payload is None
    assert "secret" in (records[0].error or "").lower()


def test_discover_run_reports(tmp_path: Path) -> None:
    run = tmp_path / "run_abc.json"
    run.write_text(json.dumps({"run_id": "abc", "started_at": "2026-01-01T00:00:00Z"}), encoding="utf-8")
    records = discover_run_reports(tmp_path)
    assert len(records) == 1
    assert records[0].kind == "run_report"


# --- Provenance ---


def test_manifest_detail_classifies(tmp_path: Path) -> None:
    path = tmp_path / "manifest_test.json"
    path.write_text(
        json.dumps(
            {
                "build_id": "test",
                "schema_version": "1.1",
                "snapshots": [],
            }
        ),
        encoding="utf-8",
    )
    detail = manifest_detail(path)
    assert "_classification" in detail


def test_snapshot_metadata_strips_secrets() -> None:
    manifest = {
        "snapshots": [
            {
                "snapshot_id": "snap1",
                "request_identity": {"authorization": "Bearer x", "url": "https://example.test"},
            }
        ]
    }
    out = snapshot_metadata_list(manifest)
    assert out
    assert "authorization" not in str(out[0].get("request_identity", {}))


def test_resolve_snapshot_path_rejects_traversal() -> None:
    with pytest.raises(ValueError, match="invalid snapshot path"):
        resolve_snapshot_path("../etc/passwd")


# --- Services ---


def test_load_coverage_delegates(monkeypatch: pytest.MonkeyPatch) -> None:
    conn = MagicMock()
    monkeypatch.setattr(
        "stockballdb.explorer.services.coverage.load_trading_days",
        lambda _c: [dt.date(2020, 1, 2)],
    )
    monkeypatch.setattr(
        "stockballdb.explorer.services.coverage.collect_table_coverage",
        lambda _c: [SimpleNamespace(table="trading_days", row_count=1)],
    )
    monkeypatch.setattr(
        "stockballdb.explorer.services.coverage.collect_symbol_coverage",
        lambda _c, _td: [],
    )
    monkeypatch.setattr(
        "stockballdb.explorer.services.coverage.collect_freshness",
        lambda _c, _td: [],
    )
    monkeypatch.setattr(
        "stockballdb.explorer.services.coverage.gap_findings",
        lambda _c, _td, _sym: [],
    )
    snap = load_coverage(conn)
    assert snap.tables
    assert snap.limitations


def test_validation_run_validate_v1_pass(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "stockballdb.explorer.services.validation.validate_v1_database",
        lambda _e: ["ok"],
    )
    engine = MagicMock(spec=Engine)
    result = validation_service.run_validate_v1(engine)
    assert result.passed
    assert result.diagnostics == ["ok"]


def test_validation_run_validate_v1_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "stockballdb.explorer.services.validation.validate_v1_database",
        lambda _e: (_ for _ in ()).throw(ValidateV1Error("bad")),
    )
    engine = MagicMock(spec=Engine)
    result = validation_service.run_validate_v1(engine)
    assert not result.passed
    assert result.error == "bad"


def test_control_center_manifest_summary() -> None:
    from stockballdb.explorer.artifacts import ArtifactRecord

    rec = ArtifactRecord(
        path=Path("manifest_x.json"),
        kind="manifest",
        artifact_id="x",
        started_at="2026-01-01",
        payload={
            "build_id": "x",
            "schema_version": "1.1",
            "validation_result": "PASS",
            "health_status": "HEALTHY",
            "snapshots": [{"snapshot_id": "a"}],
            "database_fingerprint": {"database_fingerprint": "sha256:abc"},
        },
    )
    summary = manifest_summary(rec)
    assert summary["build_id"] == "x"
    assert summary["snapshot_count"] == 1


def test_load_control_center(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    engine = MagicMock(spec=Engine)
    health = HealthReport(
        status=HealthStatus.HEALTHY,
        generated_at=dt.datetime.now(dt.timezone.utc),
        runtime_ms=1.0,
        database_connected=True,
        alembic_head="head",
        expected_alembic_head="head",
        calendar_version="4.3.3",
        validate_v1_pass=True,
        findings=[],
    )
    monkeypatch.setattr("stockballdb.explorer.services.control.run_health", lambda _e: health)
    monkeypatch.setattr(
        "stockballdb.explorer.services.control.collect_diagnostics",
        lambda _e: {"tables": {}},
    )
    monkeypatch.setattr(
        "stockballdb.explorer.services.control.git_provenance",
        lambda: {"commit": "abc"},
    )
    man = tmp_path / "manifest_m.json"
    man.write_text(
        json.dumps({"build_id": "m", "build_started_at": "2026-01-01T00:00:00Z", "snapshots": []}),
        encoding="utf-8",
    )
    monkeypatch.setattr("stockballdb.explorer.services.control.discover_manifests", lambda: discover_manifests(tmp_path))
    monkeypatch.setattr("stockballdb.explorer.services.control.discover_run_reports", lambda: [])
    snap = load_control_center(engine)
    assert snap.health.status == HealthStatus.HEALTHY
    assert snap.latest_manifest is not None


# --- Config ---


def test_explorer_database_url_prefers_explicit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STOCKBALLDB_EXPLORER_DATABASE_URL", "postgresql://ro@localhost/explorer")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert explorer_database_url() == "postgresql://ro@localhost/explorer"


def test_explorer_database_url_falls_back_to_primary(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("STOCKBALLDB_EXPLORER_DATABASE_URL", raising=False)
    settings = Settings(
        database_url="postgresql://u:p@localhost/primary",
        tiingo_api_key="t",
        fred_api_key="f",
    )
    assert explorer_database_url(settings) == settings.database_url


def test_explorer_config_constants() -> None:
    assert explorer_config.DEFAULT_PAGE_SIZE == 100
    assert explorer_config.MAX_PAGE_SIZE == 500
    assert explorer_config.CSV_EXPORT_MAX_ROWS == 10_000


# --- Read-only audit ---


def test_explorer_package_has_no_dml_strings() -> None:
    hits: list[str] = []
    for path in EXPLORER_ROOT.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for match in DML_PATTERN.finditer(text):
            hits.append(f"{path.name}:{match.group(0)}")
    assert hits == [], f"DML-like tokens in explorer: {hits}"


def test_tables_service_list_and_browse() -> None:
    assert len(list_tables()) == 7
    conn = _scripted_conn([_ScalarResult(0), _RowsResult([])])
    result = browse_table(conn, "trading_days", TableFilters(), PageRequest())
    assert result.table_key == "trading_days"


# --- Smoke ---


def test_import_explorer_app() -> None:
    import stockballdb.explorer.app  # noqa: F401


def test_import_explorer_main() -> None:
    import stockballdb.explorer.__main__  # noqa: F401


def test_fingerprint_wrapper(monkeypatch: pytest.MonkeyPatch) -> None:
    fp = DatabaseFingerprint(
        fingerprint_schema_version="1.0",
        database_fingerprint="sha256:test",
        table_fingerprints=(TableFingerprint(table="trading_days", row_count=1, sha256="a"),),
    )
    monkeypatch.setattr(
        "stockballdb.explorer.services.validation.compute_database_fingerprint",
        lambda _e: fp,
    )
    result = validation_service.run_fingerprint(MagicMock(spec=Engine))
    assert result.database_fingerprint == "sha256:test"
