"""Streamlit application shell and navigation."""

from __future__ import annotations

import streamlit as st

from stockballdb.explorer.db import check_explorer_connection
from stockballdb.explorer.pages import (
    control_center,
    coverage_explorer,
    data_explorer,
    day_inspector,
    provenance_explorer,
    validation_center,
)


def _init_session() -> None:
    if "refresh_nonce" not in st.session_state:
        st.session_state.refresh_nonce = 0


def _sidebar() -> None:
    st.sidebar.title("StockBallDB Explorer")
    st.sidebar.caption("Read-only inspection")
    if st.sidebar.button("Refresh", type="primary"):
        st.session_state.refresh_nonce += 1
        st.cache_data.clear()
        st.rerun()
    st.sidebar.divider()
    try:
        check_explorer_connection()
        st.sidebar.success("Database connected")
    except Exception:
        st.sidebar.error("Database unavailable")


def main() -> None:
    _init_session()
    _sidebar()
    pages = [
        st.Page(control_center.render, title="Control Center", icon=":material/dashboard:"),
        st.Page(data_explorer.render, title="Data Explorer", icon=":material/table:"),
        st.Page(day_inspector.render, title="Day Inspector", icon=":material/calendar_today:"),
        st.Page(coverage_explorer.render, title="Coverage Explorer", icon=":material/analytics:"),
        st.Page(provenance_explorer.render, title="Provenance Explorer", icon=":material/history:"),
        st.Page(validation_center.render, title="Validation Center", icon=":material/verified:"),
    ]
    nav = st.navigation(pages)
    st.title("StockBallDB Explorer")
    nav.run()


if __name__ == "__main__":
    main()
