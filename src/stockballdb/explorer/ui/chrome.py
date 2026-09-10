"""Application shell header (Phase 11D Pass 3) — presentation only."""

from __future__ import annotations

import datetime as dt
from typing import Any

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
    except Exception:
        pass

    health = live.health_label or "ERROR"
    if live.error_message:
        health = "ERROR"
    return {
        "health": str(health),
        "last_update": _format_last_update(last_update),
        "validate": str(live.validate_v1_label),
    }


def _format_last_update(raw: str) -> str:
    """Presentation-only: ISO dates → 'Aug 31, 2026' style."""
    if not raw or raw == "—":
        return "—"
    text = str(raw).strip()
    try:
        day = dt.date.fromisoformat(text[:10])
        return f"{day.strftime('%b')} {day.day}, {day.year}"
    except ValueError:
        if "T" in text and len(text) >= 10:
            return text[:10]
        return text


def _dot_class(health: str) -> str:
    h = health.upper()
    if h == "HEALTHY":
        return "sbdb-dot-ok"
    if "WARN" in h:
        return "sbdb-dot-warn"
    if h in {"UNHEALTHY", "ERROR", "FAIL"}:
        return "sbdb-dot-bad"
    return "sbdb-dot-muted"


def _health_display(health: str) -> str:
    h = health.upper()
    if h == "HEALTHY":
        return "Database Healthy"
    if "WARN" in h:
        return health
    return health


def render_app_header(pages: list[Any] | None = None) -> None:
    """
    Unified dark application shell: brand + page links + status.

    Uses ``st.page_link`` against the same ``st.Page`` objects as ``st.navigation``
    so url_path routing stays certified. Navigation position is ``hidden``.
    """
    nonce = int(st.session_state.get("refresh_nonce", 0))
    try:
        status = _shell_status(nonce)
    except Exception:
        status = {"health": "ERROR", "last_update": "—", "validate": "ERROR"}

    health = status["health"]
    last_update = status["last_update"]
    dot = _dot_class(health)
    health_label = _health_display(health)

    with st.container(border=True):
        st.markdown('<span class="sbdb-shell-marker"></span>', unsafe_allow_html=True)
        brand_col, nav_col, status_col = st.columns([1.65, 5.5, 1.85], gap="small")

        with brand_col:
            st.markdown(
                '<p class="sbdb-brand">StockBallDB</p>'
                '<p class="sbdb-tagline">Historical Data. Real Context.</p>',
                unsafe_allow_html=True,
            )

        with nav_col:
            if pages:
                link_cols = st.columns(len(pages), gap="small")
                for col, page in zip(link_cols, pages, strict=True):
                    with col:
                        label = getattr(page, "title", None) or str(page)
                        icon = getattr(page, "icon", None)
                        st.page_link(page, label=label, icon=icon, use_container_width=True)

        with status_col:
            s1, s2 = st.columns([3.2, 0.9], gap="small")
            with s1:
                st.markdown(
                    f'<div class="sbdb-status-block">'
                    f'<div class="sbdb-status-label">Last Update</div>'
                    f'<div class="sbdb-status-value">{last_update}</div>'
                    f'<div class="sbdb-health-line">'
                    f'<span class="sbdb-dot {dot}"></span>{health_label}'
                    f"</div></div>",
                    unsafe_allow_html=True,
                )
            with s2:
                if st.button(
                    "↻",
                    key="sbdb_header_refresh",
                    help="Refresh status & caches",
                    use_container_width=True,
                ):
                    st.session_state.refresh_nonce = nonce + 1
                    st.cache_data.clear()
                    st.rerun()
