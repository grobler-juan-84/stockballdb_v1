"""Standard library logging setup for StockBallDB."""

from __future__ import annotations

import logging
import sys
from typing import TextIO

_CONFIGURED = False

DEFAULT_FORMAT = "%(asctime)s %(levelname)s %(message)s"
DEFAULT_DATEFMT = "%Y-%m-%d %H:%M:%S"


def configure_logging(
    level: int = logging.INFO,
    *,
    stream: TextIO | None = None,
) -> None:
    """
    Configure console logging once for the StockBallDB process.

    Format includes timestamp, level, and message. Suitable for future
    pipeline messages (start, fetch, insert, validation, errors).

    When ``stream`` is provided, handlers are rebound to that stream so
    machine-readable CLI modes (e.g. ``update --json``) can keep stdout clean.
    """
    global _CONFIGURED
    if _CONFIGURED and stream is None:
        return

    handler = logging.StreamHandler(stream or sys.stdout)
    handler.setFormatter(logging.Formatter(DEFAULT_FORMAT, datefmt=DEFAULT_DATEFMT))

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    logging.getLogger("stockballdb").setLevel(level)
    _CONFIGURED = True


def get_logger(name: str = "stockballdb") -> logging.Logger:
    """Return a named logger, ensuring logging is configured."""
    configure_logging()
    return logging.getLogger(name)
