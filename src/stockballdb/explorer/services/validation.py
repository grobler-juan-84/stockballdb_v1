"""Validation Center service wrappers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy.engine import Engine

from stockballdb.fingerprint.compute import DatabaseFingerprint, compute_database_fingerprint
from stockballdb.health.engine import run_health
from stockballdb.health.models import HealthReport
from stockballdb.health.render import report_to_dict
from stockballdb.snapshots.verify import VerifyReport, load_manifest, verify_manifest
from stockballdb.validate_v1 import ValidateV1Error, validate_v1_database


@dataclass
class ValidateV1Result:
    passed: bool
    diagnostics: list[str]
    error: str | None = None


def run_validate_v1(engine: Engine) -> ValidateV1Result:
    try:
        lines = validate_v1_database(engine)
        return ValidateV1Result(passed=True, diagnostics=lines)
    except ValidateV1Error as exc:
        return ValidateV1Result(passed=False, diagnostics=[], error=str(exc))


def run_health_check(engine: Engine) -> HealthReport:
    return run_health(engine)


def health_as_dict(report: HealthReport) -> dict[str, Any]:
    return report_to_dict(report)


def run_fingerprint(engine: Engine) -> DatabaseFingerprint:
    return compute_database_fingerprint(engine)


def verify_manifest_file(path: Path) -> VerifyReport:
    return verify_manifest(load_manifest(path))
