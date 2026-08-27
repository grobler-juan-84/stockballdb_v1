"""Tiingo HTTP client for end-of-day prices."""

from __future__ import annotations

import requests

TIINGO_DAILY_PRICES_URL = "https://api.tiingo.com/tiingo/daily/{ticker}/prices"

# Without startDate, Tiingo returns only the latest bar. Request from the
# StockBallDB calendar floor so each ETF returns its full available history.
DEFAULT_START_DATE = "1957-01-01"


# Verified against live Tiingo EOD JSON (2026-08-27).
TIINGO_PRICE_FIELDS = frozenset(
    {
        "date",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "adjOpen",
        "adjHigh",
        "adjLow",
        "adjClose",
        "adjVolume",
        "divCash",
        "splitFactor",
    }
)


class TiingoError(Exception):
    """Raised when a Tiingo request fails or returns unexpected data."""


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
    Fetch Tiingo EOD price history for ``symbol``.

    Returns the raw JSON list of daily bars. Does not log the API key.
    Defaults ``start_date`` to 1957-01-01 so Tiingo returns full history
    (omitting startDate yields only the latest bar).
    """
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

    try:
        payload = response.json()
    except ValueError as exc:
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
