"""Explorer navigation configuration (testable, explicit URL pathnames)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import streamlit as st

from stockballdb.explorer import views


@dataclass(frozen=True)
class ExplorerPageSpec:
    module_name: str
    url_path: str
    title: str
    icon: str
    default: bool = False


EXPLORER_PAGE_SPECS: tuple[ExplorerPageSpec, ...] = (
    ExplorerPageSpec(
        "control_center",
        "control-center",
        "Control Center",
        ":material/dashboard:",
        default=True,
    ),
    ExplorerPageSpec("data_explorer", "data-explorer", "Data Explorer", ":material/table:"),
    ExplorerPageSpec("day_inspector", "day-inspector", "Day Inspector", ":material/calendar_today:"),
    ExplorerPageSpec(
        "coverage_explorer",
        "coverage-explorer",
        "Coverage",
        ":material/analytics:",
    ),
    ExplorerPageSpec(
        "provenance_explorer",
        "provenance-explorer",
        "Provenance",
        ":material/history:",
    ),
    ExplorerPageSpec(
        "validation_center",
        "validation-center",
        "Validation",
        ":material/verified:",
    ),
)


def build_explorer_pages() -> list[Any]:
    """Build st.Page list with unique explicit url_path values."""
    pages: list[Any] = []
    for spec in EXPLORER_PAGE_SPECS:
        render = getattr(getattr(views, spec.module_name), "render")
        pages.append(
            st.Page(
                render,
                title=spec.title,
                icon=spec.icon,
                url_path=spec.url_path,
                default=spec.default,
            )
        )
    return pages


def navigation_url_paths() -> list[str]:
    """Return configured URL pathnames (empty string = default/home page)."""
    paths: list[str] = []
    for spec in EXPLORER_PAGE_SPECS:
        paths.append("" if spec.default else spec.url_path)
    return paths
