"""Data Explorer service wrappers."""

from __future__ import annotations

from sqlalchemy.engine import Connection

from stockballdb.explorer.config import CSV_EXPORT_MAX_ROWS
from stockballdb.explorer.queries import (
    PageRequest,
    PageResult,
    TableFilters,
    export_query,
    query_table_page,
)
from stockballdb.explorer.registry import list_table_keys


def list_tables() -> list[str]:
    return list_table_keys()


def browse_table(
    conn: Connection,
    table_key: str,
    filters: TableFilters,
    page: PageRequest,
) -> PageResult:
    return query_table_page(conn, table_key, filters, page)


def export_table_csv_rows(
    conn: Connection,
    table_key: str,
    filters: TableFilters,
    sort_column: str | None,
    sort_direction: str,
) -> list[dict]:
    return export_query(
        conn,
        table_key,
        filters,
        sort_column,
        sort_direction,
        max_rows=CSV_EXPORT_MAX_ROWS,
    )
