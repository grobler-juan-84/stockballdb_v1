"""Load environment configuration for StockBallDB."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


class ConfigError(Exception):
    """Raised when required configuration is missing or invalid."""


@dataclass(frozen=True)
class Settings:
    """Application settings loaded from the environment."""

    database_url: str
    tiingo_api_key: str | None = None
    fred_api_key: str | None = None
    eia_api_key: str | None = None


def load_settings(
    *,
    require_database_url: bool = True,
    require_tiingo_api_key: bool = False,
    require_fred_api_key: bool = False,
) -> Settings:
    """
    Load settings from environment variables.

    Loads a local ``.env`` file if present. When ``require_database_url`` is
    True (default), raises ``ConfigError`` if ``DATABASE_URL`` is missing.
    When ``require_tiingo_api_key`` is True, raises ``ConfigError`` if
    ``TIINGO_API_KEY`` is missing.
    When ``require_fred_api_key`` is True, raises ``ConfigError`` if
    ``FRED_API_KEY`` is missing.
    """
    load_dotenv()

    database_url = os.getenv("DATABASE_URL", "").strip()
    if require_database_url and not database_url:
        raise ConfigError(
            "DATABASE_URL is required. Copy .env.example to .env and set "
            "DATABASE_URL to your local PostgreSQL connection string."
        )

    tiingo_api_key = _optional("TIINGO_API_KEY")
    if require_tiingo_api_key and not tiingo_api_key:
        raise ConfigError(
            "TIINGO_API_KEY is required. Copy .env.example to .env and set "
            "TIINGO_API_KEY for Tiingo market-data acquisition."
        )

    fred_api_key = _optional("FRED_API_KEY")
    if require_fred_api_key and not fred_api_key:
        raise ConfigError(
            "FRED_API_KEY is required. Copy .env.example to .env and set "
            "FRED_API_KEY for FRED/ALFRED macro acquisition."
        )

    return Settings(
        database_url=database_url,
        tiingo_api_key=tiingo_api_key,
        fred_api_key=fred_api_key,
        eia_api_key=_optional("EIA_API_KEY"),
    )


def _optional(name: str) -> str | None:
    value = os.getenv(name, "").strip()
    return value or None
