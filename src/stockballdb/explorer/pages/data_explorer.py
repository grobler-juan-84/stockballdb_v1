"""Data Explorer page."""

from __future__ import annotations

import csv
import io
import datetime as dt

import streamlit as st

from stockballdb.explorer.config import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from stockballdb.explorer.db import readonly_connection
from stockballdb.explorer.definitions import definition_for
from stockballdb.explorer.formatting import rows_to_display_dicts
from stockballdb.explorer.queries import PageRequest, TableFilters
from stockballdb.explorer.registry import TABLE_REGISTRY, allowed_event_types
from stockballdb.explorer.services import tables as table_service
from stockballdb.market_data.universe import V1_MARKET_SYMBOLS


def render() -> None:
    table_key = st.selectbox(
        "Table",
        options=list(TABLE_REGISTRY.keys()),
        format_func=lambda k: TABLE_REGISTRY[k].display_name,
    )
    spec = TABLE_REGISTRY[table_key]

    col1, col2, col3 = st.columns(3)
    use_from = col1.checkbox("Filter from date")
    date_from = col1.date_input("From date", value=dt.date(1957, 1, 2), disabled=not use_from)
    use_to = col2.checkbox("Filter to date")
    date_to = col2.date_input("To date", value=dt.date(2026, 8, 28), disabled=not use_to)
    symbol = None
    if spec.symbol_column:
        symbol = col3.selectbox("Symbol", options=["(all)"] + list(V1_MARKET_SYMBOLS))
        if symbol == "(all)":
            symbol = None

    event_type = None
    if spec.event_type_filter:
        event_type = st.selectbox("Event type", options=["(all)"] + list(allowed_event_types()))
        if event_type == "(all)":
            event_type = None

    boolean_flags = {}
    if spec.boolean_filter_columns:
        with st.expander("Boolean filters"):
            for col_name in sorted(spec.boolean_filter_columns):
                choice = st.selectbox(col_name, ["(any)", "true", "false"], key=f"bf_{col_name}")
                if choice == "true":
                    boolean_flags[col_name] = True
                elif choice == "false":
                    boolean_flags[col_name] = False

    sort_col = st.selectbox("Sort by", options=sorted(spec.sortable_columns))
    sort_dir = st.selectbox("Direction", options=["asc", "desc"])
    page_size = st.number_input("Page size", min_value=1, max_value=MAX_PAGE_SIZE, value=DEFAULT_PAGE_SIZE)
    page_num = st.number_input("Page", min_value=1, value=1)

    filters = TableFilters(
        date_from=date_from if use_from else None,
        date_to=date_to if use_to else None,
        symbol=symbol,
        event_type=event_type,
        boolean_flags=boolean_flags or None,
    )
    req = PageRequest(page=int(page_num), page_size=int(page_size), sort_column=sort_col, sort_direction=sort_dir)

    if st.button("Run query", type="primary"):
        st.session_state["de_result"] = (table_key, filters, req)

    if "de_result" not in st.session_state:
        return

    tk, flt, pg = st.session_state["de_result"]
    try:
        with readonly_connection() as conn:
            result = table_service.browse_table(conn, tk, flt, pg)
    except Exception as exc:
        st.error(f"Query failed: {exc}")
        return

    total_pages = max(1, (result.total_count + result.page_size - 1) // result.page_size)
    st.caption(
        f"Table **{result.table_key}** | {result.total_count:,} matching rows | "
        f"page {result.page}/{total_pages} | sort {result.sort_column} {result.sort_direction}"
    )

    display_rows = rows_to_display_dicts(result.rows)
    if display_rows:
        st.dataframe(display_rows, use_container_width=True)
    else:
        st.info("No rows match filters.")

    with st.expander("Column definitions"):
        for col in display_rows[0].keys() if display_rows else []:
            d = definition_for(col)
            if d:
                st.write(f"**{col}** — {d}")

    if st.button("Export filtered CSV (bounded)"):
        try:
            with readonly_connection() as conn:
                export_rows = table_service.export_table_csv_rows(
                    conn, tk, flt, pg.sort_column, pg.sort_direction
                )
            buf = io.StringIO()
            if export_rows:
                writer = csv.DictWriter(buf, fieldnames=list(export_rows[0].keys()))
                writer.writeheader()
                for row in export_rows:
                    writer.writerow({k: "" if v is None else v for k, v in row.items()})
            st.download_button(
                "Download CSV",
                data=buf.getvalue(),
                file_name=f"{tk}_export.csv",
                mime="text/csv",
            )
        except Exception as exc:
            st.error(f"Export failed: {exc}")
