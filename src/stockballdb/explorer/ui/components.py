"""Reusable Streamlit presentation primitives (Phase 11D)."""

from __future__ import annotations

from typing import Any, Sequence

import streamlit as st


def page_header(title: str, caption: str | None = None) -> None:
    st.markdown(f"## {title}")
    if caption:
        st.caption(caption)


def section_heading(title: str) -> None:
    st.markdown(f"### {title}")


def status_badge(kind: str, text: str) -> str:
    """Return HTML for an inline status badge (ok|warn|bad|info|muted)."""
    cls = {
        "ok": "sbdb-badge-ok",
        "warn": "sbdb-badge-warn",
        "bad": "sbdb-badge-bad",
        "info": "sbdb-badge-info",
        "muted": "sbdb-badge-muted",
    }.get(kind, "sbdb-badge-muted")
    return f'<span class="sbdb-badge {cls}">{text}</span>'


def metric_row(items: Sequence[tuple[str, str]]) -> None:
    """Compact label/value metrics in equal columns."""
    if not items:
        return
    cols = st.columns(len(items))
    for col, (label, value) in zip(cols, items, strict=True):
        col.metric(label, value)


def toolbar_columns(ratios: Sequence[float] | int) -> list[Any]:
    if isinstance(ratios, int):
        return list(st.columns(ratios))
    return list(st.columns(list(ratios)))


def kv_table(data: dict[str, Any] | None, *, title: str | None = None) -> None:
    """Render a dict as a two-column key/value table (presentation only)."""
    if title:
        section_heading(title)
    if not data:
        st.caption("No data.")
        return
    from stockballdb.explorer.formatting import format_cell

    rows = [{"field": str(k), "value": format_cell(v)} for k, v in data.items()]
    st.dataframe(rows, use_container_width=True, hide_index=True, height=min(420, 38 + 35 * len(rows)))


def result_banner(parts: Sequence[str]) -> None:
    body = " &nbsp;·&nbsp; ".join(p for p in parts if p)
    st.markdown(f'<div class="sbdb-banner">{body}</div>', unsafe_allow_html=True)


def dataframe_dense(data: Any, *, height: int = 520, column_config: dict | None = None) -> None:
    kwargs: dict[str, Any] = {
        "use_container_width": True,
        "height": height,
        "hide_index": True,
    }
    if column_config:
        kwargs["column_config"] = column_config
    st.dataframe(data, **kwargs)
