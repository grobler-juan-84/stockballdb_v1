"""Shared Explorer presentation helpers (Phase 11D) — display only."""

from stockballdb.explorer.ui.chrome import render_app_header
from stockballdb.explorer.ui.components import (
    dataframe_dense,
    kv_table,
    metric_row,
    page_header,
    result_banner,
    section_heading,
    status_badge,
    toolbar_columns,
)
from stockballdb.explorer.ui.css import inject_explorer_css
from stockballdb.explorer.ui.dataframes import financial_column_config, rows_to_styled_dataframe

__all__ = [
    "dataframe_dense",
    "financial_column_config",
    "inject_explorer_css",
    "kv_table",
    "metric_row",
    "page_header",
    "render_app_header",
    "result_banner",
    "rows_to_styled_dataframe",
    "section_heading",
    "status_badge",
    "toolbar_columns",
]
