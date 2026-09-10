"""Narrow Explorer CSS for desktop density (Phase 11D)."""

from __future__ import annotations

import streamlit as st

# Documented assumptions (Streamlit 1.40–1.x):
# - Targets stable structural classes (block-container, header, sidebar).
# - Does not depend on functional correctness — layout degrades to default if ignored.
# - Avoids deep nth-child widget hacks.

_EXPLORER_CSS = """
<style>
/* Wider main workspace, less vertical padding */
section.main > div.block-container {
  max-width: 100%;
  padding-top: 1rem;
  padding-bottom: 1.5rem;
  padding-left: 1.5rem;
  padding-right: 1.5rem;
}

/* Compact default heading rhythm */
h1 { font-size: 1.45rem !important; margin-bottom: 0.15rem !important; }
h2 { font-size: 1.15rem !important; margin-top: 0.75rem !important; margin-bottom: 0.35rem !important; }
h3 { font-size: 1.0rem !important; margin-top: 0.55rem !important; margin-bottom: 0.25rem !important; }

/* Application header strip */
div[data-testid="stVerticalBlockBorderWrapper"].sbdb-app-header,
.sbdb-app-header {
  background: #0b1f3a;
  border: 1px solid #0b1f3a;
  border-radius: 6px;
  padding: 0.55rem 0.85rem;
  margin-bottom: 0.65rem;
}
.sbdb-brand {
  color: #f8fafc;
  font-weight: 700;
  font-size: 1.05rem;
  letter-spacing: 0.01em;
  margin: 0;
}
.sbdb-tagline {
  color: #94a3b8;
  font-size: 0.72rem;
  margin: 0;
}
.sbdb-status {
  color: #e2e8f0;
  font-size: 0.82rem;
  text-align: right;
}
.sbdb-dot {
  display: inline-block;
  width: 0.55rem;
  height: 0.55rem;
  border-radius: 50%;
  margin-right: 0.35rem;
  vertical-align: middle;
}
.sbdb-dot-ok { background: #22c55e; }
.sbdb-dot-warn { background: #f59e0b; }
.sbdb-dot-bad { background: #ef4444; }
.sbdb-dot-muted { background: #64748b; }

/* Result / section chrome */
.sbdb-banner {
  background: #ffffff;
  border: 1px solid #dbe3ef;
  border-radius: 6px;
  padding: 0.55rem 0.75rem;
  margin: 0.35rem 0 0.55rem 0;
  font-size: 0.9rem;
}
.sbdb-banner strong { color: #0f172a; }
.sbdb-muted { color: #64748b; font-size: 0.82rem; }
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

/* Tighten sidebar if Streamlit still shows page nav */
section[data-testid="stSidebar"] {
  min-width: 12rem;
  max-width: 14rem;
}
section[data-testid="stSidebar"] .block-container {
  padding-top: 0.75rem;
}
</style>
"""


def inject_explorer_css() -> None:
    """Inject once per session. Safe no-op if HTML disallowed."""
    if st.session_state.get("_sbdb_css_injected"):
        return
    st.markdown(_EXPLORER_CSS, unsafe_allow_html=True)
    st.session_state["_sbdb_css_injected"] = True
