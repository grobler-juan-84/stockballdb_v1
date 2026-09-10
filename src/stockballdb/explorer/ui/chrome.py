"""Application shell header (Phase 11D) — presentation only."""

from __future__ import annotations

import streamlit as st

from stockballdb.explorer.services.control import load_control_artifacts, load_live_database_status


@st.cache_data(ttl=45, show_spinner=False)
def _shell_status(_nonce: int) -> dict[str, str]:
    """
    Compact header status.

    TTL + refresh_nonce: Refresh clears cache and bumps nonce so status is not
    indefinitely stale (Control Center live health remains uncached on that page).
    """
    live = load_live_database_status()
    last_update = "—"
    try:
        artifacts = load_control_artifacts()
        success = artifacts.latest_successful_run
        if success and success.payload:
            last_update = str(
                success.payload.get("run_as_of")
                or success.payload.get("finished_at")
                or success.artifact_id
                or "—"
            )
            if "T" in last_update and len(last_update) >= 10:
                last_update = last_update[:10]
    except Exception:
        pass

    health = live.health_label or "ERROR"
    if live.error_message:
        health = "ERROR"
    return {"health": str(health), "last_update": last_update, "validate": str(live.validate_v1_label)}


def _dot_class(health: str) -> str:
    h = health.upper()
    if h == "HEALTHY":
        return "sbdb-dot-ok"
    if "WARN" in h:
        return "sbdb-dot-warn"
    if h in {"UNHEALTHY", "ERROR", "FAIL"}:
        return "sbdb-dot-bad"
    return "sbdb-dot-muted"


def render_app_header() -> None:
    """Dark compact application identity + status strip."""
    nonce = int(st.session_state.get("refresh_nonce", 0))
    try:
        status = _shell_status(nonce)
    except Exception:
        status = {"health": "ERROR", "last_update": "—", "validate": "ERROR"}

    health = status["health"]
    last_update = status["last_update"]
    dot = _dot_class(health)

    left, mid, right = st.columns([2.2, 4.5, 3.3])
    with left:
        st.markdown(
            '<p class="sbdb-brand">StockBallDB</p>'
            '<p class="sbdb-tagline">Historical Data. Real Context.</p>',
            unsafe_allow_html=True,
        )
    with mid:
        st.caption("Explorer · read-only · desktop")
    with right:
        st.markdown(
            f'<div class="sbdb-status">'
            f"Last update: <strong>{last_update}</strong>"
            f"&nbsp;&nbsp;"
            f'<span class="sbdb-dot {dot}"></span>{health}'
            f"</div>",
            unsafe_allow_html=True,
        )
        b1, b2 = st.columns(2)
        if b1.button("Refresh", key="sbdb_header_refresh", use_container_width=True):
            st.session_state.refresh_nonce = nonce + 1
            st.cache_data.clear()
            st.rerun()
        try:
            from stockballdb.explorer.db import check_explorer_connection

            check_explorer_connection()
            b2.caption("DB connected")
        except Exception:
            b2.caption("DB unavailable")
