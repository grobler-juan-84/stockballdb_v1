"""Transport-agnostic result types for stockballdb.app."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class InstrumentInfo:
    """One market instrument from the current V1 universe."""

    symbol: str
    asset_type: str
    close_only: bool


@dataclass(frozen=True)
class DataDomainInfo:
    """One inspectable canonical data domain (Explorer table)."""

    key: str
    display_name: str
    date_column: str
    symbol_column: str | None
    sortable_columns: tuple[str, ...]
    boolean_filter_columns: tuple[str, ...]
    supports_event_type_filter: bool


@dataclass(frozen=True)
class FieldInfo:
    """One field available on a data domain."""

    name: str
    sortable: bool
    boolean_filterable: bool
    definition: str | None = None


@dataclass(frozen=True)
class ApplicationStatus:
    """Compact read-safe application status summary."""

    available: bool
    database_connected: bool
    health_status: str | None
    validate_v1_pass: bool | None
    alembic_head: str | None
    expected_alembic_head: str | None
    calendar_version: str | None
    finding_counts: dict[str, int] = field(default_factory=dict)
    error_message: str | None = None


@dataclass(frozen=True)
class ValidateResult:
    """Result of an explicit validate_v1 run through the façade."""

    passed: bool
    diagnostics: tuple[str, ...] = ()
    error_message: str | None = None


@dataclass(frozen=True)
class FingerprintResult:
    """Database fingerprint summary (no SQLAlchemy objects)."""

    database_fingerprint: str
    fingerprint_schema_version: str
    table_fingerprints: tuple[dict[str, Any], ...] = ()
