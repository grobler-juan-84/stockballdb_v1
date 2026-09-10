"""Data Explorer page — desktop-dense layout (Phase 11D)."""

from __future__ import annotations

import csv
import io
import datetime as dt
import math

import streamlit as st

from stockballdb.explorer.config import (
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    explorer_date_input_bounds,
    explorer_date_max,
)
from stockballdb.explorer.db import readonly_connection
from stockballdb.explorer.definitions import definition_for
from stockballdb.explorer.queries import PageRequest, TableFilters
from stockballdb.explorer.registry import TABLE_REGISTRY, allowed_event_types
from stockballdb.explorer.services import tables as table_service
from stockballdb.explorer.ui.components import dataframe_dense, page_header, result_banner, section_heading
from stockballdb.explorer.ui.dataframes import rows_to_styled_dataframe
from stockballdb.market_data.universe import V1_MARKET_SYMBOLS


def render() -> None:
    page_header("Data Explorer", "Browse canonical tables — read-only.")

    bounds = explorer_date_input_bounds()
    default_from = dt.date(1957, 1, 2)
    default_to = explorer_date_max()

    # Compact primary toolbar
    c_table, c_sym, c_from, c_to, c_sort, c_dir, c_rows, c_run = st.columns(
        [1.6, 1.0, 1.35, 1.35, 1.0, 0.75, 0.7, 0.85]
    )

    table_key = c_table.selectbox(
        "Table",
        options=list(TABLE_REGISTRY.keys()),
        format_func=lambda k: TABLE_REGISTRY[k].display_name,
        key="de_table",
    )
    spec = TABLE_REGISTRY[table_key]

    symbol = None
    if spec.symbol_column:
        sym_choice = c_sym.selectbox(
            "Symbol",
            options=["(all)"] + list(V1_MARKET_SYMBOLS),
            key="de_symbol",
        )
        symbol = None if sym_choice == "(all)" else sym_choice
    else:
        c_sym.caption("Symbol")
        c_sym.write("—")

    use_from = c_from.checkbox("From", value=False, key="de_use_from")
    date_from = c_from.date_input(
        "From date",
        value=default_from,
        disabled=not use_from,
        label_visibility="collapsed",
        key="de_from",
        **bounds,
    )
    use_to = c_to.checkbox("To", value=False, key="de_use_to")
    date_to = c_to.date_input(
        "To date",
        value=default_to,
        disabled=not use_to,
        label_visibility="collapsed",
        key="de_to",
        **bounds,
    )

    sort_col = c_sort.selectbox(
        "Sort by",
        options=sorted(spec.sortable_columns),
        key=f"de_sort_{table_key}",
    )
    sort_dir = c_dir.selectbox("Order", options=["desc", "asc"], key="de_dir")
    page_size = int(
        c_rows.number_input(
            "Rows",
            min_value=1,
            max_value=MAX_PAGE_SIZE,
            value=DEFAULT_PAGE_SIZE,
            key="de_page_size",
        )
    )

    run_clicked = c_run.button("Run query", type="primary", use_container_width=True)

    # Second row: table-specific filters
    event_type = None
    boolean_flags: dict[str, bool] = {}
    if spec.event_type_filter or spec.boolean_filter_columns:
        with st.expander("Additional filters", expanded=bool(spec.event_type_filter)):
            if spec.event_type_filter:
                event_type = st.selectbox(
                    "Event type",
                    options=["(all)"] + list(allowed_event_types()),
                    key="de_event_type",
                )
                if event_type == "(all)":
                    event_type = None
            if spec.boolean_filter_columns:
                bf_cols = st.columns(min(4, len(spec.boolean_filter_columns)) or 1)
                for i, col_name in enumerate(sorted(spec.boolean_filter_columns)):
                    choice = bf_cols[i % len(bf_cols)].selectbox(
                        col_name,
                        ["(any)", "true", "false"],
                        key=f"bf_{col_name}",
                    )
                    if choice == "true":
                        boolean_flags[col_name] = True
                    elif choice == "false":
                        boolean_flags[col_name] = False

    page_num = int(st.session_state.get("de_page_num", 1))
    filters = TableFilters(
        date_from=date_from if use_from else None,
        date_to=date_to if use_to else None,
        symbol=symbol,
        event_type=event_type,
        boolean_flags=boolean_flags or None,
    )
    req = PageRequest(
        page=page_num,
        page_size=page_size,
        sort_column=sort_col,
        sort_direction=sort_dir,
    )

    if run_clicked:
        st.session_state["de_page_num"] = 1
        req = PageRequest(page=1, page_size=page_size, sort_column=sort_col, sort_direction=sort_dir)
        st.session_state["de_result"] = (table_key, filters, req)

    if "de_result" not in st.session_state:
        st.info("Configure filters and click **Run query**.")
        _table_info_footer(table_key)
        return

    tk, flt, pg = st.session_state["de_result"]
    # Keep page size / sort from toolbar if user changed them after a prior run and clicks nav
    try:
        with readonly_connection() as conn:
            result = table_service.browse_table(conn, tk, flt, pg)
    except Exception as exc:
        st.error(f"Query failed: {exc}")
        return

    total_pages = max(1, math.ceil(result.total_count / result.page_size) if result.page_size else 1)
    sym_label = flt.symbol or "(all symbols)"
    result_banner(
        [
            f"<strong>{sym_label}</strong>",
            f"<strong>{result.total_count:,}</strong> matching rows",
            f"Page <strong>{result.page}</strong> / {total_pages}",
            f"Showing <strong>{len(result.rows)}</strong> rows",
            f"sort {result.sort_column} {result.sort_direction}",
        ]
    )

    data, col_cfg = rows_to_styled_dataframe(result.rows)
    if result.rows:
        dataframe_dense(data, height=560, column_config=col_cfg)
    else:
        st.info("No rows match filters.")

    # Pagination + export
    p_prev, p_info, p_next, p_export = st.columns([1, 2.5, 1, 1.4])
    if p_prev.button("Previous", disabled=result.page <= 1, use_container_width=True):
        new_page = max(1, result.page - 1)
        st.session_state["de_page_num"] = new_page
        st.session_state["de_result"] = (
            tk,
            flt,
            PageRequest(
                page=new_page,
                page_size=pg.page_size,
                sort_column=pg.sort_column,
                sort_direction=pg.sort_direction,
            ),
        )
        st.rerun()
    p_info.markdown(
        f'<div class="sbdb-muted" style="text-align:center;padding-top:0.45rem;">'
        f"Page {result.page} of {total_pages} · {result.page_size} rows / page</div>",
        unsafe_allow_html=True,
    )
    if p_next.button("Next", disabled=result.page >= total_pages, use_container_width=True):
        new_page = result.page + 1
        st.session_state["de_page_num"] = new_page
        st.session_state["de_result"] = (
            tk,
            flt,
            PageRequest(
                page=new_page,
                page_size=pg.page_size,
                sort_column=pg.sort_column,
                sort_direction=pg.sort_direction,
            ),
        )
        st.rerun()

    if p_export.button("Export CSV", use_container_width=True):
        st.session_state["de_do_export"] = True

    if st.session_state.pop("de_do_export", False):
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

    with st.expander("Column definitions"):
        display_cols = list(result.rows[0].keys()) if result.rows else []
        for col in display_cols:
            d = definition_for(col)
            if d:
                st.write(f"**{col}** — {d}")

    _table_info_footer(tk)


def _table_info_footer(table_key: str) -> None:
    spec = TABLE_REGISTRY.get(table_key)
    if not spec:
        return
    section_heading("Table information")
    st.markdown(
        f'<div class="sbdb-banner">'
        f"<strong>{spec.display_name}</strong> <span class=\"sbdb-muted\">({spec.key})</span>"
        f" &nbsp;·&nbsp; date column: <code>{spec.date_column}</code>"
        f" &nbsp;·&nbsp; symbol column: <code>{spec.symbol_column or '—'}</code>"
        f"</div>",
        unsafe_allow_html=True,
    )
