"""Day Inspector page."""

from __future__ import annotations

import datetime as dt

import streamlit as st

from stockballdb.explorer.db import readonly_connection
from stockballdb.explorer.formatting import rows_to_display_dicts
from stockballdb.explorer.services.day import inspect_day
from stockballdb.market_data.universe import V1_MARKET_SYMBOLS


def render() -> None:
    st.caption("Cross-table factual inspection for one calendar date.")
    col1, col2 = st.columns(2)
    target = col1.date_input("Calendar date", value=dt.date(2026, 8, 28))
    sym_choice = col2.selectbox("Symbol (optional)", options=["(all)"] + list(V1_MARKET_SYMBOLS))
    symbol = None if sym_choice == "(all)" else sym_choice

    if not st.button("Inspect date", type="primary"):
        return

    try:
        with readonly_connection() as conn:
            result = inspect_day(conn, target, symbol)
    except Exception as exc:
        st.error(f"Inspection failed: {exc}")
        return

    st.subheader(f"Calendar date: {result.calendar_date.isoformat()}")
    for msg in result.messages:
        st.info(msg)

    if result.is_trading_day:
        st.success("Trading session: yes")
    else:
        st.warning("Trading session: none")

    if result.previous_session:
        st.write(f"Previous session: **{result.previous_session['date']}**")
    if result.next_session:
        st.write(f"Next session: **{result.next_session['date']}**")

    if result.trading_day:
        st.subheader("Trading Day")
        st.json(result.trading_day)

    if result.calendar_context:
        st.subheader("Calendar Context")
        st.json(result.calendar_context)

    if result.scheduled_events:
        st.subheader("Scheduled Events")
        st.dataframe(rows_to_display_dicts(result.scheduled_events), use_container_width=True)

    if result.macro_conditions:
        st.subheader("Macro Conditions")
        st.json(result.macro_conditions)

    if result.daily_market_data:
        st.subheader("Daily Market Data")
        st.dataframe(rows_to_display_dicts(result.daily_market_data), use_container_width=True)

    if result.market_outcomes:
        st.subheader("Market Outcomes")
        st.dataframe(rows_to_display_dicts(result.market_outcomes), use_container_width=True)

    if result.asset_regimes:
        st.subheader("Asset Regimes")
        st.dataframe(rows_to_display_dicts(result.asset_regimes), use_container_width=True)
