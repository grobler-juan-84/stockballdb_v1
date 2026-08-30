"""Operational run report models and persistence."""

from __future__ import annotations

import datetime as dt
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from stockballdb.health.provenance import reports_dir, scan_secrets

RUN_REPORT_SCHEMA_VERSION = "1.0"


@dataclass
class StageRecord:
    name: str
    status: str
    started_at: str
    finished_at: str
    duration_ms: float
    detail: str = ""
    error: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_ms": self.duration_ms,
            "detail": self.detail,
            "error": self.error,
        }


@dataclass
class RunReport:
    run_id: str
    command: str
    run_as_of: str
    started_at: dt.datetime
    finished_at: dt.datetime | None = None
    status: str = "RUNNING"
    failure_kind: str | None = None
    failure_stage: str | None = None
    error: str | None = None
    git: dict[str, Any] = field(default_factory=dict)
    alembic_head: str | None = None
    fingerprint_before: str | None = None
    fingerprint_after: str | None = None
    change_classification: str | None = None
    validation_result: str | None = None
    health_status: str | None = None
    snapshot_count: int = 0
    manifest_path: str | None = None
    stages: list[StageRecord] = field(default_factory=list)

    @property
    def duration_ms(self) -> float | None:
        if self.finished_at is None:
            return None
        return (self.finished_at - self.started_at).total_seconds() * 1000

    def as_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema_version": RUN_REPORT_SCHEMA_VERSION,
            "run_id": self.run_id,
            "command": self.command,
            "run_as_of": self.run_as_of,
            "started_at": self.started_at.isoformat(),
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "failure_kind": self.failure_kind,
            "failure_stage": self.failure_stage,
            "error": self.error,
            "git": self.git,
            "alembic_head": self.alembic_head,
            "fingerprint_before": self.fingerprint_before,
            "fingerprint_after": self.fingerprint_after,
            "change_classification": self.change_classification,
            "validation_result": self.validation_result,
            "health_status": self.health_status,
            "snapshot_count": self.snapshot_count,
            "manifest_path": self.manifest_path,
            "stages": [s.as_dict() for s in self.stages],
        }
        hits = scan_secrets(payload)
        if hits:
            raise ValueError(f"run report contains secret-like keys: {hits}")
        return payload

    def write(self) -> Path | None:
        out_dir = reports_dir()
        try:
            out_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            return None
        path = out_dir / f"run_{self.run_id}.json"
        path.write_text(
            json.dumps(self.as_dict(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return path


def new_run_id(started_at: dt.datetime | None = None) -> str:
    when = started_at or dt.datetime.now(dt.timezone.utc)
    import uuid

    return when.strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex[:8]
