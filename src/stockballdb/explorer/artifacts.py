"""Safe discovery and loading of build_reports artifacts."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from stockballdb.health.provenance import reports_dir, scan_secrets


@dataclass(frozen=True)
class ArtifactRecord:
    path: Path
    kind: str
    artifact_id: str
    started_at: str | None
    payload: dict[str, Any] | None
    error: str | None = None


def _sort_key(rec: ArtifactRecord) -> tuple[str, str]:
    ts = rec.started_at or rec.artifact_id
    return (ts, rec.artifact_id)


def _load_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, str(exc)
    if not isinstance(data, dict):
        return None, "artifact root is not a JSON object"
    hits = scan_secrets(data)
    if hits:
        return None, f"artifact contains secret-like keys: {hits}"
    return data, None


def discover_manifests(root: Path | None = None) -> list[ArtifactRecord]:
    base = root or reports_dir()
    if not base.exists():
        return []
    records: list[ArtifactRecord] = []
    for path in sorted(base.glob("manifest_*.json"), reverse=True):
        data, err = _load_json(path)
        build_id = path.stem.replace("manifest_", "", 1)
        started = None
        if data:
            started = data.get("build_started_at") or data.get("started_at")
            build_id = str(data.get("build_id", build_id))
        records.append(
            ArtifactRecord(
                path=path,
                kind="manifest",
                artifact_id=build_id,
                started_at=str(started) if started else None,
                payload=data,
                error=err,
            )
        )
    records.sort(key=_sort_key, reverse=True)
    return records


def discover_run_reports(root: Path | None = None) -> list[ArtifactRecord]:
    base = root or reports_dir()
    if not base.exists():
        return []
    records: list[ArtifactRecord] = []
    for path in sorted(base.glob("run_*.json"), reverse=True):
        data, err = _load_json(path)
        run_id = path.stem.replace("run_", "", 1)
        started = None
        if data:
            started = data.get("started_at")
            run_id = str(data.get("run_id", run_id))
        records.append(
            ArtifactRecord(
                path=path,
                kind="run_report",
                artifact_id=run_id,
                started_at=str(started) if started else None,
                payload=data,
                error=err,
            )
        )
    records.sort(key=_sort_key, reverse=True)
    return records


def load_manifest(path: Path) -> dict[str, Any]:
    data, err = _load_json(path)
    if err or data is None:
        raise ValueError(err or "manifest unreadable")
    return data
