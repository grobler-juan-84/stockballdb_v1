"""Pydantic response DTOs for the HTTP edge (not used inside stockballdb.app)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from stockballdb.app.results import (
    ApplicationStatus,
    DataDomainInfo,
    FieldInfo,
    InstrumentInfo,
)


class InstrumentOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: str
    asset_type: str
    close_only: bool

    @classmethod
    def from_app(cls, item: InstrumentInfo) -> InstrumentOut:
        return cls(
            symbol=item.symbol,
            asset_type=item.asset_type,
            close_only=item.close_only,
        )


class DataDomainOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str
    display_name: str
    date_column: str
    symbol_column: str | None
    sortable_columns: list[str]
    boolean_filter_columns: list[str]
    supports_event_type_filter: bool

    @classmethod
    def from_app(cls, item: DataDomainInfo) -> DataDomainOut:
        return cls(
            key=item.key,
            display_name=item.display_name,
            date_column=item.date_column,
            symbol_column=item.symbol_column,
            sortable_columns=list(item.sortable_columns),
            boolean_filter_columns=list(item.boolean_filter_columns),
            supports_event_type_filter=item.supports_event_type_filter,
        )


class FieldOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    sortable: bool
    boolean_filterable: bool
    definition: str | None = None

    @classmethod
    def from_app(cls, item: FieldInfo) -> FieldOut:
        return cls(
            name=item.name,
            sortable=item.sortable,
            boolean_filterable=item.boolean_filterable,
            definition=item.definition,
        )


class ApplicationStatusOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    available: bool
    database_connected: bool
    health_status: str | None
    validate_v1_pass: bool | None
    alembic_head: str | None
    expected_alembic_head: str | None
    calendar_version: str | None
    finding_counts: dict[str, int] = Field(default_factory=dict)
    error_message: str | None = None

    @classmethod
    def from_app(cls, item: ApplicationStatus) -> ApplicationStatusOut:
        return cls(
            available=item.available,
            database_connected=item.database_connected,
            health_status=item.health_status,
            validate_v1_pass=item.validate_v1_pass,
            alembic_head=item.alembic_head,
            expected_alembic_head=item.expected_alembic_head,
            calendar_version=item.calendar_version,
            finding_counts=dict(item.finding_counts),
            error_message=item.error_message,
        )


class ReadyOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ready: bool = True
    service: str = "stockballdb-api"


class ErrorBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    error: ErrorBody
