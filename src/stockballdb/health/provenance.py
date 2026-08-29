"""Build manifest and git provenance helpers."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import platform
import re
import subprocess
import sys
import uuid
from importlib.metadata import version as pkg_version
from pathlib import Path
from typing import Any

import pandas_market_calendars as mcal

from stockballdb.fingerprint.compute import DatabaseFingerprint
from stockballdb.health.limitations import EXPECTED_LIMITATIONS, macro_series_ids
from stockballdb.health.models import HealthReport
from stockballdb.snapshots.models import SnapshotReference
from stockballdb.v1.preflight import REQUIRED_CALENDAR_VERSION, V1_ALEMBIC_HEAD

MANIFEST_SCHEMA_1_0 = "1.0"
MANIFEST_SCHEMA_1_1 = "1.1"

# Tiingo 14 + FRED 5 + ALFRED 4 (build_v1 macro/events; CPI/UNRATE dedupe)
MIN_SNAPSHOTS_BUILD_V1 = 23

SECRET_PATTERNS = (
    re.compile(r"api[_-]?key", re.I),
    re.compile(r"password", re.I),
    re.compile(r"secret", re.I),
    re.compile(r"authorization", re.I),
    re.compile(r"postgresql\+psycopg://[^@]+@", re.I),
)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def reports_dir() -> Path:
    return repo_root() / "build_reports"


def git_provenance() -> dict[str, Any]:
    root = repo_root()
    out: dict[str, Any] = {"available": False}
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
        dirty = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
        tag = subprocess.run(
            ["git", "describe", "--tags", "--exact-match"],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
        out = {
            "available": True,
            "commit": commit.stdout.strip(),
            "dirty": bool(dirty.stdout.strip()),
            "tag": tag.stdout.strip() if tag.returncode == 0 else None,
        }
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        pass
    return out


def scan_secrets(obj: Any) -> list[str]:
    """Return key paths that look like secrets."""
    hits: list[str] = []

    def walk(value: Any, path: str) -> None:
        if isinstance(value, dict):
            for k, v in value.items():
                p = f"{path}.{k}" if path else k
                if any(pat.search(k) for pat in SECRET_PATTERNS):
                    hits.append(p)
                walk(v, p)
        elif isinstance(value, list):
            for i, v in enumerate(value):
                walk(v, f"{path}[{i}]")

    walk(obj, "")
    return hits


def dependency_fingerprint() -> dict[str, Any]:
    """Best-effort environment fingerprint (no lockfile required)."""
    try:
        stockballdb_version = pkg_version("stockballdb")
    except Exception:
        stockballdb_version = "unknown"
    packages = {
        "stockballdb": stockballdb_version,
        "pandas_market_calendars": mcal.__version__,
        "python": platform.python_version(),
    }
    for name in ("pandas", "SQLAlchemy", "requests", "alembic", "psycopg"):
        try:
            packages[name] = pkg_version(name)
        except Exception:
            packages[name] = "unknown"
    pyproject = repo_root() / "pyproject.toml"
    digest = None
    if pyproject.exists():
        digest = hashlib.sha256(pyproject.read_bytes()).hexdigest()[:16]
    return {
        "packages": packages,
        "pyproject_sha256_prefix": digest,
        "python_executable": sys.executable,
    }


def environment_provenance() -> dict[str, Any]:
    return {
        "python_version": platform.python_version(),
        "stockballdb_version": dependency_fingerprint()["packages"].get("stockballdb"),
        "dependency_fingerprint": dependency_fingerprint(),
    }


def snapshots_manifest_entries(
    refs: list[SnapshotReference],
) -> list[dict[str, Any]]:
    return [r.manifest_entry() for r in refs]


def classify_manifest(manifest: dict[str, Any]) -> dict[str, bool]:
    schema = manifest.get("schema_version", MANIFEST_SCHEMA_1_0)
    snapshots = manifest.get("snapshots") or []
    if schema == MANIFEST_SCHEMA_1_0:
        return {
            "provenance_capable": True,
            "exact_rebuild_capable": False,
            "snapshot_capture": False,
        }
    capture = bool(manifest.get("snapshot_capture")) and len(snapshots) > 0
    exact = bool(manifest.get("exact_rebuild_capable")) and capture
    return {
        "provenance_capable": True,
        "exact_rebuild_capable": exact,
        "snapshot_capture": capture,
    }


def build_manifest_payload(
    *,
    command: str,
    started_at: dt.datetime,
    finished_at: dt.datetime,
    success: bool,
    datasets: list[dict[str, Any]],
    validation_result: str,
    alembic_head: str | None,
    health_status: str | None = None,
    stages: list[dict[str, str]] | None = None,
    retrieved_at: dt.datetime | None = None,
    snapshots: list[SnapshotReference] | None = None,
    database_fingerprint: DatabaseFingerprint | None = None,
    schema_version: str = MANIFEST_SCHEMA_1_0,
) -> dict[str, Any]:
    build_id = started_at.strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex[:8]
    snap_entries = snapshots_manifest_entries(snapshots or [])
    snapshot_capture = success and len(snap_entries) >= MIN_SNAPSHOTS_BUILD_V1
    exact_rebuild_capable = snapshot_capture and validation_result == "PASS"
    payload: dict[str, Any] = {
        "schema_version": schema_version,
        "build_id": build_id,
        "command": command,
        "pipeline": command,
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
        "retrieved_at": (retrieved_at or finished_at).isoformat(),
        "build_started_at": started_at.isoformat(),
        "build_finished_at": finished_at.isoformat(),
        "success": success,
        "validation_result": validation_result,
        "health_status": health_status,
        "alembic_head": alembic_head,
        "expected_alembic_head": V1_ALEMBIC_HEAD,
        "calendar_pin": {
            "package": "pandas_market_calendars",
            "version": mcal.__version__,
            "required": REQUIRED_CALENDAR_VERSION,
        },
        "git": git_provenance(),
        "environment": environment_provenance(),
        "datasets": datasets,
        "providers": _default_providers(),
        "stages": stages or [],
        "limitations": list(EXPECTED_LIMITATIONS),
        "deterministic_sources": [
            {
                "source": "us_statutory_election_day",
                "provenance": "code + 2 U.S.C. §7",
            },
            {
                "source": "nyse_trading_calendar",
                "provenance": "pandas_market_calendars pin + code",
            },
        ],
    }
    if schema_version == MANIFEST_SCHEMA_1_1:
        payload["snapshot_capture"] = snapshot_capture
        payload["exact_rebuild_capable"] = exact_rebuild_capable
        payload["snapshots"] = snap_entries
        payload["reproducibility_mode"] = (
            "snapshot_capable" if exact_rebuild_capable else "provenance_only"
        )
        payload["reproducibility_note"] = (
            "Exact rebuild requires manifest snapshots + pinned Git/Alembic."
        )
        if database_fingerprint is not None:
            payload["fingerprint_schema_version"] = (
                database_fingerprint.fingerprint_schema_version
            )
            payload["database_fingerprint"] = (
                database_fingerprint.database_fingerprint
            )
            payload["table_fingerprints"] = [
                t.as_dict() for t in database_fingerprint.table_fingerprints
            ]
    else:
        payload["reproducibility_note"] = (
            "Structural rebuild from live providers; exact snapshot reproducibility is Phase 9."
        )
    return payload


def _default_providers() -> list[dict[str, str]]:
    providers = [
        {"provider": "Tiingo", "identifier": "daily EOD", "dataset": "etf_market_data"},
        {"provider": "FRED", "identifier": "DCOILWTICO", "dataset": "wti"},
        {"provider": "Federal Reserve", "identifier": "FOMC pages", "dataset": "scheduled_events.fomc"},
        {"provider": "ALFRED", "identifier": "CPIAUCSL/UNRATE vintages", "dataset": "scheduled_events"},
        {"provider": "NYSE via pandas_market_calendars", "identifier": "NYSE 5.4.0", "dataset": "trading_days"},
    ]
    for field, sid in macro_series_ids().items():
        providers.append(
            {
                "provider": "FRED/ALFRED",
                "identifier": sid,
                "dataset": f"macro.{field}",
            }
        )
    return providers


def write_build_manifest(payload: dict[str, Any]) -> Path | None:
    secret_hits = scan_secrets(payload)
    if secret_hits:
        raise ValueError(f"manifest contains secret-like keys: {secret_hits}")
    out_dir = reports_dir()
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        return None
    path = out_dir / f"manifest_{payload['build_id']}.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def manifest_from_health_report(
    report: HealthReport,
    *,
    command: str,
    started_at: dt.datetime,
    finished_at: dt.datetime,
    success: bool,
    stages: list[dict[str, str]] | None = None,
    snapshots: list[SnapshotReference] | None = None,
    database_fingerprint: DatabaseFingerprint | None = None,
    schema_version: str = MANIFEST_SCHEMA_1_1,
) -> dict[str, Any]:
    datasets = []
    for t in report.tables:
        datasets.append(
            {
                "dataset": t.table,
                "row_count": t.row_count,
                "first_date": t.first_date.isoformat() if t.first_date else None,
                "last_date": t.last_date.isoformat() if t.last_date else None,
            }
        )
    return build_manifest_payload(
        command=command,
        started_at=started_at,
        finished_at=finished_at,
        success=success,
        datasets=datasets,
        validation_result="PASS" if report.validate_v1_pass else "FAIL",
        alembic_head=report.alembic_head,
        health_status=report.status.value,
        stages=stages,
        retrieved_at=finished_at,
        snapshots=snapshots,
        database_fingerprint=database_fingerprint,
        schema_version=schema_version,
    )
