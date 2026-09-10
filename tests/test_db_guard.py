"""Unit tests for mutable test-database guard (no live DB required)."""

from __future__ import annotations

import pytest

from stockballdb.config import database_endpoint_identity, same_database_url
from stockballdb.testing import (
    MutableTestDatabaseError,
    mutable_test_database_url_from_env,
    require_mutable_test_settings,
    resolve_mutable_test_database_url,
)


PRIMARY = "postgresql+psycopg://user:pass@localhost:5432/stockballdb"
TEST_DISTINCT = "postgresql+psycopg://user:pass@localhost:5432/stockballdb_test"
TEST_SAME_CREDS_DIFF = (
    "postgresql+psycopg://other:secret@localhost:5432/stockballdb"
)


@pytest.fixture(autouse=True)
def _no_dotenv(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("stockballdb.testing.load_dotenv", lambda *a, **k: None)
    monkeypatch.setattr("stockballdb.config.load_dotenv", lambda *a, **k: None)


def test_endpoint_identity_ignores_credentials() -> None:
    a = database_endpoint_identity(PRIMARY)
    b = database_endpoint_identity(TEST_SAME_CREDS_DIFF)
    assert a == b
    assert a == ("localhost", 5432, "stockballdb")


def test_same_database_url_distinct_databases() -> None:
    assert not same_database_url(PRIMARY, TEST_DISTINCT)
    assert same_database_url(PRIMARY, TEST_SAME_CREDS_DIFF)
    assert same_database_url(
        "postgresql://u:p@127.0.0.1:5432/db",
        "postgresql+psycopg://x:y@127.0.0.1/db",  # default port 5432
    )


def test_resolve_unset_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("STOCKBALLDB_TEST_DATABASE_URL", raising=False)
    with pytest.raises(MutableTestDatabaseError, match="is required"):
        resolve_mutable_test_database_url(primary_database_url=PRIMARY)


def test_resolve_never_falls_back_to_primary(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("STOCKBALLDB_TEST_DATABASE_URL", raising=False)
    monkeypatch.setenv("DATABASE_URL", PRIMARY)
    with pytest.raises(MutableTestDatabaseError, match="never fall back"):
        resolve_mutable_test_database_url()
    assert mutable_test_database_url_from_env() == ""


def test_resolve_distinct_accepted(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STOCKBALLDB_TEST_DATABASE_URL", TEST_DISTINCT)
    assert (
        resolve_mutable_test_database_url(primary_database_url=PRIMARY)
        == TEST_DISTINCT
    )


def test_resolve_same_database_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STOCKBALLDB_TEST_DATABASE_URL", PRIMARY)
    with pytest.raises(MutableTestDatabaseError, match="different database"):
        resolve_mutable_test_database_url(primary_database_url=PRIMARY)


def test_resolve_same_endpoint_different_credentials_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("STOCKBALLDB_TEST_DATABASE_URL", TEST_SAME_CREDS_DIFF)
    with pytest.raises(MutableTestDatabaseError, match="different database"):
        resolve_mutable_test_database_url(primary_database_url=PRIMARY)


def test_require_mutable_test_settings_skips_when_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("STOCKBALLDB_TEST_DATABASE_URL", raising=False)
    monkeypatch.setenv("DATABASE_URL", PRIMARY)
    with pytest.raises(pytest.skip.Exception, match="is required"):
        require_mutable_test_settings()


def test_require_mutable_test_settings_fails_when_same_db(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", PRIMARY)
    monkeypatch.setenv("STOCKBALLDB_TEST_DATABASE_URL", TEST_SAME_CREDS_DIFF)
    with pytest.raises(pytest.fail.Exception, match="different database"):
        require_mutable_test_settings()


def test_require_mutable_test_settings_uses_test_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", PRIMARY)
    monkeypatch.setenv("STOCKBALLDB_TEST_DATABASE_URL", TEST_DISTINCT)
    monkeypatch.setenv("TIINGO_API_KEY", "t")
    settings = require_mutable_test_settings()
    assert settings.database_url == TEST_DISTINCT
    assert settings.database_url != PRIMARY
