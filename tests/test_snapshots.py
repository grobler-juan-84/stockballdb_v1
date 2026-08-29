"""Tests for immutable snapshot store, fingerprints, and exact rebuild."""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from stockballdb.events.fomc import parse_calendars_html, parse_historical_html
from stockballdb.fingerprint.compute import compute_database_fingerprint
from stockballdb.fingerprint.serialize import format_value
from stockballdb.health.provenance import (
    MANIFEST_SCHEMA_1_0,
    MANIFEST_SCHEMA_1_1,
    build_manifest_payload,
    classify_manifest,
    scan_secrets,
)
from stockballdb.macro.pit import parse_alfred_rows
from stockballdb.providers.fred import parse_observations_bytes
from stockballdb.providers.tiingo import parse_daily_prices_bytes
from stockballdb.rebuild_exact import RebuildExactError, validate_manifest_for_exact_rebuild
from stockballdb.snapshots.context import (
    NetworkForbiddenError,
    acquire_bytes,
    live_build_context,
    reset_context,
    snapshot_references,
    snapshot_replay_context,
)
from stockballdb.snapshots.models import snapshot_id_from_digest
from stockballdb.snapshots.pagination import concat_pages, split_pages
from stockballdb.snapshots.sanitize import sanitize_request_identity
from stockballdb.snapshots.store import SnapshotCorruptionError, SnapshotStore
from stockballdb.snapshots.verify import verify_manifest


from stockballdb.providers.tiingo_constants import TIINGO_PRICE_FIELDS


FIXTURES = Path(__file__).parent / "fixtures" / "snapshots"


def _read(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def test_snapshot_hash_deterministic(tmp_path: Path) -> None:
    store = SnapshotStore(tmp_path)
    raw = b'[{"date":"2024-01-02","close":1}]'
    ref1 = store.store_snapshot(
        raw,
        provider="tiingo",
        source_identifier="SPY",
        source_type="api_json",
        request_identity={"provider": "tiingo", "symbol": "SPY"},
        retrieved_at=dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc),
        content_type="application/json",
    )
    ref2 = store.store_snapshot(
        raw,
        provider="tiingo",
        source_identifier="SPY",
        source_type="api_json",
        request_identity={"provider": "tiingo", "symbol": "SPY"},
        retrieved_at=dt.datetime(2026, 1, 2, tzinfo=dt.timezone.utc),
        content_type="application/json",
    )
    assert ref1.snapshot_id == ref2.snapshot_id
    assert len(list(tmp_path.rglob("*.gz"))) == 1


def test_different_bytes_different_id(tmp_path: Path) -> None:
    store = SnapshotStore(tmp_path)
    when = dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc)
    id_a = store.store_snapshot(
        b"aaa",
        provider="fred",
        source_identifier="DFF",
        source_type="api_json",
        request_identity={"series_id": "DFF"},
        retrieved_at=when,
    ).snapshot_id
    id_b = store.store_snapshot(
        b"bbb",
        provider="fred",
        source_identifier="DFF",
        source_type="api_json",
        request_identity={"series_id": "DFF"},
        retrieved_at=when,
    ).snapshot_id
    assert id_a != id_b


def test_corruption_detected(tmp_path: Path) -> None:
    store = SnapshotStore(tmp_path)
    raw = b"payload-bytes"
    ref = store.store_snapshot(
        raw,
        provider="fred",
        source_identifier="DFF",
        source_type="api_json",
        request_identity={"series_id": "DFF"},
        retrieved_at=dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc),
    )
    path = tmp_path / "sha256" / ref.sha256[:2] / f"{ref.sha256}.gz"
    path.write_bytes(b"corrupt")
    with pytest.raises(SnapshotCorruptionError):
        store.load_snapshot(ref.snapshot_id)


def test_sanitize_rejects_secrets() -> None:
    clean = sanitize_request_identity({"api_key": "secret-value", "series_id": "DFF"})
    assert "api_key" not in clean
    assert clean["series_id"] == "DFF"
    with pytest.raises(ValueError):
        sanitize_request_identity({"note": "postgresql+psycopg://user:pass@host/db"})


def test_full_concat_v1_roundtrip() -> None:
    pages = [(0, b'{"observations":[{"date":"2020-01-01","value":"1"}]}'), (100000, b'{"observations":[]}')]
    merged = concat_pages(pages)
    assert split_pages(merged) == pages


def test_tiingo_replay_matches_fixture() -> None:
    raw = _read("tiingo_spy_sample.json")
    bars = parse_daily_prices_bytes(raw, symbol="SPY")
    assert len(bars) == 2
    assert TIINGO_PRICE_FIELDS.issubset(bars[0].keys())
    assert bars[0]["extra_provider_field"] == "preserved"


def test_fred_replay_fixture() -> None:
    raw = _read("fred_dff_concat.bin")
    rows = parse_observations_bytes(raw)
    assert len(rows) >= 1
    assert "date" in rows[0]


def test_alfred_pit_replay_fixture() -> None:
    raw = _read("alfred_cpiaucsl_concat.bin")
    rows = parse_observations_bytes(raw)
    vintages = parse_alfred_rows(rows)
    assert vintages
    from stockballdb.macro.pit import first_print_events

    parsed_events = first_print_events(vintages)
    assert len(parsed_events) >= 1
    assert parsed_events[0][1] == dt.date(2020, 1, 1)


def test_fomc_html_replay_fixture() -> None:
    html = _read("fomc_historical_sample.html").decode("utf-8")
    days = parse_historical_html(html)
    assert dt.date(2019, 1, 30) in days


def test_manifest_1_0_not_exact_rebuild_capable() -> None:
    manifest = {"schema_version": MANIFEST_SCHEMA_1_0}
    flags = classify_manifest(manifest)
    assert flags["provenance_capable"]
    assert not flags["exact_rebuild_capable"]
    with pytest.raises(RebuildExactError):
        validate_manifest_for_exact_rebuild(manifest)


def test_manifest_1_1_secret_scan() -> None:
    payload = build_manifest_payload(
        command="test",
        started_at=dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc),
        finished_at=dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc),
        success=True,
        datasets=[],
        validation_result="PASS",
        alembic_head="abc",
        schema_version=MANIFEST_SCHEMA_1_1,
        snapshots=[],
    )
    assert payload["schema_version"] == MANIFEST_SCHEMA_1_1
    assert scan_secrets({"password": "x"}) == ["password"]


def test_acquire_bytes_live_then_replay(tmp_path: Path) -> None:
    reset_context()
    raw = _read("tiingo_spy_sample.json")

    def fetch_live():
        return raw, {"http_status": 200}

    with live_build_context(store=SnapshotStore(tmp_path)):
        out = acquire_bytes(
            provider="tiingo",
            source_identifier="SPY",
            source_type="api_json",
            request_identity={"provider": "tiingo", "symbol": "SPY", "endpoint": "daily_prices", "start_date": "1957-01-01", "end_date": None},
            content_type="application/json",
            fetch_live=fetch_live,
        )
        assert out == raw
        refs = snapshot_references()
        assert len(refs) == 1

    manifest_snaps = [refs[0].manifest_entry()]
    with snapshot_replay_context(manifest_snaps, store=SnapshotStore(tmp_path)):
        out2 = acquire_bytes(
            provider="tiingo",
            source_identifier="SPY",
            source_type="api_json",
            request_identity={"provider": "tiingo", "symbol": "SPY", "endpoint": "daily_prices", "start_date": "1957-01-01", "end_date": None},
            content_type="application/json",
            fetch_live=lambda: (_ for _ in ()).throw(AssertionError("network")),
        )
        assert out2 == raw
    reset_context()


def test_network_forbidden_in_snapshot_mode(tmp_path: Path) -> None:
    reset_context()
    with snapshot_replay_context([], store=SnapshotStore(tmp_path)):
        with pytest.raises(NetworkForbiddenError):
            __import__("stockballdb.providers.tiingo", fromlist=["fetch_daily_prices_bytes"]).fetch_daily_prices_bytes(
                "SPY", "fake-key"
            )
    reset_context()


def test_decimal_format_stable() -> None:
    from decimal import Decimal

    assert format_value(Decimal("1.2300")) == "1.23"
    assert format_value(Decimal("0")) == "0"


def test_verify_manifest(tmp_path: Path) -> None:
    store = SnapshotStore(tmp_path)
    raw = b"verify-me"
    ref = store.store_snapshot(
        raw,
        provider="fred",
        source_identifier="DFF",
        source_type="api_json",
        request_identity={"series_id": "DFF"},
        retrieved_at=dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc),
    )
    manifest = {
        "schema_version": MANIFEST_SCHEMA_1_1,
        "snapshots": [ref.manifest_entry()],
    }
    report = verify_manifest(manifest, store)
    assert report.ok


def test_fingerprint_deterministic_same_data() -> None:
    import os

    if not os.getenv("DATABASE_URL"):
        pytest.skip("DATABASE_URL not set")
    from stockballdb.db import get_engine, reset_engine

    reset_engine()
    engine = get_engine()
    fp1 = compute_database_fingerprint(engine)
    fp2 = compute_database_fingerprint(engine)
    assert fp1.database_fingerprint == fp2.database_fingerprint


def test_zero_network_exact_rebuild_guard() -> None:
    """Patch network helpers to ensure snapshot mode blocks them."""
    reset_context()
    with patch("stockballdb.snapshots.context._network_guard_enabled", True):
        with pytest.raises(NetworkForbiddenError):
            from stockballdb.providers.fred import _get_bytes

            _get_bytes("series/observations", "key")
    reset_context()
