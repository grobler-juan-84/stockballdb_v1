"""CLI: ``python -m stockballdb.api`` — start localhost FastAPI transport."""

from __future__ import annotations

import argparse
import sys

import uvicorn

from stockballdb.api.settings import api_host, api_port
from stockballdb.logging_config import configure_logging, get_logger


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run StockBallDB localhost-only FastAPI read transport (V2)."
    )
    parser.add_argument(
        "--host",
        default=None,
        help="Bind host (default: 127.0.0.1 / STOCKBALLDB_API_HOST).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Bind port (default: 8765 / STOCKBALLDB_API_PORT).",
    )
    args = parser.parse_args(argv)

    configure_logging()
    logger = get_logger("stockballdb.api")
    host = args.host or api_host()
    port = args.port if args.port is not None else api_port()

    if host not in {"127.0.0.1", "localhost", "::1"}:
        logger.warning(
            "binding to %s — production V2 expects loopback only (127.0.0.1)",
            host,
        )

    logger.info("starting StockBallDB API on http://%s:%s", host, port)
    uvicorn.run(
        "stockballdb.api.app:create_app",
        factory=True,
        host=host,
        port=port,
        log_level="info",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
