"""Provenance Explorer service."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from stockballdb.explorer.artifacts import ArtifactRecord, discover_manifests, discover_run_reports, load_manifest
from stockballdb.health.provenance import classify_manifest, scan_secrets
from stockballdb.snapshots.store import SnapshotStore


def list_manifests() -> list[ArtifactRecord]:
    return discover_manifests()


def list_run_reports() -> list[ArtifactRecord]:
    return discover_run_reports()


def manifest_detail(path: Path) -> dict[str, Any]:
    payload = load_manifest(path)
    hits = scan_secrets(payload)
    if hits:
        raise ValueError(f"manifest contains secret-like keys: {hits}")
    payload["_classification"] = classify_manifest(payload)
    return payload


def snapshot_metadata_list(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for entry in manifest.get("snapshots") or []:
        if not isinstance(entry, dict):
            continue
        safe = {k: v for k, v in entry.items() if k != "request_identity"}
        ri = entry.get("request_identity") or {}
        if isinstance(ri, dict):
            safe["request_identity"] = {
                k: v
                for k, v in ri.items()
                if "authorization" not in k.lower() and "api" not in k.lower()
            }
        hits = scan_secrets(safe)
        if hits:
            continue
        out.append(safe)
    return out


def resolve_snapshot_path(relative: str) -> Path:
    store = SnapshotStore()
    if ".." in relative.replace("\\", "/"):
        raise ValueError("invalid snapshot path")
    return store.resolve_payload_path(relative)
