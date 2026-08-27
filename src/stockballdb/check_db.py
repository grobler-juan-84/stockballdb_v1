"""Independent database connectivity check for StockBallDB Phase 0."""

from __future__ import annotations

import re
import sys

from stockballdb.config import ConfigError, load_settings
from stockballdb.db import check_connection, reset_engine
from stockballdb.logging_config import configure_logging, get_logger


def _sanitize_error(message: str) -> str:
    """Strip likely password material from connection error text."""
    # postgresql+psycopg://user:password@host → redact password segment
    sanitized = re.sub(
        r"(postgresql(?:\+\w+)?://[^:/@]+):([^@/]+)@",
        r"\1:***@",
        message,
        flags=re.IGNORECASE,
    )
    return sanitized


def main() -> int:
    configure_logging()
    logger = get_logger("stockballdb.check_db")
    logger.info("StockBallDB starting database connectivity check")

    try:
        settings = load_settings(require_database_url=True)
        reset_engine()
        check_connection(settings)
    except ConfigError as exc:
        print("FAILURE")
        print("Database connection failed.")
        print(str(exc))
        logger.error("Database connection failed: %s", exc)
        return 1
    except Exception as exc:
        detail = _sanitize_error(str(exc))
        print("FAILURE")
        print("Database connection failed.")
        print(detail)
        logger.error("Database connection failed: %s", detail)
        return 1

    print("SUCCESS")
    print("Database connection established.")
    logger.info("database connection successful")
    return 0


if __name__ == "__main__":
    sys.exit(main())
