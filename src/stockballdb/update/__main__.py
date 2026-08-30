"""CLI entry point for operational update."""

from __future__ import annotations

import argparse
import datetime as dt
import sys

from stockballdb.update.orchestrator import run_update


def _parse_as_of(value: str) -> dt.date:
    try:
        return dt.date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"invalid --as-of date {value!r}; expected YYYY-MM-DD"
        ) from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the StockBallDB unified operational update workflow.",
    )
    parser.add_argument(
        "--as-of",
        type=_parse_as_of,
        metavar="YYYY-MM-DD",
        help="Deterministic build boundary (default: today in America/New_York).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Write machine-readable JSON result to stdout; progress logs go to stderr.",
    )
    args = parser.parse_args(argv)
    result = run_update(run_as_of=args.as_of, json_output=args.json)
    return result.exit_code


if __name__ == "__main__":
    sys.exit(main())
