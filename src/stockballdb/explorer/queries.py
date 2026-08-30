"""Parameterized read-only SELECT queries for Explorer."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Any

from sqlalchemy import Select, asc, desc, func, select
from sqlalchemy.engine import Connection, Row

from stockballdb.explorer.config import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from stockballdb.explorer.registry import ExplorerQueryError, TableSpec, get_table_spec


@dataclass(frozen=True)
class TableFilters:
    date_from: dt.date | None = None
    date_to: dt.date | None = None
    symbol: str | None = None
    event_type: str | None = None
    boolean_flags: dict[str, bool] | None = None


@dataclass(frozen=True)
class PageRequest:
    page: int = 1
    page_size: int = DEFAULT_PAGE_SIZE
    sort_column: str | None = None
    sort_direction: str = "asc"


@dataclass
class PageResult:
    rows: list[dict[str, Any]]
    total_count: int
    page: int
    page_size: int
    sort_column: str
    sort_direction: str
    table_key: str
    filters: TableFilters


def _clamp_page_size(page_size: int) -> int:
    if page_size < 1:
        raise ExplorerQueryError("page_size must be >= 1")
    return min(page_size, MAX_PAGE_SIZE)


def _resolve_sort(
    spec: TableSpec, sort_column: str | None, sort_direction: str
) -> tuple[str, str]:
    direction = sort_direction.lower()
    if direction not in {"asc", "desc"}:
        raise ExplorerQueryError(f"invalid sort direction: {sort_direction!r}")
    if sort_column is None:
        col, dir_ = spec.default_sort[0]
        return col, dir_
    if sort_column not in spec.sortable_columns:
        raise ExplorerQueryError(f"sort column not allowed: {sort_column!r}")
    return sort_column, direction


def _apply_filters(stmt: Select[Any], spec: TableSpec, filters: TableFilters) -> Select[Any]:
    model = spec.model
    date_col = getattr(model, spec.date_column)
    if filters.date_from is not None:
        stmt = stmt.where(date_col >= filters.date_from)
    if filters.date_to is not None:
        stmt = stmt.where(date_col <= filters.date_to)
    if filters.symbol and spec.symbol_column:
        stmt = stmt.where(getattr(model, spec.symbol_column) == filters.symbol)
    if filters.event_type and spec.event_type_filter:
        stmt = stmt.where(model.event_type == filters.event_type)
    if filters.boolean_flags and spec.boolean_filter_columns:
        for col_name, value in filters.boolean_flags.items():
            if col_name not in spec.boolean_filter_columns:
                raise ExplorerQueryError(f"boolean filter not allowed: {col_name!r}")
            stmt = stmt.where(getattr(model, col_name).is_(value))
    return stmt


def _order_by(stmt: Select[Any], spec: TableSpec, sort_col: str, sort_dir: str) -> Select[Any]:
    model = spec.model
    col = getattr(model, sort_col)
    order_fn = asc if sort_dir == "asc" else desc
    stmt = stmt.order_by(order_fn(col))
    if sort_col != spec.date_column and hasattr(model, spec.date_column):
        if sort_col != "symbol" and spec.symbol_column:
            stmt = stmt.order_by(asc(getattr(model, spec.date_column)))
    if spec.symbol_column and sort_col != spec.symbol_column:
        if sort_col != spec.date_column:
            pass
    if spec.symbol_column and sort_col == spec.date_column and spec.symbol_column:
        stmt = stmt.order_by(asc(getattr(model, spec.symbol_column)))
    return stmt


def _row_to_dict(row: Row[Any]) -> dict[str, Any]:
    mapping = row._mapping
    return dict(mapping)


def query_table_page(
    conn: Connection,
    table_key: str,
    filters: TableFilters | None = None,
    page: PageRequest | None = None,
) -> PageResult:
    spec = get_table_spec(table_key)
    flt = filters or TableFilters()
    req = page or PageRequest()
    page_size = _clamp_page_size(req.page_size)
    page_num = max(1, req.page)
    sort_col, sort_dir = _resolve_sort(spec, req.sort_column, req.sort_direction)

    base = select(spec.model)
    filtered = _apply_filters(base, spec, flt)
    count_stmt = select(func.count()).select_from(filtered.subquery())
    total = int(conn.execute(count_stmt).scalar_one())

    ordered = _order_by(filtered, spec, sort_col, sort_dir)
    offset = (page_num - 1) * page_size
    rows = conn.execute(ordered.limit(page_size).offset(offset)).all()
    return PageResult(
        rows=[_row_to_dict(r) for r in rows],
        total_count=total,
        page=page_num,
        page_size=page_size,
        sort_column=sort_col,
        sort_direction=sort_dir,
        table_key=table_key,
        filters=flt,
    )


def fetch_row_by_date(
    conn: Connection, table_key: str, target_date: dt.date, symbol: str | None = None
) -> dict[str, Any] | None:
    spec = get_table_spec(table_key)
    stmt = select(spec.model).where(getattr(spec.model, spec.date_column) == target_date)
    if symbol and spec.symbol_column:
        stmt = stmt.where(getattr(spec.model, spec.symbol_column) == symbol)
    row = conn.execute(stmt).first()
    return _row_to_dict(row) if row else None


def fetch_rows_for_date(
    conn: Connection,
    table_key: str,
    target_date: dt.date,
    symbol: str | None = None,
    *,
    limit: int = MAX_PAGE_SIZE,
) -> list[dict[str, Any]]:
    spec = get_table_spec(table_key)
    stmt = select(spec.model).where(getattr(spec.model, spec.date_column) == target_date)
    if symbol and spec.symbol_column:
        stmt = stmt.where(getattr(spec.model, spec.symbol_column) == symbol)
    if spec.symbol_column:
        stmt = stmt.order_by(asc(getattr(spec.model, spec.symbol_column)))
    rows = conn.execute(stmt.limit(limit)).all()
    return [_row_to_dict(r) for r in rows]


def fetch_scheduled_events_for_date(
    conn: Connection, event_date: dt.date, *, limit: int = MAX_PAGE_SIZE
) -> list[dict[str, Any]]:
    stmt = (
        select(get_table_spec("scheduled_events").model)
        .where(get_table_spec("scheduled_events").model.event_date == event_date)
        .order_by(asc(get_table_spec("scheduled_events").model.event_id))
    )
    rows = conn.execute(stmt.limit(limit)).all()
    return [_row_to_dict(r) for r in rows]


def fetch_trading_day(conn: Connection, target_date: dt.date) -> dict[str, Any] | None:
    return fetch_row_by_date(conn, "trading_days", target_date)


def nearest_trading_sessions(
    conn: Connection, calendar_date: dt.date
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """Return (previous_trading_day_row, next_trading_day_row) relative to calendar_date."""
    model = get_table_spec("trading_days").model
    prev_row = conn.execute(
        select(model).where(model.date < calendar_date).order_by(desc(model.date)).limit(1)
    ).first()
    next_row = conn.execute(
        select(model).where(model.date > calendar_date).order_by(asc(model.date)).limit(1)
    ).first()
    return (
        _row_to_dict(prev_row) if prev_row else None,
        _row_to_dict(next_row) if next_row else None,
    )


def export_query(
    conn: Connection,
    table_key: str,
    filters: TableFilters | None = None,
    sort_column: str | None = None,
    sort_direction: str = "asc",
    *,
    max_rows: int = 10_000,
) -> list[dict[str, Any]]:
    spec = get_table_spec(table_key)
    flt = filters or TableFilters()
    sort_col, sort_dir = _resolve_sort(spec, sort_column, sort_direction)
    stmt = _order_by(_apply_filters(select(spec.model), spec, flt), spec, sort_col, sort_dir)
    rows = conn.execute(stmt.limit(max_rows)).all()
    return [_row_to_dict(r) for r in rows]
