"""Day Inspector page — desktop two-pane layout (Phase 11D)."""

from __future__ import annotations

import streamlit as st

from stockballdb.explorer.config import explorer_date_input_bounds, explorer_date_max
from stockballdb.explorer.db import readonly_connection
from stockballdb.explorer.formatting import rows_to_display_dicts
from stockballdb.explorer.services.day import inspect_day
from stockballdb.explorer.ui.components import dataframe_dense, kv_table, page_header, panel, section_heading
from stockballdb.market_data.universe import V1_MARKET_SYMBOLS


def render() -> None:
    page_header("Day Inspector", "Cross-table factual inspection for one calendar date.", icon="▦")

    with panel():
        c_date, c_sym, c_go = st.columns([1.4, 1.2, 0.8], gap="small")
        target = c_date.date_input(
            "Calendar date",
            value=explorer_date_max(),
            key="di_date",
            **explorer_date_input_bounds(),
        )
        sym_choice = c_sym.selectbox(
            "Symbol (optional)",
            options=["(all)"] + list(V1_MARKET_SYMBOLS),
            key="di_symbol",
        )
        symbol = None if sym_choice == "(all)" else sym_choice
        inspect = c_go.button("Inspect", type="primary", use_container_width=True)

    if not inspect and "di_result" not in st.session_state:
        st.info("Choose a date (and optional symbol), then click **Inspect**.")
        return

    if inspect:
        try:
            with readonly_connection() as conn:
                st.session_state["di_result"] = inspect_day(conn, target, symbol)
        except Exception as exc:
            st.error(f"Inspection failed: {exc}")
            return

    result = st.session_state.get("di_result")
    if result is None:
        return

    st.markdown(f"**Calendar date:** `{result.calendar_date.isoformat()}`")

    # Deduplicate presentation of session messaging
    shown: set[str] = set()
    for msg in result.messages:
        if msg in shown:
            continue
        shown.add(msg)
        st.info(msg)

    session_bits = []
    if result.is_trading_day:
        session_bits.append("Trading session: **yes**")
    else:
        session_bits.append("Trading session: **none**")
    if result.previous_session:
        session_bits.append(f"Previous: `{result.previous_session['date']}`")
    if result.next_session:
        session_bits.append(f"Next: `{result.next_session['date']}`")
    st.caption(" · ".join(session_bits))

    left, right = st.columns(2)
    with left:
        section_heading("Date-level context")
        if result.trading_day:
            kv_table(result.trading_day, title="Trading Day")
        if result.calendar_context:
            kv_table(result.calendar_context, title="Calendar Context")
        if result.macro_conditions:
            kv_table(result.macro_conditions, title="Macro Conditions")
        if result.scheduled_events:
            section_heading("Scheduled Events")
            dataframe_dense(rows_to_display_dicts(result.scheduled_events), height=220)
        if not any(
            [
                result.trading_day,
                result.calendar_context,
                result.macro_conditions,
                result.scheduled_events,
            ]
        ):
            st.caption("No date-level rows for this calendar date.")

    with right:
        section_heading("Symbol-level data")
        if result.daily_market_data:
            section_heading("Daily Market Data")
            dataframe_dense(rows_to_display_dicts(result.daily_market_data), height=240)
        if result.market_outcomes:
            section_heading("Market Outcomes")
            dataframe_dense(rows_to_display_dicts(result.market_outcomes), height=240)
        if result.asset_regimes:
            section_heading("Asset Regimes")
            dataframe_dense(rows_to_display_dicts(result.asset_regimes), height=240)
        if not any([result.daily_market_data, result.market_outcomes, result.asset_regimes]):
            st.caption("No symbol-level rows for this selection.")
