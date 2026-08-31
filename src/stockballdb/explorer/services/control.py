"""Control Center data assembly."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from stockballdb.explorer.artifacts import ArtifactRecord, discover_manifests, discover_run_reports
from stockballdb.fingerprint.compute import DatabaseFingerprint, compute_database_fingerprint
from stockballdb.health.engine import run_health
from stockballdb.health.models import HealthReport, HealthStatus
from stockballdb.health.provenance import classify_manifest, git_provenance
from stockballdb.health.render import report_to_dict
from stockballdb.v1.stages import collect_diagnostics

SUCCESS_RUN_STATUSES = frozenset({"SUCCESS_NO_CHANGE", "SUCCESS_UPDATED"})


@dataclass(frozen=True)
class DatabaseStatus:
    """Current database status from live health check only."""

    health_status: HealthStatus
    validate_v1_pass: bool
    alembic_head: str | None

    @property
    def health_label(self) -> str:
        return self.health_status.value

    @property
    def validate_v1_label(self) -> str:
        return "PASS" if self.validate_v1_pass else "FAIL"


@dataclass(frozen=True)
class RunReportView:
    run_id: str | None
    status: str | None
    run_as_of: str | None
    failure_stage: str | None
    failure_reason: str | None
    validation_result: str | None
    health_status: str | None
    change_classification: str | None


@dataclass
class ControlCenterSnapshot:
    health: HealthReport
    database_status: DatabaseStatus
    health_dict: dict[str, Any]
    diagnostics: dict[str, Any]
    git: dict[str, Any]
    latest_manifest: ArtifactRecord | None
    latest_run_attempt: ArtifactRecord | None
    latest_successful_run: ArtifactRecord | None
    fingerprint: DatabaseFingerprint | None = None


def database_status_from_health(report: HealthReport) -> DatabaseStatus:
    """Derive headline status only from authoritative HealthReport fields."""
    return DatabaseStatus(
        health_status=report.status,
        validate_v1_pass=report.validate_v1_pass,
        alembic_head=report.alembic_head,
    )


def load_current_health() -> HealthReport:
    """Run the same health check as ``python -m stockballdb.health``."""
    return run_health()


def select_operational_runs(
    runs: list[ArtifactRecord],
) -> tuple[ArtifactRecord | None, ArtifactRecord | None]:
    """Return (newest run report, newest successful run report)."""
    valid = [r for r in runs if r.payload and r.error is None]
    latest_attempt = valid[0] if valid else None
    latest_success = next(
        (
            r
            for r in valid
            if isinstance(r.payload, dict)
            and r.payload.get("status") in SUCCESS_RUN_STATUSES
        ),
        None,
    )
    return latest_attempt, latest_success


def run_report_view(payload: dict[str, Any]) -> RunReportView:
    failure_reason = payload.get("error")
    failure_stage = payload.get("failure_stage")
    if not failure_reason and failure_stage:
        failure_reason = str(failure_stage)
    return RunReportView(
        run_id=payload.get("run_id"),
        status=payload.get("status"),
        run_as_of=payload.get("run_as_of"),
        failure_stage=failure_stage,
        failure_reason=failure_reason,
        validation_result=payload.get("validation_result"),
        health_status=payload.get("health_status"),
        change_classification=payload.get("change_classification"),
    )


def _coerce_database_fingerprint(payload: dict[str, Any]) -> str | None:
    raw = payload.get("database_fingerprint")
    if isinstance(raw, str):
        return raw
    if isinstance(raw, dict):
        inner = raw.get("database_fingerprint")
        return inner if isinstance(inner, str) else None
    return None


def _snapshot_count(payload: dict[str, Any]) -> int:
    snapshots = payload.get("snapshots")
    if isinstance(snapshots, list):
        return len(snapshots)
    return 0


def _table_fingerprint_count(payload: dict[str, Any]) -> int:
    tables = payload.get("table_fingerprints")
    if isinstance(tables, list):
        return len(tables)
    return 0


def load_control_center() -> ControlCenterSnapshot:
    health = load_current_health()
    manifests = discover_manifests()
    runs = discover_run_reports()
    latest_manifest = next((m for m in manifests if m.payload and m.error is None), None)
    latest_attempt, latest_success = select_operational_runs(runs)
    from stockballdb.db import get_engine

    return ControlCenterSnapshot(
        health=health,
        database_status=database_status_from_health(health),
        health_dict=report_to_dict(health),
        diagnostics=collect_diagnostics(get_engine()),
        git=git_provenance(),
        latest_manifest=latest_manifest,
        latest_run_attempt=latest_attempt,
        latest_successful_run=latest_success,
    )


def load_fingerprint(engine) -> DatabaseFingerprint:
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
        "snapshot_count": _snapshot_count(payload),
        "table_fingerprint_count": _table_fingerprint_count(payload),
        "database_fingerprint": _coerce_database_fingerprint(payload),
        "path": str(record.path),
    }
