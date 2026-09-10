"""Coverage Explorer page — desktop multi-panel layout (Phase 11D)."""

from __future__ import annotations

import streamlit as st

from stockballdb.explorer.db import readonly_connection
from stockballdb.explorer.services.coverage import load_coverage
from stockballdb.explorer.ui.components import dataframe_dense, page_header, section_heading


def render() -> None:
    page_header("Coverage", "Coverage and missingness from Phase 8 health logic.", icon="▥")
    try:
        with readonly_connection() as conn:
            snap = load_coverage(conn)
    except Exception as exc:
        st.error(f"Coverage load failed: {exc}")
        return

    left, right = st.columns(2)
    with left:
        section_heading("Table coverage")
        table_rows = [
            {
                "table": t.table,
                "rows": t.row_count,
                "first": str(t.first_date),
                "last": str(t.last_date),
                "grain": t.grain,
            }
            for t in snap.tables
        ]
        dataframe_dense(table_rows, height=320)
    with right:
        section_heading("Symbol coverage")
        sym_rows = [
            {
                "symbol": s.symbol,
                "type": s.asset_type,
                "coverage_pct": s.coverage_pct,
                "rows": s.row_count,
                "first": str(s.first_date),
                "last": str(s.last_date),
                "missing": s.internal_missing_sessions,
                "max_gap": s.max_consecutive_missing,
            }
            for s in snap.symbols
        ]
        dataframe_dense(sym_rows, height=320)

    if snap.symbols:
        chart_data = {s.symbol: s.coverage_pct for s in snap.symbols}
        with st.expander("Coverage chart", expanded=False):
            st.bar_chart(chart_data)

    f_col, g_col = st.columns(2)
    with f_col:
        section_heading("Freshness")
        fresh_rows = [
            {
                "dataset": f.dataset,
                "classification": f.classification.value,
                "lag_sessions": f.lag_sessions,
                "severity": f.severity.value,
            }
            for f in snap.freshness
        ]
        if fresh_rows:
            dataframe_dense(fresh_rows, height=220)
        else:
            st.caption("No freshness results.")
    with g_col:
        section_heading("Gap findings")
        gap_rows = [
            {
                "severity": g.severity.value,
                "code": g.code,
                "message": g.message,
            }
            for g in snap.gap_findings
        ]
        if gap_rows:
            dataframe_dense(gap_rows, height=220)
        else:
            st.caption("No gap findings.")

    section_heading("Known limitations")
    st.markdown("\n".join(f"- {item}" for item in snap.limitations))
    st.caption(
        f"Unresolved symbols: {', '.join(snap.unresolved_symbols) or '—'} · "
        f"Unresolved macro: {', '.join(snap.unresolved_macro) or '—'}"
    )
