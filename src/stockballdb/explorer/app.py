"""Streamlit application shell and navigation (Phase 11D desktop shell)."""

from __future__ import annotations

import streamlit as st

from stockballdb.explorer.navigation import build_explorer_pages
from stockballdb.explorer.ui.chrome import render_app_header
from stockballdb.explorer.ui.css import inject_explorer_css


def _init_session() -> None:
    if "refresh_nonce" not in st.session_state:
        st.session_state.refresh_nonce = 0


def _configure_page() -> None:
    """Must run before other Streamlit calls."""
    st.set_page_config(
        page_title="StockBallDB Explorer",
        page_icon=":material/database:",
        layout="wide",
        initial_sidebar_state="collapsed",
    )


def main() -> None:
    _configure_page()
    _init_session()
    inject_explorer_css()
    render_app_header()
    nav = st.navigation(build_explorer_pages(), position="top")
    nav.run()


if __name__ == "__main__":
    main()
