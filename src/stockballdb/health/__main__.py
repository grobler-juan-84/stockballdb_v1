"""CLI: python -m stockballdb.health"""

from __future__ import annotations

import argparse
import sys

from stockballdb.health.engine import run_health
from stockballdb.health.render import render_human, render_json


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="StockBallDB whole-database health check")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero on HEALTHY WITH WARNINGS",
    )
    args = parser.parse_args(argv)

    report = run_health()
    if args.json:
        sys.stdout.write(render_json(report))
    else:
        sys.stdout.write(render_human(report))

    return report.exit_code(strict=args.strict)


if __name__ == "__main__":
    sys.exit(main())
