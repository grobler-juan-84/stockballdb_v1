"""Streamlit application shell and navigation."""

from __future__ import annotations

import streamlit as st

from stockballdb.explorer.db import check_explorer_connection
from stockballdb.explorer.navigation import build_explorer_pages


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
    nav = st.navigation(build_explorer_pages())
    nav.run()


if __name__ == "__main__":
    main()
