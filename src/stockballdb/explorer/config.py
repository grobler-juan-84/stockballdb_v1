"""Explorer configuration constants."""

from __future__ import annotations

import datetime as dt

from stockballdb.calendar.nyse import CALENDAR_START, today_ny

DEFAULT_PAGE_SIZE = 100
MAX_PAGE_SIZE = 500
CSV_EXPORT_MAX_ROWS = 10_000
LOCALHOST_BIND = "localhost"

# Explicit Streamlit date_input bounds (avoid Streamlit's implicit ±10y window).
EXPLORER_DATE_MIN: dt.date = CALENDAR_START  # 1957-01-01


def explorer_date_max() -> dt.date:
    """Upper bound for Explorer date widgets (America/New_York calendar date)."""
    return today_ny()


def explorer_date_input_bounds() -> dict[str, dt.date]:
    """Keyword args for ``st.date_input`` min/max across Explorer views."""
    return {"min_value": EXPLORER_DATE_MIN, "max_value": explorer_date_max()}
