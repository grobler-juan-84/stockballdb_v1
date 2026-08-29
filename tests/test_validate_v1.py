"""Tests for whole-database V1 validator."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from sqlalchemy.engine import Engine

from stockballdb.validate_v1 import ValidateV1Error, validate_v1_database
from stockballdb.v1.preflight import REQUIRED_CALENDAR_VERSION, V1_ALEMBIC_HEAD


class _ScalarResult:
    def __init__(self, value):
        self._value = value

    def scalar_one(self):
        return self._value


def _scripted_conn(responses: list):
    """Connection whose execute() returns scripted scalar results in order."""
    conn = MagicMock()
    it = iter(responses)

    def _execute(*_a, **_k):
        try:
            return _ScalarResult(next(it))
        except StopIteration as exc:
            raise AssertionError("unexpected extra SQL execute") from exc

    conn.execute.side_effect = _execute
    return conn


def _engine_with_conn(conn) -> Engine:
    engine = MagicMock(spec=Engine)
    cm = MagicMock()
    cm.__enter__.return_value = conn
    cm.__exit__.return_value = False
    engine.connect.return_value = cm
    return engine


def test_validator_wrong_calendar_version(monkeypatch: pytest.MonkeyPatch) -> None:
    import stockballdb.validate_v1 as mod

    monkeypatch.setattr(mod.mcal, "__version__", "0.0.0")
    engine = MagicMock(spec=Engine)
    with pytest.raises(ValidateV1Error, match=REQUIRED_CALENDAR_VERSION):
        validate_v1_database(engine)


def test_validator_detects_broken_macro_grain(monkeypatch: pytest.MonkeyPatch) -> None:
    import stockballdb.validate_v1 as mod

    monkeypatch.setattr(mod.mcal, "__version__", REQUIRED_CALENDAR_VERSION)
    # alembic, td, macro, cal
    conn = _scripted_conn([V1_ALEMBIC_HEAD, 10, 9, 10])
    engine = _engine_with_conn(conn)
    with pytest.raises(ValidateV1Error, match="macro_conditions"):
        validate_v1_database(engine)


def test_validator_detects_market_date_outside_spine(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import stockballdb.validate_v1 as mod

    monkeypatch.setattr(mod.mcal, "__version__", REQUIRED_CALENDAR_VERSION)
    # After grain checks, first outside-spine table fails
    responses = [
        V1_ALEMBIC_HEAD,  # alembic
        2,  # td
        2,  # macro
        2,  # cal
        0,  # missing_macro
        0,  # missing_cal
        2,  # dmd
        2,  # mo
        2,  # ar
        0,  # mo orphans
        0,  # ar orphans
        1,  # daily_market_data outside trading_days
    ]
    engine = _engine_with_conn(_scripted_conn(responses))
    with pytest.raises(ValidateV1Error, match="outside trading_days"):
        validate_v1_database(engine)


def test_validator_detects_drawdown_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    import stockballdb.validate_v1 as mod

    monkeypatch.setattr(mod.mcal, "__version__", REQUIRED_CALENDAR_VERSION)
    responses = [
        V1_ALEMBIC_HEAD,
        2,
        2,
        2,
        0,
        0,
        2,
        2,
        2,
        0,
        0,
        0,
        0,
        0,  # three tables outside spine
        3,  # dd_bad
    ]
    engine = _engine_with_conn(_scripted_conn(responses))
    with pytest.raises(ValidateV1Error, match="drawdown identity"):
        validate_v1_database(engine)


def test_validator_detects_outcome_identity_mismatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import stockballdb.validate_v1 as mod

    monkeypatch.setattr(mod.mcal, "__version__", REQUIRED_CALENDAR_VERSION)
    responses = [
        V1_ALEMBIC_HEAD,
        2,
        2,
        2,
        0,
        0,
        2,
        2,
        2,
        0,
        0,
        0,
        0,
        0,
        0,  # dd ok
        5,  # r1_bad
    ]
    engine = _engine_with_conn(_scripted_conn(responses))
    with pytest.raises(ValidateV1Error, match="return_1d"):
        validate_v1_database(engine)


def test_validator_detects_event_context_mismatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import stockballdb.validate_v1 as mod

    monkeypatch.setattr(mod.mcal, "__version__", REQUIRED_CALENDAR_VERSION)
    responses = [
        V1_ALEMBIC_HEAD,
        2,
        2,
        2,
        0,
        0,
        2,
        2,
        2,
        0,
        0,
        0,
        0,
        0,
        0,
        0,  # r1 ok
        10,  # is_fomc_day true count
        9,  # on-calendar fomc
    ]
    engine = _engine_with_conn(_scripted_conn(responses))
    with pytest.raises(ValidateV1Error, match="is_fomc_day"):
        validate_v1_database(engine)


def test_validator_success_path(monkeypatch: pytest.MonkeyPatch) -> None:
    import stockballdb.validate_v1 as mod

    monkeypatch.setattr(mod.mcal, "__version__", REQUIRED_CALENDAR_VERSION)
    monkeypatch.setattr(
        mod,
        "collect_diagnostics",
        lambda _e: {"trading_days": 2, "daily_market_data": 2},
    )
    # event flags: 4 types each (true_n, on_cal)
    responses = [
        V1_ALEMBIC_HEAD,
        2,
        2,
        2,
        0,
        0,
        2,
        2,
        2,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        # 4 event types
        1,
        1,
        1,
        1,
        1,
        1,
        1,
        1,
        0,  # null_dd
        0,  # first_null_r1
        15,  # symbols
        0,  # malformed_etf
        0,  # malformed_close
    ]
    engine = _engine_with_conn(_scripted_conn(responses))
    diagnostics = validate_v1_database(engine)
    assert any("alembic=" in d for d in diagnostics)
    assert any("trading_days=2" in d for d in diagnostics)
