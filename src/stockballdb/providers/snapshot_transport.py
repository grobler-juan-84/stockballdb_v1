"""Request identity helpers for snapshot metadata."""

from __future__ import annotations

from typing import Any


def tiingo_request_identity(
    symbol: str,
    *,
    start_date: str | None,
    end_date: str | None,
) -> dict[str, Any]:
    return {
        "provider": "tiingo",
        "endpoint": "daily_prices",
        "symbol": symbol,
        "start_date": start_date,
        "end_date": end_date,
    }


def fred_request_identity(
    series_id: str,
    *,
    realtime_start: str | None = None,
    realtime_end: str | None = None,
    observation_start: str | None = None,
    observation_end: str | None = None,
) -> dict[str, Any]:
    provider = "alfred" if realtime_start or realtime_end else "fred"
    return {
        "provider": provider,
        "endpoint": "series/observations",
        "series_id": series_id,
        "realtime_start": realtime_start,
        "realtime_end": realtime_end,
        "observation_start": observation_start,
        "observation_end": observation_end,
        "pagination": "full_concat_v1",
    }


def fed_html_request_identity(path: str) -> dict[str, Any]:
    return {
        "provider": "federal_reserve",
        "endpoint": "html_page",
        "path": path,
    }
