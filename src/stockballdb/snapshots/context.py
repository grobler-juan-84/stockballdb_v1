"""Build-time snapshot acquisition context."""

from __future__ import annotations

import contextlib
import datetime as dt
from collections.abc import Callable, Generator
from typing import Any

from stockballdb.snapshots.models import (
    BuildSnapshotCollector,
    SnapshotReference,
    SourceMode,
    request_identity_key,
)
from stockballdb.snapshots.store import SnapshotError, SnapshotStore


class OfflineSourceError(SnapshotError):
    """Raised when LIVE provider access is attempted in SNAPSHOT mode."""


class NetworkForbiddenError(OfflineSourceError):
    """Raised when a provider network call is attempted during offline rebuild."""


_collector: BuildSnapshotCollector | None = None
_store: SnapshotStore | None = None
_network_guard_enabled: bool = False
_build_context_active: bool = False


def get_collector() -> BuildSnapshotCollector | None:
    return _collector


def get_store() -> SnapshotStore:
    global _store
    if _store is None:
        _store = SnapshotStore()
    return _store


def is_snapshot_mode() -> bool:
    return _collector is not None and _collector.mode == SourceMode.SNAPSHOT


def enable_network_guard() -> None:
    global _network_guard_enabled
    _network_guard_enabled = True


def disable_network_guard() -> None:
    global _network_guard_enabled
    _network_guard_enabled = False


def assert_network_allowed(provider: str) -> None:
    if _network_guard_enabled or is_snapshot_mode():
        raise NetworkForbiddenError(
            f"provider network access forbidden ({provider}) in snapshot/offline mode"
        )


def reset_context() -> None:
    global _collector, _store, _network_guard_enabled, _build_context_active
    _collector = None
    _store = None
    _network_guard_enabled = False
    _build_context_active = False


@contextlib.contextmanager
def live_build_context(
    *,
    store: SnapshotStore | None = None,
    retrieved_at: dt.datetime | None = None,
) -> Generator[BuildSnapshotCollector, None, None]:
    global _collector, _store, _build_context_active
    _store = store or SnapshotStore()
    _collector = BuildSnapshotCollector(mode=SourceMode.LIVE)
    _build_context_active = True
    try:
        yield _collector
    finally:
        _build_context_active = False


@contextlib.contextmanager
def snapshot_replay_context(
    manifest_snapshots: list[dict[str, Any]],
    *,
    store: SnapshotStore | None = None,
) -> Generator[BuildSnapshotCollector, None, None]:
    global _collector, _store, _network_guard_enabled
    _store = store or SnapshotStore()
    _collector = BuildSnapshotCollector.from_manifest(manifest_snapshots)
    enable_network_guard()
    try:
        yield _collector
    finally:
        disable_network_guard()


def snapshot_references() -> list[SnapshotReference]:
    if _collector is None:
        return []
    return list(_collector.references)


def acquire_bytes(
    *,
    provider: str,
    source_identifier: str,
    source_type: str,
    request_identity: dict[str, Any],
    content_type: str,
    encoding: str = "utf-8",
    fetch_live: Callable[[], tuple[bytes, dict[str, Any]]],
    retrieved_at: dt.datetime | None = None,
) -> bytes:
    """
    Outside build context: direct live fetch (no snapshot persistence).
    LIVE build context: fetch → store → load from store boundary.
    SNAPSHOT context: resolve manifest reference → load from store.
    """
    collector = _collector
    store = get_store()

    if collector is None:
        assert_network_allowed(provider)
        raw_bytes, _http_meta = fetch_live()
        return raw_bytes

    if collector.mode == SourceMode.SNAPSHOT:
        key = request_identity_key(request_identity)
        ref = collector._lookup.get(key)
        if ref is None:
            raise SnapshotError(
                f"missing snapshot for {provider}/{source_identifier}"
            )
        return store.load_snapshot(ref.snapshot_id)

    assert_network_allowed(provider)
    raw_bytes, http_meta = fetch_live()
    when = retrieved_at or dt.datetime.now(dt.timezone.utc)
    ref = store.store_snapshot(
        raw_bytes,
        provider=provider,
        source_identifier=source_identifier,
        source_type=source_type,
        request_identity=request_identity,
        retrieved_at=when,
        content_type=content_type,
        encoding=encoding,
        http_status=http_meta.get("http_status"),
        etag=http_meta.get("etag"),
        last_modified=http_meta.get("last_modified"),
    )
    collector.register(ref)
    return store.load_snapshot(ref.snapshot_id)
