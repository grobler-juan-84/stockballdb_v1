"""Reusable Streamlit presentation primitives (Phase 11D Pass 2)."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator, Sequence

import streamlit as st


def page_header(title: str, caption: str | None = None, *, icon: str = "▣") -> None:
    cap = f'<p class="sbdb-page-caption">{caption}</p>' if caption else ""
    st.markdown(
        f'<div class="sbdb-page-header">'
        f'<div class="sbdb-page-icon">{icon}</div>'
        f"<div><p class=\"sbdb-page-title\">{title}</p>{cap}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )


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


@contextmanager
def panel() -> Iterator[None]:
    """White bordered content panel (toolbar / footer grouping)."""
    with st.container(border=True):
        st.markdown('<span class="sbdb-panel-marker"></span>', unsafe_allow_html=True)
        yield


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
    """Legacy single-line banner (kept for compatibility)."""
    body = " &nbsp;·&nbsp; ".join(p for p in parts if p)
    st.markdown(f'<div class="sbdb-banner">{body}</div>', unsafe_allow_html=True)


def result_strip(
    *,
    identity: str,
    identity_sub: str | None = None,
    metrics: Sequence[tuple[str, str, str | None]],
) -> None:
    """
    Structured result summary strip.

    metrics: sequence of (label, value, sublabel|None)
    """
    id_sub = f'<div class="s">{identity_sub}</div>' if identity_sub else ""
    parts = [
        f'<div class="sbdb-result-id"><div class="k">Selection</div>'
        f'<div class="v">{identity}</div>{id_sub}</div>'
    ]
    for label, value, sub in metrics:
        sub_html = f'<div class="s">{sub}</div>' if sub else ""
        parts.append(
            f'<div class="sbdb-result-metric"><div class="k">{label}</div>'
            f'<div class="v">{value}</div>{sub_html}</div>'
        )
    st.markdown(
        f'<div class="sbdb-result-strip">{"".join(parts)}</div>',
        unsafe_allow_html=True,
    )


def dataframe_dense(data: Any, *, height: int = 520, column_config: dict | None = None) -> None:
    kwargs: dict[str, Any] = {
        "use_container_width": True,
        "height": height,
        "hide_index": True,
    }
    if column_config:
        kwargs["column_config"] = column_config
    st.dataframe(data, **kwargs)
