"""FRED / ALFRED HTTP client (no credentials in logs)."""

from __future__ import annotations

import json
import time
from typing import Any

import requests

from stockballdb.providers.snapshot_transport import fred_request_identity
from stockballdb.snapshots.context import acquire_bytes, assert_network_allowed
from stockballdb.snapshots.pagination import concat_pages, split_pages

FRED_API_BASE = "https://api.stlouisfed.org/fred"


class FredError(Exception):
    """Raised when a FRED/ALFRED request fails."""


def _get_bytes(
    path: str,
    api_key: str,
    *,
    params: dict[str, Any] | None = None,
    timeout: float = 120.0,
    retries: int = 4,
    session: requests.Session | None = None,
) -> tuple[bytes, dict[str, Any]]:
    assert_network_allowed("fred")
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
            meta = {
                "http_status": response.status_code,
                "etag": response.headers.get("ETag"),
                "last_modified": response.headers.get("Last-Modified"),
            }
            return response.content, meta
        except (requests.RequestException, FredError) as exc:
            last_exc = exc
            time.sleep(2 * (attempt + 1))
    raise FredError(f"FRED request failed for {path}: {last_exc}") from last_exc


def fetch_observations_bytes(
    series_id: str,
    api_key: str,
    *,
    realtime_start: str | None = None,
    realtime_end: str | None = None,
    observation_start: str | None = None,
    observation_end: str | None = None,
    units: str | None = None,
    session: requests.Session | None = None,
) -> bytes:
    """Fetch paginated FRED/ALFRED observations as full_concat_v1 bytes."""
    pages: list[tuple[int, bytes]] = []
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
        body, _meta = _get_bytes(
            "series/observations",
            api_key,
            params=params,
            session=session,
        )
        pages.append((offset, body))
        payload = json.loads(body.decode("utf-8"))
        rows = payload.get("observations") or []
        if len(rows) < limit:
            break
        offset += limit
        time.sleep(0.35)
    return concat_pages(pages)


def parse_observations_bytes(data: bytes) -> list[dict]:
    """Parse full_concat_v1 FRED bytes into observation rows."""
    all_rows: list[dict] = []
    for _offset, body in split_pages(data):
        payload = json.loads(body.decode("utf-8"))
        all_rows.extend(payload.get("observations") or [])
    return all_rows


def _acquire_fred_bytes(
    series_id: str,
    api_key: str,
    *,
    realtime_start: str | None = None,
    realtime_end: str | None = None,
    session: requests.Session | None = None,
) -> bytes:
    identity = fred_request_identity(
        series_id,
        realtime_start=realtime_start,
        realtime_end=realtime_end,
    )
    provider = identity["provider"]
    source_type = "api_json"

    def _live() -> tuple[bytes, dict[str, Any]]:
        raw = fetch_observations_bytes(
            series_id,
            api_key,
            realtime_start=realtime_start,
            realtime_end=realtime_end,
            session=session,
        )
        return raw, {"http_status": 200}

    return acquire_bytes(
        provider=provider,
        source_identifier=series_id,
        source_type=source_type,
        request_identity=identity,
        content_type="application/json",
        fetch_live=_live,
    )


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
    """Fetch observations via snapshot boundary."""
    if observation_start or observation_end or units:
        # Preflight/specialized calls bypass snapshot store when params differ
        raw = fetch_observations_bytes(
            series_id,
            api_key,
            realtime_start=realtime_start,
            realtime_end=realtime_end,
            observation_start=observation_start,
            observation_end=observation_end,
            units=units,
            session=session,
        )
        return parse_observations_bytes(raw)
    raw = _acquire_fred_bytes(
        series_id,
        api_key,
        realtime_start=realtime_start,
        realtime_end=realtime_end,
        session=session,
    )
    return parse_observations_bytes(raw)


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
