"""Tiingo HTTP client for end-of-day prices."""

from __future__ import annotations

import json

import requests

from stockballdb.providers.snapshot_transport import tiingo_request_identity
from stockballdb.snapshots.context import acquire_bytes, assert_network_allowed
from stockballdb.providers.tiingo_constants import (
    DEFAULT_START_DATE,
    TIINGO_DAILY_PRICES_URL,
    TIINGO_PRICE_FIELDS,
)

# Re-export for backward compatibility
__all__ = [
    "DEFAULT_START_DATE",
    "TIINGO_DAILY_PRICES_URL",
    "TIINGO_PRICE_FIELDS",
    "TiingoError",
    "fetch_daily_prices",
    "fetch_daily_prices_bytes",
    "parse_daily_prices_bytes",
]


class TiingoError(Exception):
    """Raised when a Tiingo request fails or returns unexpected data."""


def fetch_daily_prices_bytes(
    symbol: str,
    api_key: str,
    *,
    start_date: str | None = DEFAULT_START_DATE,
    end_date: str | None = None,
    timeout: float = 120.0,
    session: requests.Session | None = None,
) -> bytes:
    """Fetch raw Tiingo EOD JSON response bytes (network; no snapshot)."""
    assert_network_allowed("tiingo")
    url = TIINGO_DAILY_PRICES_URL.format(ticker=symbol)
    params: dict[str, str] = {}
    if start_date:
        params["startDate"] = start_date
    if end_date:
        params["endDate"] = end_date
    headers = {
        "Authorization": f"Token {api_key}",
        "Content-Type": "application/json",
    }
    http = session or requests.Session()
    try:
        response = http.get(url, headers=headers, params=params, timeout=timeout)
    except requests.RequestException as exc:
        raise TiingoError(f"Tiingo request failed for {symbol}: {exc}") from exc
    if response.status_code != 200:
        raise TiingoError(
            f"Tiingo HTTP {response.status_code} for {symbol}: {response.text[:200]}"
        )
    return response.content


def parse_daily_prices_bytes(raw_bytes: bytes, *, symbol: str) -> list[dict]:
    """Parse Tiingo EOD JSON bytes into a list of daily bar dicts."""
    try:
        payload = json.loads(raw_bytes.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        raise TiingoError(f"Tiingo returned non-JSON for {symbol}") from exc
    if not isinstance(payload, list):
        raise TiingoError(
            f"Tiingo unexpected payload type for {symbol}: {type(payload).__name__}"
        )
    if not payload:
        raise TiingoError(f"Tiingo returned empty price history for {symbol}")
    first = payload[0]
    if not isinstance(first, dict):
        raise TiingoError(f"Tiingo unexpected row type for {symbol}")
    missing = TIINGO_PRICE_FIELDS - set(first.keys())
    if missing:
        raise TiingoError(
            f"Tiingo response missing fields for {symbol}: {sorted(missing)}"
        )
    return payload


def fetch_daily_prices(
    symbol: str,
    api_key: str,
    *,
    start_date: str | None = DEFAULT_START_DATE,
    end_date: str | None = None,
    timeout: float = 120.0,
    session: requests.Session | None = None,
) -> list[dict]:
    """
    Fetch Tiingo EOD history via snapshot boundary when build context is active.

    LIVE: network → snapshot → parse from stored bytes.
    SNAPSHOT: load manifest snapshot → parse.
    """
    identity = tiingo_request_identity(symbol, start_date=start_date, end_date=end_date)

    def _live() -> tuple[bytes, dict]:
        return (
            fetch_daily_prices_bytes(
                symbol,
                api_key,
                start_date=start_date,
                end_date=end_date,
                timeout=timeout,
                session=session,
            ),
            {"http_status": 200},
        )

    raw = acquire_bytes(
        provider="tiingo",
        source_identifier=symbol,
        source_type="api_json",
        request_identity=identity,
        content_type="application/json",
        fetch_live=_live,
    )
    return parse_daily_prices_bytes(raw, symbol=symbol)
