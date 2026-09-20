"""StockBallDB V2 application façade (transport-agnostic use-case layer).

P1 exposes Catalog and Status only. Callers should use these APIs instead of
importing Explorer internals, SQLAlchemy models, or Streamlit.
"""

from stockballdb.app.errors import AppError, AppNotFoundError, AppUnavailableError
from stockballdb.app.read import catalog, status

__all__ = [
    "AppError",
    "AppNotFoundError",
    "AppUnavailableError",
    "catalog",
    "status",
]
