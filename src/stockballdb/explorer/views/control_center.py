"""Control Center page."""

from __future__ import annotations

import streamlit as st

from stockballdb.explorer.db import get_explorer_engine
from stockballdb.explorer.services.control import (
    load_control_center,
    load_fingerprint,
    manifest_summary,
    run_report_view,
)


@st.cache_data(show_spinner="Loading status…")
def _cached_control(_nonce: int):
    return load_control_center()


@st.cache_data(show_spinner="Computing fingerprint…")
def _cached_fingerprint(_nonce: int, compute: bool):
    if not compute:
        return None
    return load_fingerprint(get_explorer_engine())


def _render_run_section(title: str, record) -> None:
    st.markdown(f"**{title}**")
    if not record or not record.payload:
        st.info("None found.")
        return
    view = run_report_view(record.payload)
    st.write(f"Status: **{view.status or '—'}**")
    st.write(f"run_id: `{view.run_id or '—'}`")
    st.write(f"as-of: {view.run_as_of or '—'}")
    if view.failure_stage or view.failure_reason:
        st.write(f"failure: {view.failure_stage or '—'} — {view.failure_reason or '—'}")
    if view.validation_result or view.health_status:
        st.write(
            f"validation: {view.validation_result or '—'} | "
            f"health: {view.health_status or '—'}"
        )
    if view.change_classification:
        st.write(f"change: {view.change_classification}")


def render() -> None:
    nonce = st.session_state.get("refresh_nonce", 0)
    try:
        snap = _cached_control(nonce)
    except Exception as exc:
        st.error(f"Unable to load Control Center: {exc}")
        return

    status = snap.database_status
    st.subheader("Database Status")
    st.caption("Live checks only — not inferred from historical run reports or manifests.")
    c1, c2, c3 = st.columns(3)
    c1.metric("Health", status.health_label)
    c2.metric("validate_v1", status.validate_v1_label)
    c3.metric("Alembic", status.alembic_head or "—")

    st.write("Git:", snap.git.get("commit", "—"), "| dirty:", snap.git.get("dirty"))

    if st.button("Compute database fingerprint"):
        st.session_state["compute_fp"] = True

    if st.session_state.get("compute_fp"):
        try:
            fp = _cached_fingerprint(nonce, True)
            if fp:
                st.code(fp.database_fingerprint)
        except Exception as exc:
            st.error(f"Fingerprint failed: {exc}")

    st.subheader("Table Summary")
    for t in snap.health.tables:
        st.write(
            f"**{t.table}** — {t.row_count:,} rows | "
            f"{t.first_date} → {t.last_date} ({t.grain})"
        )

    st.subheader("Operational Runs")
    _render_run_section("Latest Attempt", snap.latest_run_attempt)
    _render_run_section("Latest Successful Run", snap.latest_successful_run)

    st.subheader("Latest Manifest 1.1")
    summary = manifest_summary(snap.latest_manifest)
    if summary:
        st.json(summary)
    else:
        st.info("No manifests found.")

    with st.expander("Health details"):
        st.json(snap.health_dict)
