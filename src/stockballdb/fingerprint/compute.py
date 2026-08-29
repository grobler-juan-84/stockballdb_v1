"""Compute deterministic table and database fingerprints."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

from stockballdb.fingerprint.serialize import FINGERPRINT_SCHEMA_VERSION, serialize_row
from stockballdb.models.asset_regimes import AssetRegime
from stockballdb.models.calendar_context import CalendarContext
from stockballdb.models.daily_market_data import DailyMarketData
from stockballdb.models.macro_conditions import MacroCondition
from stockballdb.models.market_outcomes import MarketOutcome
from stockballdb.models.scheduled_events import ScheduledEvent
from stockballdb.models.trading_days import TradingDay

CANONICAL_TABLES: tuple[type, ...] = (
    AssetRegime,
    CalendarContext,
    DailyMarketData,
    MacroCondition,
    MarketOutcome,
    ScheduledEvent,
    TradingDay,
)


@dataclass(frozen=True)
class TableFingerprint:
    table: str
    row_count: int
    sha256: str
    serialization_version: str = FINGERPRINT_SCHEMA_VERSION

    def as_dict(self) -> dict[str, Any]:
        return {
            "table": self.table,
            "row_count": self.row_count,
            "sha256": self.sha256,
            "serialization_version": self.serialization_version,
        }


@dataclass(frozen=True)
class DatabaseFingerprint:
    fingerprint_schema_version: str
    database_fingerprint: str
    table_fingerprints: tuple[TableFingerprint, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "fingerprint_schema_version": self.fingerprint_schema_version,
            "database_fingerprint": self.database_fingerprint,
            "table_fingerprints": [t.as_dict() for t in self.table_fingerprints],
        }


def _pk_columns(model: type) -> list[str]:
    mapper = inspect(model)
    return [c.key for c in mapper.primary_key]


def _all_columns(model: type) -> list[str]:
    return sorted(c.key for c in inspect(model).columns)


def _order_clause(model: type) -> str:
    pk = _pk_columns(model)
    return ", ".join(pk)


def compute_table_fingerprint(engine: Engine, model: type) -> TableFingerprint:
    table = model.__tablename__
    columns = _all_columns(model)
    order = _order_clause(model)
    col_list = ", ".join(columns)
    query = text(f"SELECT {col_list} FROM {table} ORDER BY {order}")
    hasher = hashlib.sha256()
    row_count = 0
    with engine.connect() as conn:
        result = conn.execute(query)
        for row in result.mappings():
            row_count += 1
            line = serialize_row(columns, dict(row)) + "\n"
            hasher.update(line.encode("utf-8"))
    digest = hasher.hexdigest()
    return TableFingerprint(table=table, row_count=row_count, sha256=f"sha256:{digest}")


def compute_database_fingerprint(engine: Engine) -> DatabaseFingerprint:
    table_fps = tuple(
        compute_table_fingerprint(engine, model) for model in CANONICAL_TABLES
    )
    db_hasher = hashlib.sha256()
    for tf in table_fps:
        line = f"{tf.table}:{tf.sha256}:{tf.row_count}:{tf.serialization_version}\n"
        db_hasher.update(line.encode("utf-8"))
    db_digest = db_hasher.hexdigest()
    return DatabaseFingerprint(
        fingerprint_schema_version=FINGERPRINT_SCHEMA_VERSION,
        database_fingerprint=f"sha256:{db_digest}",
        table_fingerprints=table_fps,
    )
