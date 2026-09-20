"""Status application service — read-safe availability and health summary.

P1 is foundational Status for vertical-slice proof, not the full P8 dashboard.
"""

from __future__ import annotations

from stockballdb.app.connections import ensure_database_available, get_read_engine
from stockballdb.app.errors import AppUnavailableError
from stockballdb.app.results import ApplicationStatus, FingerprintResult, ValidateResult
from stockballdb.config import Settings
from stockballdb.fingerprint.compute import compute_database_fingerprint
from stockballdb.health.engine import run_health
from stockballdb.validate_v1 import ValidateV1Error, validate_v1_database


def get_status(settings: Settings | None = None) -> ApplicationStatus:
    """
    Return a compact application status summary.

    Uses the Explorer read engine when invoking V1 health. If the database is
    unreachable, returns ``available=False`` with an error message rather than
    raising (suitable for readiness/status screens). Unexpected programming
    errors still propagate.
    """
    try:
        ensure_database_available(settings)
    except AppUnavailableError as exc:
        return ApplicationStatus(
            available=False,
            database_connected=False,
            health_status=None,
            validate_v1_pass=None,
            alembic_head=None,
            expected_alembic_head=None,
            calendar_version=None,
            finding_counts={},
            error_message=str(exc),
        )

    engine = get_read_engine(settings)
    report = run_health(engine)
    return ApplicationStatus(
        available=True,
        database_connected=report.database_connected,
        health_status=report.status.value,
        validate_v1_pass=report.validate_v1_pass,
        alembic_head=report.alembic_head,
        expected_alembic_head=report.expected_alembic_head,
        calendar_version=report.calendar_version,
        finding_counts=report.finding_counts(),
        error_message=None,
    )


def run_validate_v1(settings: Settings | None = None) -> ValidateResult:
    """Run ``validate_v1`` through the façade using the read engine."""
    ensure_database_available(settings)
    engine = get_read_engine(settings)
    try:
        lines = validate_v1_database(engine)
        return ValidateResult(passed=True, diagnostics=tuple(lines), error_message=None)
    except ValidateV1Error as exc:
        return ValidateResult(passed=False, diagnostics=(), error_message=str(exc))


def get_fingerprint(settings: Settings | None = None) -> FingerprintResult:
    """Compute the database fingerprint via the façade (read-safe)."""
    ensure_database_available(settings)
    engine = get_read_engine(settings)
    fp = compute_database_fingerprint(engine)
    return FingerprintResult(
        database_fingerprint=fp.database_fingerprint,
        fingerprint_schema_version=fp.fingerprint_schema_version,
        table_fingerprints=tuple(t.as_dict() for t in fp.table_fingerprints),
    )
