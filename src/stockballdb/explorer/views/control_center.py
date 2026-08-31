"""Control Center page."""

from __future__ import annotations

import streamlit as st

from stockballdb.explorer.db import get_explorer_engine, readonly_connection
from stockballdb.explorer.services.control import (
    load_control_center,
    load_fingerprint,
    manifest_summary,
)


@st.cache_data(show_spinner="Loading status…")
def _cached_control(_nonce: int):
    engine = get_explorer_engine()
    return load_control_center(engine)


@st.cache_data(show_spinner="Computing fingerprint…")
def _cached_fingerprint(_nonce: int, compute: bool):
    if not compute:
        return None
    return load_fingerprint(get_explorer_engine())


def render() -> None:
    nonce = st.session_state.get("refresh_nonce", 0)
    try:
        snap = _cached_control(nonce)
    except Exception as exc:
        st.error(f"Unable to load Control Center: {exc}")
        return

    h = snap.health
    st.subheader("Database Status")
    c1, c2, c3 = st.columns(3)
    c1.metric("Health", h.status.value)
    c2.metric("validate_v1", "PASS" if h.validate_v1_pass else "FAIL")
    c3.metric("Alembic", h.alembic_head or "—")

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

    st.subheader("Latest Operational Run")
    if snap.latest_run and snap.latest_run.payload:
        r = snap.latest_run.payload
        st.write(
            f"Run `{r.get('run_id')}` — **{r.get('status')}** | "
            f"as-of {r.get('run_as_of')} | {r.get('change_classification') or '—'}"
        )
    else:
        st.info("No operational run reports found.")

    st.subheader("Latest Manifest 1.1")
    summary = manifest_summary(snap.latest_manifest)
    if summary:
        st.json(summary)
    else:
        st.info("No manifests found.")

    with st.expander("Health details"):
        st.json(snap.health_dict)
