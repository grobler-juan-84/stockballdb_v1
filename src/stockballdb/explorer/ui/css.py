"""Narrow Explorer CSS for desktop density + Pass 2 visual polish (Phase 11D)."""

from __future__ import annotations

import streamlit as st

# Documented assumptions (Streamlit 1.40–1.x / 1.62):
# - Styles header shell, page_link nav, panels, result strip, dataframe chrome.
# - Uses structural testids + our sbdb-* classes — not deep nth-child widget trees.
# - Layout degrades gracefully if a selector is ignored after a Streamlit bump.
# - Functional correctness never depends on CSS.

_EXPLORER_CSS = """
<style>
:root {
  --sbdb-navy: #0b1f3a;
  --sbdb-navy-2: #132a4a;
  --sbdb-navy-3: #1a3558;
  --sbdb-blue: #2563eb;
  --sbdb-blue-soft: #dbeafe;
  --sbdb-bg: #eef2f7;
  --sbdb-panel: #ffffff;
  --sbdb-border: #d5dee9;
  --sbdb-text: #0f172a;
  --sbdb-muted: #64748b;
  --sbdb-ok: #15803d;
  --sbdb-bad: #b91c1c;
  --sbdb-warn: #b45309;
}

/* App canvas */
.stApp {
  background: var(--sbdb-bg);
}
section.main > div.block-container {
  max-width: 100%;
  padding-top: 0.55rem;
  padding-bottom: 1.25rem;
  padding-left: 1.25rem;
  padding-right: 1.25rem;
}

/* Collapse unused Streamlit chrome when using custom shell nav */
header[data-testid="stHeader"] {
  background: transparent;
  height: 2.25rem;
}
div[data-testid="stToolbar"] { right: 0.5rem; }

/* Compact heading rhythm */
h1, h2, h3 { color: var(--sbdb-text) !important; }
h1 { font-size: 1.35rem !important; margin: 0 0 0.1rem 0 !important; line-height: 1.25 !important; }
h2 { font-size: 1.28rem !important; margin: 0.15rem 0 0.1rem 0 !important; line-height: 1.25 !important; }
h3 { font-size: 0.95rem !important; margin: 0.45rem 0 0.2rem 0 !important; }
label, .stCaption, [data-testid="stCaptionContainer"] {
  font-size: 0.78rem !important;
  color: var(--sbdb-muted) !important;
}

/* ===== Application shell ===== */
div[data-testid="stVerticalBlockBorderWrapper"]:has(.sbdb-shell-marker),
.sbdb-shell-wrap {
  background: var(--sbdb-navy) !important;
  border: 1px solid var(--sbdb-navy) !important;
  border-radius: 8px !important;
  padding: 0.35rem 0.65rem 0.45rem 0.65rem !important;
  margin: 0 0 0.55rem 0 !important;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.18);
}
.sbdb-shell-marker { display: none; }
.sbdb-brand {
  color: #f8fafc;
  font-weight: 700;
  font-size: 1.05rem;
  letter-spacing: 0.01em;
  margin: 0;
  line-height: 1.15;
}
.sbdb-tagline {
  color: #94a3b8;
  font-size: 0.68rem;
  margin: 0.05rem 0 0 0;
  line-height: 1.2;
}
.sbdb-status-block {
  text-align: right;
  color: #e2e8f0;
  line-height: 1.15;
}
.sbdb-status-label {
  font-size: 0.65rem;
  color: #94a3b8;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.sbdb-status-value {
  font-size: 0.84rem;
  font-weight: 600;
  color: #f8fafc;
}
.sbdb-health-line {
  margin-top: 0.2rem;
  font-size: 0.8rem;
  color: #e2e8f0;
}
.sbdb-dot {
  display: inline-block;
  width: 0.5rem;
  height: 0.5rem;
  border-radius: 50%;
  margin-right: 0.35rem;
  vertical-align: middle;
}
.sbdb-dot-ok { background: #22c55e; }
.sbdb-dot-warn { background: #f59e0b; }
.sbdb-dot-bad { background: #ef4444; }
.sbdb-dot-muted { background: #64748b; }

/* Shell page links (custom nav) */
div[data-testid="stVerticalBlockBorderWrapper"]:has(.sbdb-shell-marker) a[data-testid="stPageLink-NavLink"],
div[data-testid="stVerticalBlockBorderWrapper"]:has(.sbdb-shell-marker) [data-testid="stPageLink"] a {
  color: #cbd5e1 !important;
  background: transparent !important;
  border-radius: 4px !important;
  border-bottom: 2px solid transparent !important;
  padding: 0.35rem 0.4rem !important;
  font-size: 0.82rem !important;
  font-weight: 500 !important;
  justify-content: center !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.sbdb-shell-marker) a[data-testid="stPageLink-NavLink"]:hover,
div[data-testid="stVerticalBlockBorderWrapper"]:has(.sbdb-shell-marker) [data-testid="stPageLink"] a:hover {
  color: #ffffff !important;
  background: var(--sbdb-navy-3) !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.sbdb-shell-marker) a[aria-current="page"],
div[data-testid="stVerticalBlockBorderWrapper"]:has(.sbdb-shell-marker) [aria-current="page"] a,
div[data-testid="stVerticalBlockBorderWrapper"]:has(.sbdb-shell-marker) a[data-testid="stPageLink-NavLink"][aria-current="page"] {
  color: #ffffff !important;
  background: var(--sbdb-navy-2) !important;
  border-bottom: 2px solid var(--sbdb-blue) !important;
  font-weight: 650 !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.sbdb-shell-marker) button {
  background: var(--sbdb-navy-3) !important;
  color: #e2e8f0 !important;
  border: 1px solid #334155 !important;
  min-height: 2rem !important;
  font-size: 0.75rem !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.sbdb-shell-marker) button:hover {
  border-color: var(--sbdb-blue) !important;
  color: #fff !important;
}

/* ===== Page header ===== */
.sbdb-page-header {
  display: flex;
  align-items: flex-start;
  gap: 0.65rem;
  margin: 0.1rem 0 0.55rem 0;
}
.sbdb-page-icon {
  width: 2rem;
  height: 2rem;
  border-radius: 999px;
  background: var(--sbdb-blue-soft);
  color: var(--sbdb-blue);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.95rem;
  flex-shrink: 0;
  margin-top: 0.05rem;
}
.sbdb-page-title {
  margin: 0;
  font-size: 1.28rem;
  font-weight: 700;
  color: var(--sbdb-text);
  line-height: 1.2;
}
.sbdb-page-caption {
  margin: 0.12rem 0 0 0;
  font-size: 0.82rem;
  color: var(--sbdb-muted);
}

/* ===== Panels / toolbar ===== */
div[data-testid="stVerticalBlockBorderWrapper"]:has(.sbdb-panel-marker) {
  background: var(--sbdb-panel) !important;
  border: 1px solid var(--sbdb-border) !important;
  border-radius: 8px !important;
  padding: 0.55rem 0.7rem !important;
  margin: 0 0 0.55rem 0 !important;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}
.sbdb-panel-marker { display: none; }

/* Primary button emphasis */
div[data-testid="stVerticalBlockBorderWrapper"]:has(.sbdb-panel-marker) button[kind="primary"],
div[data-testid="stVerticalBlockBorderWrapper"]:has(.sbdb-panel-marker) button[data-testid="baseButton-primary"] {
  background: var(--sbdb-blue) !important;
  border-color: var(--sbdb-blue) !important;
  font-weight: 650 !important;
}

/* ===== Result strip ===== */
.sbdb-result-strip {
  display: flex;
  flex-wrap: wrap;
  align-items: stretch;
  gap: 0.75rem 1.25rem;
  background: var(--sbdb-panel);
  border: 1px solid var(--sbdb-border);
  border-radius: 8px;
  padding: 0.65rem 0.85rem;
  margin: 0 0 0.55rem 0;
}
.sbdb-result-id {
  min-width: 7rem;
}
.sbdb-result-id .k {
  font-size: 0.68rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--sbdb-muted);
}
.sbdb-result-id .v {
  font-size: 1.05rem;
  font-weight: 700;
  color: var(--sbdb-text);
}
.sbdb-result-metric .k {
  font-size: 0.68rem;
  color: var(--sbdb-muted);
  text-transform: uppercase;
  letter-spacing: 0.03em;
}
.sbdb-result-metric .v {
  font-size: 1.05rem;
  font-weight: 700;
  color: var(--sbdb-blue);
  line-height: 1.15;
}
.sbdb-result-metric .v.neutral { color: var(--sbdb-text); }
.sbdb-result-metric .s {
  font-size: 0.75rem;
  color: var(--sbdb-muted);
}

/* ===== Table / footer ===== */
.sbdb-table-wrap div[data-testid="stDataFrame"],
div[data-testid="stDataFrame"] {
  border: 1px solid var(--sbdb-border);
  border-radius: 8px;
  overflow: hidden;
  background: var(--sbdb-panel);
}
.sbdb-table-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  background: var(--sbdb-panel);
  border: 1px solid var(--sbdb-border);
  border-radius: 8px;
  padding: 0.45rem 0.65rem;
  margin: 0.45rem 0 0.55rem 0;
}
.sbdb-meta-panel {
  background: #f8fafc;
  border: 1px dashed var(--sbdb-border);
  border-radius: 8px;
  padding: 0.55rem 0.75rem;
  margin-top: 0.35rem;
  color: var(--sbdb-muted);
  font-size: 0.82rem;
}

/* Badges / misc */
.sbdb-banner {
  background: var(--sbdb-panel);
  border: 1px solid var(--sbdb-border);
  border-radius: 6px;
  padding: 0.55rem 0.75rem;
  margin: 0.25rem 0 0.45rem 0;
  font-size: 0.88rem;
}
.sbdb-banner strong { color: var(--sbdb-text); }
.sbdb-muted { color: var(--sbdb-muted); font-size: 0.82rem; }
.sbdb-badge {
  display: inline-block;
  padding: 0.12rem 0.45rem;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.02em;
}
.sbdb-badge-ok { background: #dcfce7; color: #166534; }
.sbdb-badge-warn { background: #fef3c7; color: #92400e; }
.sbdb-badge-bad { background: #fee2e2; color: #991b1b; }
.sbdb-badge-info { background: #dbeafe; color: #1e40af; }
.sbdb-badge-muted { background: #e2e8f0; color: #334155; }

/* Hide collapsed sidebar gutter when unused */
section[data-testid="stSidebar"] { display: none !important; }
</style>
"""


def inject_explorer_css() -> None:
    """Inject every run so Pass 2 CSS updates without a stale session flag."""
    st.markdown(_EXPLORER_CSS, unsafe_allow_html=True)
