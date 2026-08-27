"""Unit tests for V1 build orchestration and preflight."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from stockballdb.build_v1 import run_build_v1
from stockballdb.v1.preflight import (
    REQUIRED_CALENDAR_VERSION,
    PreflightError,
    run_preflight,
)
from stockballdb.v1.stages import BUILD_STAGES


def test_build_stages_order() -> None:
    assert [s.key for s in BUILD_STAGES] == [
        "migrate",
        "trading_days",
        "daily_market_data",
        "derive_market_data",
        "market_outcomes",
        "asset_regimes",
        "macro_conditions",
        "scheduled_events",
        "calendar_context",
    ]


def test_run_build_v1_fail_fast_skips_later_stages(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    settings = SimpleNamespace(
        database_url="postgresql+psycopg://u:p@localhost:5432/x",
        tiingo_api_key="t",
        fred_api_key="f",
    )
    monkeypatch.setattr("stockballdb.build_v1.run_preflight", lambda: settings)

    calls: list[str] = []

    def _make_run(key: str):
        def _run(_settings):
            calls.append(key)
            if key == "trading_days":
                raise RuntimeError("boom trading_days")
            return "ok"

        return _run

    fake_stages = tuple(
        SimpleNamespace(key=s.key, label=s.label, run=_make_run(s.key))
        for s in BUILD_STAGES
    )
    monkeypatch.setattr("stockballdb.build_v1.BUILD_STAGES", fake_stages)
    monkeypatch.setattr("stockballdb.build_v1.write_build_report", lambda **kw: None)

    code = run_build_v1(run_pytest=False)
    assert code == 1
    assert calls == ["migrate", "trading_days"]
    out = capsys.readouterr().out
    assert "STATUS: PARTIAL" in out
    assert "FAILED STAGE: 1/8 trading_days" in out
    assert "V1 READY" not in out


def test_preflight_missing_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "stockballdb.v1.preflight.load_settings",
        MagicMock(side_effect=__import__("stockballdb.config", fromlist=["ConfigError"]).ConfigError("DATABASE_URL is required")),
    )
    with pytest.raises(PreflightError, match="DATABASE_URL"):
        run_preflight()


def test_preflight_missing_tiingo(monkeypatch: pytest.MonkeyPatch) -> None:
    from stockballdb.config import ConfigError

    monkeypatch.setattr(
        "stockballdb.v1.preflight.load_settings",
        MagicMock(side_effect=ConfigError("TIINGO_API_KEY is required")),
    )
    with pytest.raises(PreflightError, match="TIINGO_API_KEY"):
        run_preflight()


def test_preflight_missing_fred(monkeypatch: pytest.MonkeyPatch) -> None:
    from stockballdb.config import ConfigError

    monkeypatch.setattr(
        "stockballdb.v1.preflight.load_settings",
        MagicMock(side_effect=ConfigError("FRED_API_KEY is required")),
    )
    with pytest.raises(PreflightError, match="FRED_API_KEY"):
        run_preflight()


def test_preflight_wrong_calendar_version(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = SimpleNamespace(
        database_url="postgresql+psycopg://u:p@localhost:5432/x",
        tiingo_api_key="t",
        fred_api_key="f",
    )
    monkeypatch.setattr(
        "stockballdb.v1.preflight.load_settings",
        lambda **kw: settings,
    )
    monkeypatch.setattr(
        "stockballdb.v1.preflight.mcal.__version__",
        "0.0.0",
        raising=False,
    )
    # pandas_market_calendars module attribute
    import stockballdb.v1.preflight as pf

    monkeypatch.setattr(pf.mcal, "__version__", "9.9.9")
    with pytest.raises(PreflightError, match=REQUIRED_CALENDAR_VERSION):
        run_preflight()
