"""Standard library logging setup for StockBallDB."""

from __future__ import annotations

import logging
import sys

_CONFIGURED = False

DEFAULT_FORMAT = "%(asctime)s %(levelname)s %(message)s"
DEFAULT_DATEFMT = "%Y-%m-%d %H:%M:%S"


def configure_logging(level: int = logging.INFO) -> None:
    """
    Configure console logging once for the StockBallDB process.

    Format includes timestamp, level, and message. Suitable for future
    pipeline messages (start, fetch, insert, validation, errors).
    """
    global _CONFIGURED
    if _CONFIGURED:
        return

    handler = logging.StreamHandler(sys.stdout)
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
