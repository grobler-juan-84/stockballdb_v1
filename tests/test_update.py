"""Tests for operational update orchestration."""

from __future__ import annotations

import datetime as dt
import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from stockballdb.config import ConfigError, Settings
from stockballdb.fingerprint.compute import DatabaseFingerprint, TableFingerprint
from stockballdb.health.models import HealthReport, HealthStatus
from stockballdb.snapshots.models import SnapshotReference
from stockballdb.update import __main__ as update_main
from stockballdb.update.lock import AdvisoryLock
from stockballdb.update.orchestrator import (
    EXIT_CONCURRENT,
    EXIT_FAILED,
    EXIT_PREFLIGHT,
    EXIT_SUCCESS,
    run_update,
)
from stockballdb.update.preflight import UpdatePreflightError, run_update_preflight
from stockballdb.update.report import RunReport
from stockballdb.validate_v1 import ValidateV1Error
from stockballdb.v1.preflight import REQUIRED_CALENDAR_VERSION, V1_ALEMBIC_HEAD
from stockballdb.v1.stages import BUILD_STAGES, UPDATE_STAGES, effective_run_as_of


def _fp(digest: str) -> DatabaseFingerprint:
    table = TableFingerprint(table="trading_days", row_count=1, sha256="abc")
    return DatabaseFingerprint(
        fingerprint_schema_version="1.0",
        database_fingerprint=digest,
        table_fingerprints=(table,),
    )


def _sample_snap() -> SnapshotReference:
    return SnapshotReference(
        snapshot_id="snapsha256deadbeef",
        sha256="deadbeef",
        provider="tiingo",
        source_identifier="SPY",
        source_type="etf_daily",
        retrieved_at=dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc),
        request_identity={"url": "https://example.test"},
        payload_path="snapshots/ab/cd/snapsha256deadbeef.json.gz",
        byte_size_uncompressed=10,
    )


def _settings(**overrides) -> Settings:
    base = Settings(
        database_url="postgresql+psycopg://u:p@localhost:5432/x",
        tiingo_api_key="t",
        fred_api_key="f",
    )
    if overrides:
        return replace_settings(base, **overrides)
    return base


def replace_settings(base: Settings, **overrides) -> Settings:
    return Settings(
        database_url=overrides.get("database_url", base.database_url),
        tiingo_api_key=overrides.get("tiingo_api_key", base.tiingo_api_key),
        fred_api_key=overrides.get("fred_api_key", base.fred_api_key),
        eia_api_key=overrides.get("eia_api_key", base.eia_api_key),
        run_as_of=overrides.get("run_as_of", base.run_as_of),
    )


def _health(status: HealthStatus = HealthStatus.HEALTHY) -> HealthReport:
    return HealthReport(
        status=status,
        generated_at=dt.datetime.now(dt.timezone.utc),
        runtime_ms=1.0,
        database_connected=True,
        alembic_head=V1_ALEMBIC_HEAD,
        expected_alembic_head=V1_ALEMBIC_HEAD,
        calendar_version=REQUIRED_CALENDAR_VERSION,
        validate_v1_pass=True,
    )


def _patch_happy_path(monkeypatch: pytest.MonkeyPatch, *, fp_before: str, fp_after: str) -> None:
    settings = _settings()
    monkeypatch.setattr(
        "stockballdb.update.orchestrator.run_update_preflight",
        lambda: settings,
    )

    class _Lock:
        acquired = False

        def try_acquire(self) -> bool:
            self.acquired = True
            return True

        def release(self) -> None:
            self.acquired = False

    monkeypatch.setattr(
        "stockballdb.update.orchestrator.AdvisoryLock",
        lambda _url: _Lock(),
    )
    monkeypatch.setattr(
        "stockballdb.update.orchestrator.get_engine",
        lambda _s: MagicMock(),
    )
    monkeypatch.setattr(
        "stockballdb.update.orchestrator.compute_database_fingerprint",
        MagicMock(side_effect=[_fp(fp_before), _fp(fp_after)]),
    )

    def _make_run(key: str):
        def _run(_settings):
            return f"{key}=ok"

        return _run

    fake_stages = tuple(
        SimpleNamespace(key=s.key, label=s.label, run=_make_run(s.key))
        for s in UPDATE_STAGES
    )
    monkeypatch.setattr("stockballdb.update.orchestrator.UPDATE_STAGES", fake_stages)
    monkeypatch.setattr(
        "stockballdb.update.orchestrator.validate_v1_database",
        lambda _engine: ["ok"],
    )
    monkeypatch.setattr(
        "stockballdb.update.orchestrator.run_health",
        lambda _engine: _health(),
    )
    captured: dict = {}

    def _manifest(*args, **kwargs):
        captured["snapshots"] = kwargs.get("snapshots")
        return {"build_id": "test", "snapshots": []}

    monkeypatch.setattr(
        "stockballdb.update.orchestrator.manifest_from_health_report",
        _manifest,
    )
    monkeypatch.setattr(
        "stockballdb.update.orchestrator.write_build_manifest",
        lambda payload: None,
    )
    monkeypatch.setattr(
        "stockballdb.update.orchestrator.snapshot_references",
        lambda: [_sample_snap()],
    )
    monkeypatch.setattr(
        "stockballdb.update.orchestrator.live_build_context",
        lambda: MagicMock(__enter__=lambda s: s, __exit__=lambda *a: None),
    )
    monkeypatch.setattr("stockballdb.update.orchestrator.reset_context", lambda: None)
    monkeypatch.setattr("stockballdb.update.orchestrator.reset_engine", lambda: None)
    monkeypatch.setattr(
        "stockballdb.update.orchestrator.git_provenance",
        lambda: {"available": True, "commit": "abc", "dirty": False},
    )

    conn = MagicMock()
    conn.__enter__ = lambda s: s
    conn.__exit__ = lambda *a: None
    conn.execute.return_value.scalar_one.return_value = V1_ALEMBIC_HEAD
    engine = MagicMock()
    engine.connect.return_value = conn
    monkeypatch.setattr(
        "stockballdb.update.orchestrator.get_engine",
        lambda _s: engine,
    )


def test_update_stages_order() -> None:
    assert [s.key for s in UPDATE_STAGES] == [
        "trading_days",
        "daily_market_data",
        "derive_market_data",
        "market_outcomes",
        "asset_regimes",
        "wti_context",
        "macro_conditions",
        "scheduled_events",
        "calendar_context",
    ]
    assert "migrate" not in [s.key for s in UPDATE_STAGES]
    assert len(UPDATE_STAGES) == len(BUILD_STAGES) - 1


def test_effective_run_as_of_uses_settings_boundary() -> None:
    boundary = dt.date(2020, 3, 15)
    settings = _settings(run_as_of=boundary)
    assert effective_run_as_of(settings) == boundary


def test_effective_run_as_of_defaults_to_today_ny(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "stockballdb.v1.stages.today_ny",
        lambda: dt.date(2026, 8, 29),
    )
    assert effective_run_as_of(_settings()) == dt.date(2026, 8, 29)


def test_preflight_missing_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "stockballdb.update.preflight.load_settings",
        MagicMock(side_effect=ConfigError("DATABASE_URL is required")),
    )
    with pytest.raises(UpdatePreflightError, match="DATABASE_URL"):
        run_update_preflight()


def test_preflight_alembic_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = _settings()
    monkeypatch.setattr(
        "stockballdb.update.preflight.load_settings",
        lambda **kw: settings,
    )
    monkeypatch.setattr("stockballdb.update.preflight.check_connection", lambda _s: None)
    monkeypatch.setattr("stockballdb.update.preflight.reset_engine", lambda: None)

    conn = MagicMock()
    conn.__enter__ = lambda s: s
    conn.__exit__ = lambda *a: None
    conn.execute.return_value.scalar_one.side_effect = ["wrong", 100]
    engine = MagicMock()
    engine.connect.return_value = conn
    monkeypatch.setattr("stockballdb.update.preflight.get_engine", lambda _s: engine)
    monkeypatch.setattr(
        "stockballdb.update.preflight._assert_paths_writable",
        lambda: None,
    )

    with pytest.raises(UpdatePreflightError, match="Alembic revision"):
        run_update_preflight()


def test_preflight_primary_rebuild_collision(monkeypatch: pytest.MonkeyPatch) -> None:
    url = "postgresql+psycopg://u:p@localhost:5432/same_db"
    settings = _settings(database_url=url)
    monkeypatch.setattr(
        "stockballdb.update.preflight.load_settings",
        lambda **kw: settings,
    )
    monkeypatch.setenv("STOCKBALLDB_REBUILD_DATABASE_URL", url)
    with pytest.raises(UpdatePreflightError, match="must not target the same database"):
        run_update_preflight()


def test_preflight_empty_trading_days(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = _settings()
    monkeypatch.setattr(
        "stockballdb.update.preflight.load_settings",
        lambda **kw: settings,
    )
    monkeypatch.setattr("stockballdb.update.preflight.check_connection", lambda _s: None)
    monkeypatch.setattr("stockballdb.update.preflight.reset_engine", lambda: None)

    conn = MagicMock()
    conn.__enter__ = lambda s: s
    conn.__exit__ = lambda *a: None
    conn.execute.return_value.scalar_one.side_effect = [V1_ALEMBIC_HEAD, 0]
    engine = MagicMock()
    engine.connect.return_value = conn
    monkeypatch.setattr("stockballdb.update.preflight.get_engine", lambda _s: engine)

    with pytest.raises(UpdatePreflightError, match="bootstrap with python -m stockballdb.build_v1"):
        run_update_preflight()


def test_run_update_preflight_failure_writes_report(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    monkeypatch.setattr(
        "stockballdb.update.orchestrator.run_update_preflight",
        MagicMock(side_effect=UpdatePreflightError("DATABASE_URL missing")),
    )
    monkeypatch.setattr(
        "stockballdb.update.orchestrator.reports_dir",
        lambda: tmp_path,
        raising=False,
    )
    monkeypatch.setattr(
        "stockballdb.update.report.reports_dir",
        lambda: tmp_path,
    )
    result = run_update()
    assert result.exit_code == EXIT_PREFLIGHT
    assert result.report.status == "FAILED"
    assert result.report.failure_kind == "FAILED_PRECHECK"
    assert result.report_path is not None


def test_run_update_concurrent_refused(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    settings = _settings()
    monkeypatch.setattr(
        "stockballdb.update.orchestrator.run_update_preflight",
        lambda: settings,
    )

    class _Lock:
        def try_acquire(self) -> bool:
            return False

        def release(self) -> None:
            return None

    monkeypatch.setattr(
        "stockballdb.update.orchestrator.AdvisoryLock",
        lambda _url: _Lock(),
    )
    monkeypatch.setattr("stockballdb.update.orchestrator.reset_engine", lambda: None)
    conn = MagicMock()
    conn.__enter__ = lambda s: s
    conn.__exit__ = lambda *a: None
    conn.execute.return_value.scalar_one.return_value = V1_ALEMBIC_HEAD
    engine = MagicMock()
    engine.connect.return_value = conn
    monkeypatch.setattr("stockballdb.update.orchestrator.get_engine", lambda _s: engine)
    monkeypatch.setattr("stockballdb.update.report.reports_dir", lambda: tmp_path)

    result = run_update()
    assert result.exit_code == EXIT_CONCURRENT
    assert result.report.failure_kind == "FAILED_CONCURRENT"


def test_run_update_stage_failure_skips_later_stages(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    settings = _settings()
    monkeypatch.setattr(
        "stockballdb.update.orchestrator.run_update_preflight",
        lambda: settings,
    )

    class _Lock:
        def try_acquire(self) -> bool:
            return True

        def release(self) -> None:
            return None

    monkeypatch.setattr(
        "stockballdb.update.orchestrator.AdvisoryLock",
        lambda _url: _Lock(),
    )
    monkeypatch.setattr("stockballdb.update.orchestrator.reset_engine", lambda: None)
    conn = MagicMock()
    conn.__enter__ = lambda s: s
    conn.__exit__ = lambda *a: None
    conn.execute.return_value.scalar_one.return_value = V1_ALEMBIC_HEAD
    engine = MagicMock()
    engine.connect.return_value = conn
    monkeypatch.setattr("stockballdb.update.orchestrator.get_engine", lambda _s: engine)
    monkeypatch.setattr(
        "stockballdb.update.orchestrator.compute_database_fingerprint",
        lambda _e: _fp("before"),
    )
    monkeypatch.setattr(
        "stockballdb.update.orchestrator.live_build_context",
        lambda: MagicMock(__enter__=lambda s: s, __exit__=lambda *a: None),
    )
    monkeypatch.setattr("stockballdb.update.orchestrator.reset_context", lambda: None)
    monkeypatch.setattr("stockballdb.update.report.reports_dir", lambda: tmp_path)

    calls: list[str] = []

    def _make_run(key: str):
        def _run(_settings):
            calls.append(key)
            if key == "trading_days":
                raise RuntimeError("boom")
            return "ok"

        return _run

    fake_stages = tuple(
        SimpleNamespace(key=s.key, label=s.label, run=_make_run(s.key))
        for s in UPDATE_STAGES
    )
    monkeypatch.setattr("stockballdb.update.orchestrator.UPDATE_STAGES", fake_stages)
    manifest_written = {"called": False}
    monkeypatch.setattr(
        "stockballdb.update.orchestrator.write_build_manifest",
        lambda _p: manifest_written.__setitem__("called", True),
    )

    result = run_update()
    assert result.exit_code == EXIT_FAILED
    assert calls == ["trading_days"]
    assert result.report.failure_kind == "FAILED_STAGE"
    assert result.report.manifest_path is None
    assert manifest_written["called"] is False


def test_run_update_validation_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    _patch_happy_path(monkeypatch, fp_before="a", fp_after="b")
    monkeypatch.setattr(
        "stockballdb.update.orchestrator.validate_v1_database",
        MagicMock(side_effect=ValidateV1Error("bad data")),
    )
    monkeypatch.setattr("stockballdb.update.report.reports_dir", lambda: tmp_path)

    result = run_update()
    assert result.exit_code == EXIT_FAILED
    assert result.report.failure_kind == "FAILED_VALIDATION"
    assert result.report.manifest_path is None


def test_run_update_health_unhealthy_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    _patch_happy_path(monkeypatch, fp_before="a", fp_after="b")
    monkeypatch.setattr(
        "stockballdb.update.orchestrator.run_health",
        lambda _e: _health(HealthStatus.UNHEALTHY),
    )
    monkeypatch.setattr("stockballdb.update.report.reports_dir", lambda: tmp_path)

    result = run_update()
    assert result.exit_code == EXIT_FAILED
    assert result.report.failure_kind == "FAILED_HEALTH"
    assert result.report.manifest_path is None


def test_run_update_health_warnings_still_succeeds(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    _patch_happy_path(monkeypatch, fp_before="same", fp_after="same")
    monkeypatch.setattr(
        "stockballdb.update.orchestrator.run_health",
        lambda _e: _health(HealthStatus.HEALTHY_WITH_WARNINGS),
    )
    monkeypatch.setattr("stockballdb.update.report.reports_dir", lambda: tmp_path)

    result = run_update()
    assert result.exit_code == EXIT_SUCCESS
    assert result.report.status == "SUCCESS_NO_CHANGE"


def test_run_update_fingerprint_classification(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    _patch_happy_path(monkeypatch, fp_before="sha256:aaa", fp_after="sha256:bbb")
    monkeypatch.setattr("stockballdb.update.report.reports_dir", lambda: tmp_path)

    updated = run_update()
    assert updated.report.change_classification == "SUCCESS_UPDATED"

    _patch_happy_path(monkeypatch, fp_before="sha256:same", fp_after="sha256:same")
    no_change = run_update()
    assert no_change.report.change_classification == "SUCCESS_NO_CHANGE"


def test_run_update_manifest_receives_snapshots_before_context_reset(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    _patch_happy_path(monkeypatch, fp_before="a", fp_after="a")
    captured: dict = {}

    def _manifest(*args, **kwargs):
        captured["snapshots"] = kwargs.get("snapshots")
        return {"build_id": "x"}

    monkeypatch.setattr(
        "stockballdb.update.orchestrator.manifest_from_health_report",
        _manifest,
    )
    monkeypatch.setattr("stockballdb.update.report.reports_dir", lambda: tmp_path)

    run_update()
    assert captured["snapshots"] is not None
    assert len(captured["snapshots"]) == 1
    assert captured["snapshots"][0].provider == "tiingo"


def test_run_update_json_stdout_parseable(
    monkeypatch: pytest.MonkeyPatch, tmp_path, capsys: pytest.CaptureFixture[str]
) -> None:
    _patch_happy_path(monkeypatch, fp_before="a", fp_after="a")
    monkeypatch.setattr("stockballdb.update.report.reports_dir", lambda: tmp_path)

    result = run_update(json_output=True)
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload["status"] == result.report.status
    assert "StockBallDB Update" in captured.err
    assert captured.out.strip().startswith("{")


def test_run_update_propagates_run_as_of(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    boundary = dt.date(2024, 6, 1)
    seen: dict[str, dt.date | None] = {}

    def _make_run(key: str):
        def _run(settings: Settings):
            seen["run_as_of"] = settings.run_as_of
            return f"{key}=ok"

        return _run

    settings = _settings()
    monkeypatch.setattr(
        "stockballdb.update.orchestrator.run_update_preflight",
        lambda: settings,
    )

    class _Lock:
        def try_acquire(self) -> bool:
            return True

        def release(self) -> None:
            return None

    monkeypatch.setattr(
        "stockballdb.update.orchestrator.AdvisoryLock",
        lambda _url: _Lock(),
    )
    monkeypatch.setattr("stockballdb.update.orchestrator.reset_engine", lambda: None)
    conn = MagicMock()
    conn.__enter__ = lambda s: s
    conn.__exit__ = lambda *a: None
    conn.execute.return_value.scalar_one.return_value = V1_ALEMBIC_HEAD
    engine = MagicMock()
    engine.connect.return_value = conn
    monkeypatch.setattr("stockballdb.update.orchestrator.get_engine", lambda _s: engine)
    monkeypatch.setattr(
        "stockballdb.update.orchestrator.compute_database_fingerprint",
        MagicMock(side_effect=[_fp("a"), _fp("a")]),
    )
    fake_stages = tuple(
        SimpleNamespace(key=s.key, label=s.label, run=_make_run(s.key))
        for s in UPDATE_STAGES[:1]
    )
    monkeypatch.setattr("stockballdb.update.orchestrator.UPDATE_STAGES", fake_stages)
    monkeypatch.setattr(
        "stockballdb.update.orchestrator.validate_v1_database",
        lambda _engine: ["ok"],
    )
    monkeypatch.setattr(
        "stockballdb.update.orchestrator.run_health",
        lambda _engine: _health(),
    )
    monkeypatch.setattr(
        "stockballdb.update.orchestrator.manifest_from_health_report",
        lambda *a, **k: {"build_id": "x"},
    )
    monkeypatch.setattr(
        "stockballdb.update.orchestrator.write_build_manifest",
        lambda _p: None,
    )
    monkeypatch.setattr(
        "stockballdb.update.orchestrator.snapshot_references",
        lambda: [],
    )
    monkeypatch.setattr(
        "stockballdb.update.orchestrator.live_build_context",
        lambda: MagicMock(__enter__=lambda s: s, __exit__=lambda *a: None),
    )
    monkeypatch.setattr("stockballdb.update.orchestrator.reset_context", lambda: None)
    monkeypatch.setattr("stockballdb.update.report.reports_dir", lambda: tmp_path)

    result = run_update(run_as_of=boundary)
    assert result.report.run_as_of == boundary.isoformat()
    assert seen["run_as_of"] == boundary


def test_run_report_sanitizes_secrets() -> None:
    report = RunReport(
        run_id="r",
        command="python -m stockballdb.update",
        run_as_of="2026-01-01",
        started_at=dt.datetime.now(dt.timezone.utc),
        git={"password": "secret"},
    )
    with pytest.raises(ValueError, match="secret-like"):
        report.as_dict()


def test_advisory_lock_release_after_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    released = {"called": False}
    original_release = AdvisoryLock.release

    def _release(self) -> None:
        released["called"] = True
        original_release(self)

    monkeypatch.setattr(AdvisoryLock, "release", _release)
    settings = _settings()
    monkeypatch.setattr(
        "stockballdb.update.orchestrator.run_update_preflight",
        lambda: settings,
    )

    class _Lock:
        def try_acquire(self) -> bool:
            return True

        def release(self) -> None:
            released["called"] = True

    monkeypatch.setattr(
        "stockballdb.update.orchestrator.AdvisoryLock",
        lambda _url: _Lock(),
    )
    monkeypatch.setattr("stockballdb.update.orchestrator.reset_engine", lambda: None)
    conn = MagicMock()
    conn.__enter__ = lambda s: s
    conn.__exit__ = lambda *a: None
    conn.execute.return_value.scalar_one.return_value = V1_ALEMBIC_HEAD
    engine = MagicMock()
    engine.connect.return_value = conn
    monkeypatch.setattr("stockballdb.update.orchestrator.get_engine", lambda _s: engine)
    monkeypatch.setattr(
        "stockballdb.update.orchestrator.compute_database_fingerprint",
        MagicMock(side_effect=RuntimeError("fp boom")),
    )
    monkeypatch.setattr("stockballdb.update.report.reports_dir", lambda: pytest.MonkeyPatch())

    import tempfile
    from pathlib import Path

    tmp = Path(tempfile.mkdtemp())
    monkeypatch.setattr("stockballdb.update.report.reports_dir", lambda: tmp)

    result = run_update()
    assert result.exit_code == EXIT_FAILED
    assert released["called"] is True


def test_advisory_lock_integration() -> None:
    import os

    if not os.getenv("DATABASE_URL"):
        pytest.skip("DATABASE_URL not set")
    from stockballdb.config import load_settings
    from stockballdb.db import reset_engine

    reset_engine()
    settings = load_settings(require_database_url=True)
    lock_a = AdvisoryLock(settings.database_url)
    lock_b = AdvisoryLock(settings.database_url)
    try:
        assert lock_a.try_acquire() is True
        assert lock_b.try_acquire() is False
    finally:
        lock_a.release()
    lock_c = AdvisoryLock(settings.database_url)
    try:
        assert lock_c.try_acquire() is True
    finally:
        lock_c.release()


def test_cli_invalid_as_of() -> None:
    with pytest.raises(SystemExit) as exc:
        update_main.main(["--as-of", "not-a-date"])
    assert exc.value.code == 2


def test_cli_json_exit_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "stockballdb.update.__main__.run_update",
        lambda **kw: SimpleNamespace(exit_code=EXIT_SUCCESS),
    )
    assert update_main.main(["--json"]) == EXIT_SUCCESS
