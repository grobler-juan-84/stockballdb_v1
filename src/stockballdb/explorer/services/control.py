"""Control Center data assembly."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.engine import Engine

from stockballdb.explorer.artifacts import ArtifactRecord, discover_manifests, discover_run_reports
from stockballdb.fingerprint.compute import DatabaseFingerprint, compute_database_fingerprint
from stockballdb.health.engine import run_health
from stockballdb.health.models import HealthReport
from stockballdb.health.provenance import classify_manifest, git_provenance
from stockballdb.health.render import report_to_dict
from stockballdb.v1.stages import collect_diagnostics


@dataclass
class ControlCenterSnapshot:
    health: HealthReport
    health_dict: dict[str, Any]
    diagnostics: dict[str, Any]
    git: dict[str, Any]
    latest_manifest: ArtifactRecord | None
    latest_run: ArtifactRecord | None
    fingerprint: DatabaseFingerprint | None = None


def load_control_center(engine: Engine) -> ControlCenterSnapshot:
    health = run_health(engine)
    manifests = discover_manifests()
    runs = discover_run_reports()
    latest_manifest = next((m for m in manifests if m.payload and m.error is None), None)
    latest_run = next((r for r in runs if r.payload and r.error is None), None)
    return ControlCenterSnapshot(
        health=health,
        health_dict=report_to_dict(health),
        diagnostics=collect_diagnostics(engine),
        git=git_provenance(),
        latest_manifest=latest_manifest,
        latest_run=latest_run,
    )


def load_fingerprint(engine: Engine) -> DatabaseFingerprint:
    return compute_database_fingerprint(engine)


def manifest_summary(record: ArtifactRecord | None) -> dict[str, Any]:
    if not record or not record.payload:
        return {}
    payload = record.payload
    classification = classify_manifest(payload)
    return {
        "build_id": payload.get("build_id"),
        "schema_version": payload.get("schema_version"),
        "validation_result": payload.get("validation_result"),
        "health_status": payload.get("health_status"),
        "exact_rebuild_capable": classification.get("exact_rebuild_capable"),
        "snapshot_count": len(payload.get("snapshots") or []),
        "database_fingerprint": (payload.get("database_fingerprint") or {}).get(
            "database_fingerprint"
        ),
        "path": str(record.path),
    }
