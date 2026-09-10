"""Control Center page — compact desktop dashboard (Phase 11D)."""

from __future__ import annotations

import streamlit as st

from stockballdb.explorer.db import get_explorer_engine
from stockballdb.explorer.formatting import format_hash
from stockballdb.explorer.services.control import (
    load_control_artifacts,
    load_fingerprint,
    load_live_database_status,
    manifest_summary,
    run_report_view,
)
from stockballdb.explorer.ui.components import dataframe_dense, metric_row, page_header, section_heading, status_badge


@st.cache_data(show_spinner="Computing fingerprint…")
def _cached_fingerprint(_nonce: int, compute: bool):
    if not compute:
        return None
    return load_fingerprint(get_explorer_engine())


def _run_card(title: str, record) -> None:
    st.markdown(f"**{title}**")
    if not record or not record.payload:
        st.caption("None found.")
        return
    view = run_report_view(record.payload)
    st.markdown(
        f"{status_badge('info', view.status or '—')} "
        f"`{view.run_id or '—'}` · as-of {view.run_as_of or '—'}",
        unsafe_allow_html=True,
    )
    bits = []
    if view.validation_result:
        bits.append(f"validation {view.validation_result}")
    if view.health_status:
        bits.append(f"health {view.health_status}")
    if view.change_classification:
        bits.append(str(view.change_classification))
    if view.failure_stage or view.failure_reason:
        bits.append(f"failure: {view.failure_stage or '—'} — {view.failure_reason or '—'}")
    if bits:
        st.caption(" · ".join(bits))


def render() -> None:
    page_header("Control Center", "Live database status and latest operational provenance.")
    nonce = st.session_state.get("refresh_nonce", 0)

    live = load_live_database_status()
    if live.error_message:
        st.error(f"Live health check error: {live.error_message}")

    try:
        artifacts = load_control_artifacts()
    except Exception as exc:
        st.error(f"Unable to load Control Center artifacts: {exc}")
        return

    health_kind = "ok"
    hl = (live.health_label or "").upper()
    if "WARN" in hl:
        health_kind = "warn"
    elif hl in {"UNHEALTHY", "ERROR"}:
        health_kind = "bad"

    v_kind = "ok" if live.validate_v1_label == "PASS" else "bad"
    alembic_label = f"Alembic {live.alembic_head or '—'}"

    st.markdown(
        f"{status_badge(health_kind, f'Health {live.health_label}')} "
        f"{status_badge(v_kind, f'validate_v1 {live.validate_v1_label}')} "
        f"{status_badge('muted', alembic_label)}",
        unsafe_allow_html=True,
    )

    metric_row(
        [
            ("Health", live.health_label),
            ("validate_v1", live.validate_v1_label),
            ("Alembic", live.alembic_head or "—"),
            ("Git", format_hash(str(artifacts.git.get("commit") or ""), prefix_len=10)),
        ]
    )
    st.caption(f"Git dirty: {artifacts.git.get('dirty')} — live checks only (not inferred from run reports).")

    left, right = st.columns(2)
    with left:
        section_heading("Latest successful run")
        _run_card("", artifacts.latest_successful_run)
    with right:
        section_heading("Latest attempt")
        _run_card("", artifacts.latest_run_attempt)

    fp_col, man_col = st.columns([1.2, 1.8])
    with fp_col:
        section_heading("Fingerprint")
        if st.button("Compute database fingerprint", use_container_width=True):
            st.session_state["compute_fp"] = True
        if st.session_state.get("compute_fp"):
            try:
                fp = _cached_fingerprint(nonce, True)
                if fp:
                    st.code(fp.database_fingerprint)
            except Exception as exc:
                st.error(f"Fingerprint failed: {exc}")
    with man_col:
        section_heading("Latest Manifest 1.1")
        summary = manifest_summary(artifacts.latest_manifest)
        if summary:
            st.json(summary, expanded=False)
        else:
            st.caption("No manifests found.")

    section_heading("Table coverage")
    if live.health_report:
        table_rows = [
            {
                "table": t.table,
                "rows": t.row_count,
                "first": str(t.first_date),
                "last": str(t.last_date),
                "grain": t.grain,
            }
            for t in live.health_report.tables
        ]
        dataframe_dense(table_rows, height=280)
    else:
        st.info("Table summary unavailable — live health check did not complete.")

    if live.health_report:
        with st.expander("Health details (raw)"):
            from stockballdb.health.render import report_to_dict

            st.json(report_to_dict(live.health_report))
