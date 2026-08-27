"""Configuration loading tests."""

import pytest

from stockballdb.config import ConfigError, load_settings


def test_load_settings_requires_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("TIINGO_API_KEY", "")
    # Avoid picking up a developer's real .env if present: force empty after load
    monkeypatch.setattr(
        "stockballdb.config.load_dotenv",
        lambda *args, **kwargs: None,
    )
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(ConfigError, match="DATABASE_URL"):
        load_settings(require_database_url=True)


def test_load_settings_reads_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "stockballdb.config.load_dotenv",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://user:pass@localhost:5432/stockballdb",
    )
    monkeypatch.setenv("TIINGO_API_KEY", "tiingo-test")
    monkeypatch.setenv("FRED_API_KEY", "")
    monkeypatch.delenv("EIA_API_KEY", raising=False)

    settings = load_settings(require_database_url=True)

    assert settings.database_url.startswith("postgresql+psycopg://")
    assert settings.tiingo_api_key == "tiingo-test"
    assert settings.fred_api_key is None
    assert settings.eia_api_key is None


def test_load_settings_optional_without_database_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "stockballdb.config.load_dotenv",
        lambda *args, **kwargs: None,
    )
    monkeypatch.delenv("DATABASE_URL", raising=False)

    settings = load_settings(require_database_url=False)
    assert settings.database_url == ""
