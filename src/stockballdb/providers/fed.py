"""Federal Reserve HTML acquisition helpers."""

from __future__ import annotations

import time

import requests

FED_BASE = "https://www.federalreserve.gov"


class FedError(Exception):
    """Raised when a Federal Reserve page fetch fails."""


def fetch_text(
    path_or_url: str,
    *,
    timeout: float = 90.0,
    retries: int = 5,
    session: requests.Session | None = None,
) -> str:
    """GET a Fed page; path may be absolute URL or site-relative."""
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
            return response.text
        except (requests.RequestException, FedError) as exc:
            last_exc = exc
            if isinstance(exc, FedError) and "404" in str(exc):
                raise
            time.sleep(2 * (attempt + 1))
    raise FedError(f"Fed request failed for {url}: {last_exc}") from last_exc
