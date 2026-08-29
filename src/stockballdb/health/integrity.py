"""Structural integrity via validate_v1 and supplemental SQL checks."""

from __future__ import annotations

from stockballdb.health.models import Finding, Severity
from stockballdb.validate_v1 import ValidateV1Error, validate_v1_database


def run_integrity(engine) -> tuple[bool, list[str], list[Finding]]:
    """Run validate_v1; return pass flag, diagnostics, findings."""
    findings: list[Finding] = []
    try:
        diagnostics = validate_v1_database(engine)
        findings.append(
            Finding(
                severity=Severity.PASS,
                code="VALIDATE_V1_PASS",
                dataset="whole_db",
                message="validate_v1 passed",
                details={"diagnostics_count": len(diagnostics)},
            )
        )
        return True, diagnostics, findings
    except ValidateV1Error as exc:
        findings.append(
            Finding(
                severity=Severity.FATAL,
                code="VALIDATE_V1_FAIL",
                dataset="whole_db",
                message=str(exc),
                details={},
            )
        )
        return False, [], findings
