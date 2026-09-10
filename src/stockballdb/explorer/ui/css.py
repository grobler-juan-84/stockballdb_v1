"""Explorer CSS — Phase 11D Pass 4 (flush top shell + mockup navy)."""

from __future__ import annotations

import streamlit as st

# Documented assumptions (Streamlit 1.40–1.x / 1.62):
# - Pass 4: pin shell to viewport top; match mockup deep navy; soft blue active pill.
# - Targets structural testids + sbdb-* classes; no deep nth-child widget trees.
# - Layout degrades gracefully if a selector is ignored after a Streamlit bump.
# - Functional correctness never depends on CSS.

_EXPLORER_CSS = """
<style>
:root {
  /* Mockup-aligned deep navy (charcoal-navy, not bright blue-navy) */
  --sbdb-navy: #0a1628;
  --sbdb-navy-2: #102038;
  --sbdb-navy-3: #162a45;
  --sbdb-navy-edge: #060e1a;
  --sbdb-pill-bg: rgba(37, 99, 235, 0.32);
  --sbdb-pill-border: rgba(96, 165, 250, 0.55);
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
  --sbdb-gutter: 1.25rem;
}

/* ===== Kill Streamlit chrome that creates top gap ===== */
header[data-testid="stHeader"],
header[data-testid="stHeader"] > * {
  display: none !important;
  height: 0 !important;
  min-height: 0 !important;
  max-height: 0 !important;
  padding: 0 !important;
  margin: 0 !important;
  border: none !important;
  opacity: 0 !important;
  pointer-events: none !important;
}
div[data-testid="stToolbar"],
div[data-testid="stDecoration"],
div[data-testid="stStatusWidget"],
#MainMenu,
footer,
.stDeployButton,
[data-testid="stSidebarCollapsedControl"] {
  display: none !important;
}

.stApp {
  background: var(--sbdb-bg);
  margin: 0 !important;
  padding: 0 !important;
}
[data-testid="stAppViewContainer"] {
  margin: 0 !important;
  padding: 0 !important;
}
[data-testid="stAppViewContainer"] > section.main {
  margin: 0 !important;
  padding: 0 !important;
}
section.main > div.block-container,
div[data-testid="stMainBlockContainer"] {
  max-width: 100% !important;
  padding-top: 0 !important;
  padding-bottom: 1.25rem !important;
  padding-left: var(--sbdb-gutter) !important;
  padding-right: var(--sbdb-gutter) !important;
  margin-top: 0 !important;
}
/* Collapse gap before first content block (our shell) */
section.main > div.block-container > div:first-child,
div[data-testid="stMainBlockContainer"] > div:first-child {
  margin-top: 0 !important;
  padding-top: 0 !important;
}

/* Compact heading rhythm */
h1, h2, h3 { color: var(--sbdb-text) !important; }
h1 { font-size: 1.35rem !important; margin: 0 0 0.1rem 0 !important; line-height: 1.25 !important; }
h2 { font-size: 1.28rem !important; margin: 0.15rem 0 0.1rem 0 !important; line-height: 1.25 !important; }
h3 { font-size: 0.95rem !important; margin: 0.45rem 0 0.2rem 0 !important; }
label, .stCaption, [data-testid="stCaptionContainer"] {
  font-size: 0.78rem !important;
  color: var(--sbdb-muted) !important;
}

/* ===== Application shell: flush top + full bleed ===== */
div[data-testid="stVerticalBlockBorderWrapper"]:has(.sbdb-shell-marker) {
  background: var(--sbdb-navy) !important;
  border: none !important;
  border-bottom: 1px solid var(--sbdb-navy-edge) !important;
  border-radius: 0 !important;
  padding: 0.5rem var(--sbdb-gutter) 0.45rem var(--sbdb-gutter) !important;
  /* Cancel block-container gutters so bar hits left/right viewport edges */
  margin-left: calc(-1 * var(--sbdb-gutter)) !important;
  margin-right: calc(-1 * var(--sbdb-gutter)) !important;
  margin-top: 0 !important;
  margin-bottom: 0.85rem !important;
  width: calc(100% + 2 * var(--sbdb-gutter)) !important;
  max-width: none !important;
  box-shadow: 0 1px 0 rgba(255, 255, 255, 0.04), 0 4px 12px rgba(0, 0, 0, 0.28);
  position: sticky;
  top: 0;
  z-index: 999;
}
.sbdb-shell-marker { display: none; }

div[data-testid="stVerticalBlockBorderWrapper"]:has(.sbdb-shell-marker)
  div[data-testid="stHorizontalBlock"] {
  gap: 0.3rem 0.45rem !important;
  align-items: center !important;
}

.sbdb-brand {
  color: #f8fafc;
  font-weight: 700;
  font-size: 1.08rem;
  letter-spacing: 0.01em;
  margin: 0;
  line-height: 1.1;
}
.sbdb-tagline {
  color: #94a3b8;
  font-size: 0.66rem;
  margin: 0.08rem 0 0 0;
  line-height: 1.2;
}
.sbdb-status-block {
  text-align: right;
  color: #e2e8f0;
  line-height: 1.15;
  padding-top: 0.05rem;
}
.sbdb-status-label {
  font-size: 0.62rem;
  color: #94a3b8;
  text-transform: none;
  letter-spacing: 0.01em;
  font-weight: 500;
}
.sbdb-status-value {
  font-size: 0.88rem;
  font-weight: 650;
  color: #f8fafc;
}
.sbdb-health-line {
  margin-top: 0.28rem;
  font-size: 0.78rem;
  color: #e2e8f0;
  font-weight: 500;
  white-space: nowrap;
}
.sbdb-dot {
  display: inline-block;
  width: 0.5rem;
  height: 0.5rem;
  border-radius: 50%;
  margin-right: 0.35rem;
  vertical-align: middle;
  box-shadow: 0 0 0 2px rgba(34, 197, 94, 0.18);
}
.sbdb-dot-ok { background: #22c55e; }
.sbdb-dot-warn { background: #f59e0b; box-shadow: 0 0 0 2px rgba(245, 158, 11, 0.2); }
.sbdb-dot-bad { background: #ef4444; box-shadow: 0 0 0 2px rgba(239, 68, 68, 0.2); }
.sbdb-dot-muted { background: #64748b; box-shadow: none; }

/* Inactive nav links */
div[data-testid="stVerticalBlockBorderWrapper"]:has(.sbdb-shell-marker) a[data-testid="stPageLink-NavLink"],
div[data-testid="stVerticalBlockBorderWrapper"]:has(.sbdb-shell-marker) [data-testid="stPageLink"] a {
  color: #b6c2d1 !important;
  background: transparent !important;
  border: 1px solid transparent !important;
  border-radius: 0.55rem !important;
  padding: 0.36rem 0.55rem !important;
  font-size: 0.78rem !important;
  font-weight: 500 !important;
  justify-content: center !important;
  gap: 0.3rem !important;
  box-shadow: none !important;
  min-height: 2.05rem !important;
  transition: color 0.12s ease, background 0.12s ease, border-color 0.12s ease;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.sbdb-shell-marker) a[data-testid="stPageLink-NavLink"] span,
div[data-testid="stVerticalBlockBorderWrapper"]:has(.sbdb-shell-marker) [data-testid="stPageLink"] a span {
  color: inherit !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.sbdb-shell-marker) a[data-testid="stPageLink-NavLink"]:hover,
div[data-testid="stVerticalBlockBorderWrapper"]:has(.sbdb-shell-marker) [data-testid="stPageLink"] a:hover {
  color: #ffffff !important;
  background: rgba(255, 255, 255, 0.06) !important;
}

/* Active nav — soft blue rounded rect (mockup), not cyan neon glow */
div[data-testid="stVerticalBlockBorderWrapper"]:has(.sbdb-shell-marker) a[aria-current="page"],
div[data-testid="stVerticalBlockBorderWrapper"]:has(.sbdb-shell-marker) [aria-current="page"] a,
div[data-testid="stVerticalBlockBorderWrapper"]:has(.sbdb-shell-marker) a[data-testid="stPageLink-NavLink"][aria-current="page"] {
  color: #ffffff !important;
  background: var(--sbdb-pill-bg) !important;
  border: 1px solid var(--sbdb-pill-border) !important;
  border-radius: 0.55rem !important;
  box-shadow: none !important;
  font-weight: 650 !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.sbdb-shell-marker) a[aria-current="page"]:hover,
div[data-testid="stVerticalBlockBorderWrapper"]:has(.sbdb-shell-marker) a[data-testid="stPageLink-NavLink"][aria-current="page"]:hover {
  background: rgba(37, 99, 235, 0.42) !important;
  border-color: rgba(147, 197, 253, 0.7) !important;
  color: #ffffff !important;
}

/* Compact refresh in shell */
div[data-testid="stVerticalBlockBorderWrapper"]:has(.sbdb-shell-marker) button {
  background: transparent !important;
  color: #94a3b8 !important;
  border: 1px solid #334155 !important;
  border-radius: 999px !important;
  min-height: 2.05rem !important;
  height: 2.05rem !important;
  font-size: 0.85rem !important;
  padding: 0 !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.sbdb-shell-marker) button:hover {
  border-color: #60a5fa !important;
  color: #fff !important;
  background: rgba(37, 99, 235, 0.15) !important;
}

/* ===== Page header ===== */
.sbdb-page-header {
  display: flex;
  align-items: flex-start;
  gap: 0.65rem;
  margin: 0.1rem 0 0.55rem 0;
}
.sbdb-page-icon {
  width: 2.15rem;
  height: 2.15rem;
  border-radius: 0.55rem;
  background: var(--sbdb-blue);
  color: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.95rem;
  flex-shrink: 0;
  margin-top: 0.05rem;
  box-shadow: 0 1px 2px rgba(37, 99, 235, 0.35);
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
.sbdb-result-id { min-width: 7rem; }
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
div[data-testid="stDataFrame"] {
  border: 1px solid var(--sbdb-border);
  border-radius: 8px;
  overflow: hidden;
  background: var(--sbdb-panel);
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

section[data-testid="stSidebar"] { display: none !important; }
</style>
"""


def inject_explorer_css() -> None:
    """Inject every run so Pass 4 CSS updates without a stale session flag."""
    st.markdown(_EXPLORER_CSS, unsafe_allow_html=True)
