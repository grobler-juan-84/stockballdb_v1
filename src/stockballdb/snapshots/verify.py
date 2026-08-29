"""Snapshot verification utilities."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from stockballdb.snapshots.models import digest_from_snapshot_id
from stockballdb.snapshots.sanitize import scan_object_for_secrets
from stockballdb.snapshots.store import SnapshotCorruptionError, SnapshotError, SnapshotStore


@dataclass
class VerifyReport:
    checked: int = 0
    unique_payloads: int = 0
    missing: int = 0
    corrupt: int = 0
    invalid_metadata: int = 0
    total_compressed_bytes: int = 0
    total_uncompressed_bytes: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.missing == 0 and self.corrupt == 0 and self.invalid_metadata == 0

    def exit_code(self) -> int:
        return 0 if self.ok else 1


def load_manifest(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def verify_snapshot_entry(
    store: SnapshotStore,
    entry: dict[str, Any],
    report: VerifyReport,
) -> None:
    report.checked += 1
    sid = entry.get("snapshot_id")
    if not sid:
        report.invalid_metadata += 1
        report.errors.append("snapshot entry missing snapshot_id")
        return
    try:
        digest_from_snapshot_id(sid)
    except ValueError as exc:
        report.invalid_metadata += 1
        report.errors.append(str(exc))
        return
    if scan_object_for_secrets(entry):
        report.invalid_metadata += 1
        report.errors.append(f"secret-like keys in manifest entry {sid}")
        return
    try:
        sidecar = store.load_sidecar(sid)
    except SnapshotError:
        report.missing += 1
        report.errors.append(f"missing sidecar for {sid}")
        return
    if scan_object_for_secrets(sidecar):
        report.invalid_metadata += 1
        report.errors.append(f"secret-like keys in sidecar {sid}")
        return
    payload_path = store.resolve_payload_path(sidecar["payload_path"])
    if not payload_path.exists():
        report.missing += 1
        report.errors.append(f"missing payload for {sid}")
        return
    report.total_compressed_bytes += payload_path.stat().st_size
    try:
        raw = store.load_snapshot(sid)
    except SnapshotCorruptionError as exc:
        report.corrupt += 1
        report.errors.append(str(exc))
        return
    except SnapshotError as exc:
        report.missing += 1
        report.errors.append(str(exc))
        return
    report.total_uncompressed_bytes += len(raw)
    if sidecar.get("sha256", sidecar.get("digest")) != digest_from_snapshot_id(sid):
        report.invalid_metadata += 1
        report.errors.append(f"sidecar sha256 mismatch for {sid}")


def verify_manifest(manifest: dict[str, Any], store: SnapshotStore | None = None) -> VerifyReport:
    store = store or SnapshotStore()
    report = VerifyReport()
    snapshots = manifest.get("snapshots") or []
    seen_ids: set[str] = set()
    for entry in snapshots:
        sid = entry.get("snapshot_id")
        if sid:
            seen_ids.add(sid)
        verify_snapshot_entry(store, entry, report)
    report.unique_payloads = len(seen_ids)
    return report


def verify_all_referenced(store: SnapshotStore | None = None) -> VerifyReport:
    """Verify snapshots referenced by all manifests in build_reports/."""
    from stockballdb.health.provenance import reports_dir

    store = store or SnapshotStore()
    combined = VerifyReport()
    manifest_dir = reports_dir()
    if not manifest_dir.exists():
        return combined
    seen_global: set[str] = set()
    for path in sorted(manifest_dir.glob("manifest_*.json")):
        manifest = load_manifest(path)
        sub = verify_manifest(manifest, store)
        combined.checked += sub.checked
        combined.missing += sub.missing
        combined.corrupt += sub.corrupt
        combined.invalid_metadata += sub.invalid_metadata
        combined.total_compressed_bytes += sub.total_compressed_bytes
        combined.total_uncompressed_bytes += sub.total_uncompressed_bytes
        combined.errors.extend(sub.errors)
        for entry in manifest.get("snapshots") or []:
            sid = entry.get("snapshot_id")
            if sid:
                seen_global.add(sid)
    combined.unique_payloads = len(seen_global)
    return combined
