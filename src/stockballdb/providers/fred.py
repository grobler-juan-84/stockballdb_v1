"""FRED / ALFRED HTTP client (no credentials in logs)."""

from __future__ import annotations

import time
from typing import Any

import requests

FRED_API_BASE = "https://api.stlouisfed.org/fred"


class FredError(Exception):
    """Raised when a FRED/ALFRED request fails."""


def _get(
    path: str,
    api_key: str,
    *,
    params: dict[str, Any] | None = None,
    timeout: float = 120.0,
    retries: int = 4,
    session: requests.Session | None = None,
) -> dict:
    query = {"api_key": api_key, "file_type": "json", **(params or {})}
    http = session or requests.Session()
    last_exc: Exception | None = None
    for attempt in range(retries):
        try:
            response = http.get(
                f"{FRED_API_BASE}/{path}", params=query, timeout=timeout
            )
            if response.status_code != 200:
                raise FredError(
                    f"FRED HTTP {response.status_code} for {path}: "
                    f"{response.text[:200]}"
                )
            return response.json()
        except (requests.RequestException, FredError) as exc:
            last_exc = exc
            time.sleep(2 * (attempt + 1))
    raise FredError(f"FRED request failed for {path}: {last_exc}") from last_exc


def fetch_observations(
    series_id: str,
    api_key: str,
    *,
    realtime_start: str | None = None,
    realtime_end: str | None = None,
    observation_start: str | None = None,
    observation_end: str | None = None,
    units: str | None = None,
    session: requests.Session | None = None,
) -> list[dict]:
    """
    Fetch FRED/ALFRED observations.

    When realtime_start/end span the full ALFRED window, returns all vintages.
    Paginates with limit/offset.
    """
    all_rows: list[dict] = []
    offset = 0
    limit = 100_000
    while True:
        params: dict[str, Any] = {
            "series_id": series_id,
            "limit": limit,
            "offset": offset,
            "sort_order": "asc",
        }
        if realtime_start:
            params["realtime_start"] = realtime_start
        if realtime_end:
            params["realtime_end"] = realtime_end
        if observation_start:
            params["observation_start"] = observation_start
        if observation_end:
            params["observation_end"] = observation_end
        if units:
            params["units"] = units

        payload = _get(
            "series/observations",
            api_key,
            params=params,
            session=session,
        )
        rows = payload.get("observations") or []
        all_rows.extend(rows)
        if len(rows) < limit:
            break
        offset += limit
        time.sleep(0.35)
    return all_rows


def fetch_current_observations(
    series_id: str,
    api_key: str,
    *,
    session: requests.Session | None = None,
) -> list[dict]:
    """Fetch the current (latest vintage) observation history."""
    return fetch_observations(series_id, api_key, session=session)


def fetch_all_vintages(
    series_id: str,
    api_key: str,
    *,
    session: requests.Session | None = None,
) -> list[dict]:
    """Fetch all ALFRED vintages for a series."""
    return fetch_observations(
        series_id,
        api_key,
        realtime_start="1776-07-04",
        realtime_end="9999-12-31",
        session=session,
    )
