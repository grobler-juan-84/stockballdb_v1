"""CLI: python -m stockballdb.snapshots verify [--manifest PATH]"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from stockballdb.snapshots.verify import load_manifest, verify_all_referenced, verify_manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify StockBallDB snapshot integrity")
    parser.add_argument(
        "--manifest",
        type=Path,
        help="Verify snapshots referenced by a specific manifest",
    )
    args = parser.parse_args(argv)

    started = time.perf_counter()
    if args.manifest:
        report = verify_manifest(load_manifest(args.manifest))
    else:
        report = verify_all_referenced()
    elapsed = time.perf_counter() - started

    print("StockBallDB Snapshot Verification")
    print("=================================")
    print(f"checked: {report.checked}")
    print(f"unique payloads: {report.unique_payloads}")
    print(f"missing: {report.missing}")
    print(f"corrupt: {report.corrupt}")
    print(f"invalid metadata: {report.invalid_metadata}")
    print(f"compressed bytes: {report.total_compressed_bytes}")
    print(f"uncompressed bytes: {report.total_uncompressed_bytes}")
    print(f"runtime: {elapsed:.2f}s")
    if report.errors:
        print("\nErrors:")
        for err in report.errors[:20]:
            print(f"  - {err}")
        if len(report.errors) > 20:
            print(f"  ... and {len(report.errors) - 20} more")
    status = "PASS" if report.ok else "FAIL"
    print(f"\nSTATUS: {status}")
    return report.exit_code()


if __name__ == "__main__":
    sys.exit(main())
