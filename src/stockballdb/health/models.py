"""Health report data models."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Severity(str, Enum):
    PASS = "PASS"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    FATAL = "FATAL"


class HealthStatus(str, Enum):
    HEALTHY = "HEALTHY"
    HEALTHY_WITH_WARNINGS = "HEALTHY WITH WARNINGS"
    UNHEALTHY = "UNHEALTHY"


class FreshnessClass(str, Enum):
    CURRENT = "CURRENT"
    EXPECTED_LAG = "EXPECTED_LAG"
    STALE = "STALE"
    UNKNOWN = "UNKNOWN"


class MissingnessClass(str, Enum):
    PRE_SERIES = "PRE_SERIES"
    PRE_INCEPTION = "PRE_INCEPTION"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    NOT_YET_PUBLISHED = "NOT_YET_PUBLISHED"
    EXPECTED_PROVIDER_GAP = "EXPECTED_PROVIDER_GAP"
    EXPECTED_LAG = "EXPECTED_LAG"
    UNEXPECTED_GAP = "UNEXPECTED_GAP"
    UNRESOLVED_SOURCE = "UNRESOLVED_SOURCE"


@dataclass(frozen=True)
class Finding:
    severity: Severity
    code: str
    dataset: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class TableCoverage:
    table: str
    grain: str
    row_count: int
    first_date: dt.date | None
    last_date: dt.date | None


@dataclass
class SymbolCoverage:
    symbol: str
    asset_type: str
    first_date: dt.date
    last_date: dt.date
    row_count: int
    eligible_sessions: int
    coverage_pct: float
    internal_missing_sessions: int
    max_consecutive_missing: int
    sample_missing_dates: list[str]


@dataclass
class FreshnessResult:
    dataset: str
    latest_observation: str | None
    freshness_anchor: str | None
    lag_sessions: int | None
    classification: FreshnessClass
    severity: Severity
    missingness: MissingnessClass | None = None


@dataclass
class HealthReport:
    status: HealthStatus
    generated_at: dt.datetime
    runtime_ms: float
    database_connected: bool
    alembic_head: str | None
    expected_alembic_head: str
    calendar_version: str
    validate_v1_pass: bool
    tables: list[TableCoverage] = field(default_factory=list)
    symbols: list[SymbolCoverage] = field(default_factory=list)
    freshness: list[FreshnessResult] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    provenance: dict[str, Any] = field(default_factory=dict)
    integrity: dict[str, Any] = field(default_factory=dict)
    coverage_summary: dict[str, Any] = field(default_factory=dict)

    def finding_counts(self) -> dict[str, int]:
        counts = {s.value: 0 for s in Severity if s != Severity.PASS}
        for f in self.findings:
            if f.severity != Severity.PASS:
                counts[f.severity.value] = counts.get(f.severity.value, 0) + 1
        return counts

    @staticmethod
    def aggregate_status(findings: list[Finding]) -> HealthStatus:
        severities = {f.severity for f in findings if f.severity != Severity.PASS}
        if severities & {Severity.ERROR, Severity.FATAL}:
            return HealthStatus.UNHEALTHY
        if Severity.WARNING in severities:
            return HealthStatus.HEALTHY_WITH_WARNINGS
        return HealthStatus.HEALTHY

    def exit_code(self, *, strict: bool = False) -> int:
        if self.status == HealthStatus.UNHEALTHY:
            return 1
        if strict and self.status == HealthStatus.HEALTHY_WITH_WARNINGS:
            return 1
        return 0
