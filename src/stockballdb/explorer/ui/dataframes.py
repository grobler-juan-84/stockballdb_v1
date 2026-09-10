"""Dataframe presentation helpers — display only (Phase 11D)."""

from __future__ import annotations

from typing import Any

import streamlit as st

from stockballdb.explorer.formatting import (
    NULL_DISPLAY,
    is_decimal_ratio_column,
    rows_to_display_dicts,
)


def financial_column_config(columns: list[str]) -> dict[str, Any]:
    """Streamlit column_config for known columns (widths / number hints)."""
    cfg: dict[str, Any] = {}
    for col in columns:
        if col == "date":
            cfg[col] = st.column_config.TextColumn("date", width="small")
        elif col == "symbol":
            cfg[col] = st.column_config.TextColumn("symbol", width="small")
        elif is_decimal_ratio_column(col):
            cfg[col] = st.column_config.TextColumn(col, width="small")
        elif col in {
            "open",
            "high",
            "low",
            "close",
            "adj_open",
            "adj_high",
            "adj_low",
            "adj_close",
            "volume",
        }:
            cfg[col] = st.column_config.TextColumn(col, width="small")
    return cfg


def _signed_color(value: Any) -> str:
    """CSS color for a display cell; empty string = default."""
    if value is None or value == NULL_DISPLAY or value == "":
        return ""
    try:
        # Display strings from format_cell (may already be percent like "0.70%")
        text = str(value).replace(",", "").strip()
        if text.endswith("%"):
            text = text[:-1]
        num = float(text)
    except (TypeError, ValueError):
        return ""
    if num > 0:
        return "color: #15803d; font-weight: 600"
    if num < 0:
        return "color: #b91c1c; font-weight: 600"
    return ""


def rows_to_styled_dataframe(rows: list[dict[str, Any]]):
    """
    Build a display dataframe with optional green/red styling on financial columns.

    Uses formatted cells (NULL → —; decimal ratios → percent) so certified NULL
    presentation is preserved. Does not mutate ``rows``.
    Returns (data, column_config) where data may be a pandas Styler or list[dict].
    """
    display = rows_to_display_dicts(rows)
    if not display:
        return display, None

    columns = list(display[0].keys())
    color_cols = [c for c in columns if is_decimal_ratio_column(c)]
    cfg = financial_column_config(columns)

    if not color_cols:
        return display, cfg

    try:
        import pandas as pd
    except ImportError:
        return display, cfg

    frame = pd.DataFrame(display)
    subset = [c for c in color_cols if c in frame.columns]
    if not subset:
        return display, cfg

    try:
        styled = frame.style.map(_signed_color, subset=subset)
        return styled, cfg
    except Exception:
        # Prefer unstyled certified display over a fragile styling failure.
        return display, cfg
