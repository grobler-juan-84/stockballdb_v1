"""Coverage Explorer page."""

from __future__ import annotations

import streamlit as st

from stockballdb.explorer.db import readonly_connection
from stockballdb.explorer.services.coverage import load_coverage


def render() -> None:
    st.caption("Coverage and missingness from Phase 8 health logic.")
    try:
        with readonly_connection() as conn:
            snap = load_coverage(conn)
    except Exception as exc:
        st.error(f"Coverage load failed: {exc}")
        return

    st.subheader("Table coverage")
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
    st.dataframe(table_rows, use_container_width=True)

    st.subheader("Symbol coverage")
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
    st.dataframe(sym_rows, use_container_width=True)
    if sym_rows:
        chart_data = {r["symbol"]: r["coverage_pct"] for r in sym_rows}
        st.bar_chart(chart_data)

    st.subheader("Freshness")
    for f in snap.freshness:
        st.write(
            f"**{f.dataset}** — {f.classification.value} | lag={f.lag_sessions} | {f.severity.value}"
        )

    st.subheader("Gap findings")
    for g in snap.gap_findings:
        st.write(f"[{g.severity.value}] {g.code} — {g.message}")

    st.subheader("Known limitations")
    for item in snap.limitations:
        st.write(f"- {item}")
    st.write("Unresolved symbols:", ", ".join(snap.unresolved_symbols))
    st.write("Unresolved macro:", ", ".join(snap.unresolved_macro))
