"""Transport tests for stockballdb.api (V2 P2)."""

from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient

from stockballdb.app.errors import AppNotFoundError, AppUnavailableError
from stockballdb.app.results import (
    ApplicationStatus,
    DataDomainInfo,
    FieldInfo,
    InstrumentInfo,
)
from stockballdb.api.app import create_app
from stockballdb.market_data.universe import WTI_SYMBOL


def _client() -> TestClient:
    return TestClient(create_app())


def test_ready_does_not_require_database() -> None:
    with patch("stockballdb.app.read.status.ensure_database_available") as ensure:
        response = _client().get("/ready")
    ensure.assert_not_called()
    assert response.status_code == 200
    body = response.json()
    assert body == {"ready": True, "service": "stockballdb-api"}


def test_instruments_endpoint_structure_and_wti() -> None:
    response = _client().get("/api/catalog/instruments")
    assert response.status_code == 200
    rows = response.json()
    assert isinstance(rows, list)
    assert len(rows) >= 15
    by_symbol = {r["symbol"]: r for r in rows}
    assert set(by_symbol[WTI_SYMBOL].keys()) == {"symbol", "asset_type", "close_only"}
    assert by_symbol[WTI_SYMBOL]["asset_type"] == "commodity"
    assert by_symbol[WTI_SYMBOL]["close_only"] is True
    assert by_symbol["SPY"]["asset_type"] == "etf"


def test_domains_endpoint() -> None:
    response = _client().get("/api/catalog/domains")
    assert response.status_code == 200
    rows = response.json()
    keys = {r["key"] for r in rows}
    assert "daily_market_data" in keys
    assert "trading_days" in keys
    sample = rows[0]
    assert "model" not in sample
    assert "sortable_columns" in sample
    assert isinstance(sample["sortable_columns"], list)


def test_fields_known_domain() -> None:
    response = _client().get("/api/catalog/domains/daily_market_data/fields")
    assert response.status_code == 200
    names = {r["name"] for r in response.json()}
    assert "adj_close" in names
    assert "symbol" in names


def test_fields_unknown_domain_is_structured_404() -> None:
    response = _client().get("/api/catalog/domains/not_a_real_table/fields")
    assert response.status_code == 404
    body = response.json()
    assert "error" in body
    assert body["error"]["code"] == "not_found"
    assert "message" in body["error"]
    assert "traceback" not in response.text.lower()
    assert "Traceback" not in response.text


def test_status_success_payload() -> None:
    fake = ApplicationStatus(
        available=True,
        database_connected=True,
        health_status="HEALTHY",
        validate_v1_pass=True,
        alembic_head="a8f3c2d1b4e5",
        expected_alembic_head="a8f3c2d1b4e5",
        calendar_version="5.4.0",
        finding_counts={"INFO": 1},
        error_message=None,
    )
    with patch("stockballdb.app.read.status.get_status", return_value=fake):
        response = _client().get("/api/status")
    assert response.status_code == 200
    body = response.json()
    assert body["available"] is True
    assert body["health_status"] == "HEALTHY"
    assert body["finding_counts"]["INFO"] == 1


def test_status_unavailable_is_structured_200_from_app_summary() -> None:
    """P1 get_status returns available=False without raising — HTTP 200 with payload."""
    fake = ApplicationStatus(
        available=False,
        database_connected=False,
        health_status=None,
        validate_v1_pass=None,
        alembic_head=None,
        expected_alembic_head=None,
        calendar_version=None,
        finding_counts={},
        error_message="database unavailable: boom",
    )
    with patch("stockballdb.app.read.status.get_status", return_value=fake):
        response = _client().get("/api/status")
    assert response.status_code == 200
    body = response.json()
    assert body["available"] is False
    assert body["error_message"] is not None


def test_app_unavailable_error_maps_to_503() -> None:
    with patch(
        "stockballdb.app.read.catalog.list_instruments",
        side_effect=AppUnavailableError("database unavailable: x"),
    ):
        response = _client().get("/api/catalog/instruments")
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "unavailable"


def test_app_not_found_error_maps_to_404() -> None:
    with patch(
        "stockballdb.app.read.catalog.get_fields",
        side_effect=AppNotFoundError("unknown data domain: 'x'"),
    ):
        response = _client().get("/api/catalog/domains/x/fields")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_unhandled_error_is_500_without_stack_in_body() -> None:
    # ServerErrorMiddleware re-raises after the Exception handler responds;
    # disable that so we assert the HTTP body clients actually receive.
    client = TestClient(create_app(), raise_server_exceptions=False)
    with patch(
        "stockballdb.app.read.catalog.list_data_domains",
        side_effect=RuntimeError("boom"),
    ):
        response = client.get("/api/catalog/domains")
    assert response.status_code == 500
    body = response.json()
    assert body["error"]["code"] == "internal_error"
    assert body["error"]["message"] == "an unexpected error occurred"
    assert "boom" not in response.text
    assert "Traceback" not in response.text


def test_instrument_dto_from_app() -> None:
    from stockballdb.api.schemas import DataDomainOut, FieldOut, InstrumentOut

    inst = InstrumentOut.from_app(
        InstrumentInfo(symbol="SPY", asset_type="etf", close_only=False)
    )
    assert inst.model_dump() == {
        "symbol": "SPY",
        "asset_type": "etf",
        "close_only": False,
    }
    domain = DataDomainOut.from_app(
        DataDomainInfo(
            key="trading_days",
            display_name="Trading Days",
            date_column="date",
            symbol_column=None,
            sortable_columns=("date",),
            boolean_filter_columns=(),
            supports_event_type_filter=False,
        )
    )
    assert domain.key == "trading_days"
    field = FieldOut.from_app(
        FieldInfo(name="date", sortable=True, boolean_filterable=False, definition=None)
    )
    assert field.name == "date"
