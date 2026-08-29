"""Preflight checks before a V1 full rebuild."""

from __future__ import annotations

import sys

import pandas_market_calendars as mcal

from stockballdb.config import ConfigError, Settings, load_settings
from stockballdb.db import check_connection, reset_engine
from stockballdb.market_data.universe import PHASE_2A_ETF_SYMBOLS
from stockballdb.providers.fed import FedError, fetch_text
from stockballdb.providers.fred import FredError, fetch_observations
from stockballdb.providers.tiingo import TiingoError, fetch_daily_prices

REQUIRED_CALENDAR_VERSION = "5.4.0"
V1_ALEMBIC_HEAD = "a8f3c2d1b4e5"
EXPECTED_ETF_COUNT = 14


class PreflightError(Exception):
    """Raised when V1 preflight fails."""


def run_preflight(settings: Settings | None = None) -> Settings:
    """
    Validate environment, credentials, and lightweight source reachability.

    Does not perform full historical acquisition.
    """
    if sys.version_info < (3, 11):
        raise PreflightError(
            f"Python >= 3.11 required; found {sys.version_info.major}."
            f"{sys.version_info.minor}"
        )

    try:
        cfg = settings or load_settings(
            require_database_url=True,
            require_tiingo_api_key=True,
            require_fred_api_key=True,
        )
    except ConfigError as exc:
        raise PreflightError(str(exc)) from exc

    if mcal.__version__ != REQUIRED_CALENDAR_VERSION:
        raise PreflightError(
            f"pandas_market_calendars must be {REQUIRED_CALENDAR_VERSION}; "
            f"found {mcal.__version__}"
        )

    if len(PHASE_2A_ETF_SYMBOLS) != EXPECTED_ETF_COUNT:
        raise PreflightError(
            f"expected {EXPECTED_ETF_COUNT} ETF symbols; "
            f"found {len(PHASE_2A_ETF_SYMBOLS)}"
        )

    reset_engine()
    try:
        check_connection(cfg)
    except Exception as exc:
        raise PreflightError(f"database connection failed: {exc}") from exc

    assert cfg.tiingo_api_key is not None
    assert cfg.fred_api_key is not None

    try:
        bars = fetch_daily_prices(
            "SPY",
            cfg.tiingo_api_key,
            start_date="2024-01-02",
            end_date="2024-01-05",
            timeout=60.0,
        )
        if not bars:
            raise PreflightError("Tiingo probe returned no bars for SPY")
    except TiingoError as exc:
        raise PreflightError(f"Tiingo unreachable or unauthorized: {exc}") from exc

    try:
        obs = fetch_observations(
            "DFF",
            cfg.fred_api_key,
            observation_start="2024-01-02",
            observation_end="2024-01-05",
        )
        if not obs:
            raise PreflightError("FRED probe returned no observations for DFF")
    except FredError as exc:
        raise PreflightError(f"FRED unreachable or unauthorized: {exc}") from exc

    try:
        html = fetch_text(
            "/monetarypolicy/fomccalendars.htm",
            timeout=45.0,
            retries=2,
        )
        if "FOMC" not in html:
            raise PreflightError("Federal Reserve calendar page unexpected content")
    except FedError as exc:
        raise PreflightError(f"Federal Reserve source unreachable: {exc}") from exc

    return cfg
