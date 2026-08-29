"""Federal Reserve HTML acquisition helpers."""

from __future__ import annotations

import time

import requests

from stockballdb.providers.snapshot_transport import fed_html_request_identity
from stockballdb.snapshots.context import acquire_bytes, assert_network_allowed

FED_BASE = "https://www.federalreserve.gov"


class FedError(Exception):
    """Raised when a Federal Reserve page fetch fails."""


def fetch_html_bytes(
    path_or_url: str,
    *,
    timeout: float = 90.0,
    retries: int = 5,
    session: requests.Session | None = None,
) -> bytes:
    """GET a Fed page and return raw bytes (network; no snapshot)."""
    assert_network_allowed("federal_reserve")
    url = (
        path_or_url
        if path_or_url.startswith("http")
        else f"{FED_BASE}{path_or_url}"
    )
    http = session or requests.Session()
    headers = {"User-Agent": "StockBallDB/0.1 (research; scheduled_events)"}
    last_exc: Exception | None = None
    for attempt in range(retries):
        try:
            response = http.get(url, timeout=timeout, headers=headers)
            if response.status_code == 404:
                raise FedError(f"Fed HTTP 404 for {url}")
            if response.status_code != 200:
                raise FedError(
                    f"Fed HTTP {response.status_code} for {url}: "
                    f"{response.text[:200]}"
                )
            return response.content
        except (requests.RequestException, FedError) as exc:
            last_exc = exc
            if isinstance(exc, FedError) and "404" in str(exc):
                raise
            time.sleep(2 * (attempt + 1))
    raise FedError(f"Fed request failed for {url}: {last_exc}") from last_exc


def parse_html_bytes(raw_bytes: bytes) -> str:
    return raw_bytes.decode("utf-8", errors="replace")


def fetch_text(
    path_or_url: str,
    *,
    timeout: float = 90.0,
    retries: int = 5,
    session: requests.Session | None = None,
) -> str:
    """GET a Fed page via snapshot boundary; returns decoded HTML text."""
    path = path_or_url
    if path.startswith(FED_BASE):
        path = path[len(FED_BASE) :]
    if path.startswith("http"):
        # absolute non-FED_BASE URL — use as-is in identity
        identity = fed_html_request_identity(path_or_url)
    else:
        identity = fed_html_request_identity(path)

    def _live() -> tuple[bytes, dict]:
        return (
            fetch_html_bytes(
                path_or_url,
                timeout=timeout,
                retries=retries,
                session=session,
            ),
            {"http_status": 200},
        )

    source_id = identity.get("path", path_or_url)
    raw = acquire_bytes(
        provider="federal_reserve",
        source_identifier=source_id,
        source_type="html_page",
        request_identity=identity,
        content_type="text/html",
        encoding="utf-8",
        fetch_live=_live,
    )
    return parse_html_bytes(raw)
