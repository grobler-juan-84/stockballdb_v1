"""Exact rebuild from immutable snapshots (offline)."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from stockballdb.config import ConfigError, Settings, load_settings
from stockballdb.db import get_engine, reset_engine
from stockballdb.fingerprint.compute import compute_database_fingerprint
from stockballdb.health.engine import run_health
from stockballdb.health.provenance import (
    MANIFEST_SCHEMA_1_1,
    classify_manifest,
    git_provenance,
    repo_root,
)
from stockballdb.rebuild.truncate import truncate_canonical_tables
from stockballdb.snapshots.context import reset_context, snapshot_replay_context
from stockballdb.snapshots.verify import load_manifest, verify_manifest
from stockballdb.validate_v1 import ValidateV1Error, validate_v1_database
from stockballdb.v1.preflight import V1_ALEMBIC_HEAD
from stockballdb.v1.stages import BUILD_STAGES, StageError, collect_diagnostics


class RebuildExactError(Exception):
    """Exact rebuild cannot proceed."""


@dataclass
class RebuildExactReport:
    manifest_path: str
    build_id: str
    source_mode: str = "snapshot"
    snapshot_count: int = 0
    snapshot_verification: str = "UNKNOWN"
    git_compatible: bool = False
    alembic_compatible: bool = False
    dirty_refused: bool = False
    validation_result: str = "UNKNOWN"
    health_status: str | None = None
    expected_fingerprint: str | None = None
    actual_fingerprint: str | None = None
    fingerprint_match: bool = False
    table_comparisons: list[dict[str, Any]] = field(default_factory=list)
    elapsed_ms: float = 0.0
    status: str = "FAIL"
    network_forbidden: bool = True
    errors: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "manifest_path": self.manifest_path,
            "build_id": self.build_id,
            "source_mode": self.source_mode,
            "snapshot_count": self.snapshot_count,
            "snapshot_verification": self.snapshot_verification,
            "git_compatible": self.git_compatible,
            "alembic_compatible": self.alembic_compatible,
            "validation_result": self.validation_result,
            "health_status": self.health_status,
            "expected_fingerprint": self.expected_fingerprint,
            "actual_fingerprint": self.actual_fingerprint,
            "fingerprint_match": self.fingerprint_match,
            "table_comparisons": self.table_comparisons,
            "elapsed_ms": self.elapsed_ms,
            "status": self.status,
            "errors": self.errors,
        }


def _current_git_commit() -> str | None:
    git = git_provenance()
    return git.get("commit") if git.get("available") else None


def validate_manifest_for_exact_rebuild(manifest: dict[str, Any]) -> None:
    schema = manifest.get("schema_version", "1.0")
    if schema != MANIFEST_SCHEMA_1_1:
        raise RebuildExactError(
            "Manifest predates snapshot capture and cannot support exact rebuild."
        )
    flags = classify_manifest(manifest)
    if not flags["exact_rebuild_capable"]:
        raise RebuildExactError(
            "Manifest is not exact-rebuild-capable (snapshot_capture=false or incomplete)."
        )
    if not manifest.get("database_fingerprint"):
        raise RebuildExactError("Manifest missing database_fingerprint.")
    snapshots = manifest.get("snapshots") or []
    if not snapshots:
        raise RebuildExactError("Manifest has no snapshot references.")


def check_git_guard(manifest: dict[str, Any], *, allow_dirty: bool = False) -> None:
    manifest_git = manifest.get("git") or {}
    required = manifest_git.get("commit")
    if not required:
        raise RebuildExactError("Manifest missing git commit for exact rebuild.")
    current = _current_git_commit()
    if current != required:
        raise RebuildExactError(
            f"Git commit mismatch: manifest={required[:12]} current={current[:12] if current else 'none'}. "
            "Checkout the manifest commit before REBUILD EXACT."
        )
    if manifest_git.get("dirty") and not allow_dirty:
        raise RebuildExactError(
            "Manifest was built from a dirty working tree; exact rebuild refused."
        )
    current_git = git_provenance()
    if current_git.get("dirty") and not allow_dirty:
        raise RebuildExactError(
            "Current working tree is dirty; exact rebuild refused."
        )


def check_alembic_guard(manifest: dict[str, Any]) -> None:
    required = manifest.get("alembic_head") or manifest.get("expected_alembic_head")
    if required != V1_ALEMBIC_HEAD:
        raise RebuildExactError(
            f"Manifest Alembic revision {required} != expected {V1_ALEMBIC_HEAD}"
        )


def _settings_for_url(database_url: str) -> Settings:
    base = load_settings(require_database_url=False)
    return Settings(
        database_url=database_url,
        tiingo_api_key=base.tiingo_api_key or "offline-placeholder",
        fred_api_key=base.fred_api_key or "offline-placeholder",
        eia_api_key=base.eia_api_key,
    )


def run_rebuild_exact(
    manifest_path: Path,
    *,
    database_url: str,
    allow_dirty: bool = False,
    skip_truncate: bool = False,
) -> RebuildExactReport:
    started = time.perf_counter()
    manifest = load_manifest(manifest_path)
    report = RebuildExactReport(
        manifest_path=str(manifest_path),
        build_id=manifest.get("build_id", "unknown"),
        snapshot_count=len(manifest.get("snapshots") or []),
        expected_fingerprint=manifest.get("database_fingerprint"),
    )

    try:
        validate_manifest_for_exact_rebuild(manifest)
        verify = verify_manifest(manifest)
        report.snapshot_verification = "PASS" if verify.ok else "FAIL"
        if not verify.ok:
            raise RebuildExactError(
                f"Snapshot verification failed: {verify.errors[:3]}"
            )

        check_git_guard(manifest, allow_dirty=allow_dirty)
        report.git_compatible = True
        check_alembic_guard(manifest)
        report.alembic_compatible = True

        settings = _settings_for_url(database_url)
        reset_context()
        with snapshot_replay_context(manifest.get("snapshots") or []):
            reset_engine()
            engine = get_engine(settings)
            if not skip_truncate:
                truncate_canonical_tables(engine)

            for stage in BUILD_STAGES:
                try:
                    stage.run(settings)
                except (StageError, ConfigError, Exception) as exc:
                    raise RebuildExactError(f"stage {stage.key} failed: {exc}") from exc

            validate_v1_database(engine)
            report.validation_result = "PASS"
            health = run_health(engine)
            report.health_status = health.status.value

            actual = compute_database_fingerprint(engine)
            report.actual_fingerprint = actual.database_fingerprint
            expected_tables = {
                t["table"]: t for t in manifest.get("table_fingerprints") or []
            }
            for tf in actual.table_fingerprints:
                exp = expected_tables.get(tf.table, {})
                match = exp.get("sha256") == tf.sha256
                report.table_comparisons.append(
                    {
                        "table": tf.table,
                        "expected": exp.get("sha256"),
                        "actual": tf.sha256,
                        "match": match,
                    }
                )
            report.fingerprint_match = (
                report.actual_fingerprint == report.expected_fingerprint
            )
            if not report.fingerprint_match:
                raise RebuildExactError("Database fingerprint mismatch after rebuild.")

        report.status = "PASS"
    except RebuildExactError as exc:
        report.errors.append(str(exc))
        report.status = "FAIL"
    finally:
        reset_context()
        report.elapsed_ms = (time.perf_counter() - started) * 1000

    return report


def _resolve_database_url(args: argparse.Namespace) -> str:
    url = args.database_url or os.getenv("STOCKBALLDB_REBUILD_DATABASE_URL", "").strip()
    if not url:
        url = os.getenv("DATABASE_URL", "").strip()
        if url and not args.force_same_database:
            raise RebuildExactError(
                "Refusing to rebuild into DATABASE_URL without --force-same-database. "
                "Set STOCKBALLDB_REBUILD_DATABASE_URL or pass --database-url."
            )
    if not url:
        raise RebuildExactError("No rebuild database URL provided.")
    return url


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="StockBallDB exact rebuild from snapshots")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--database-url", type=str, default=None)
    parser.add_argument(
        "--force-same-database",
        action="store_true",
        help="Allow rebuilding into DATABASE_URL (destructive)",
    )
    parser.add_argument(
        "--allow-dirty",
        action="store_true",
        help="Allow rebuild with dirty Git (non-certified)",
    )
    parser.add_argument("--report", type=Path, help="Write JSON rebuild report")
    args = parser.parse_args(argv)

    try:
        db_url = _resolve_database_url(args)
        report = run_rebuild_exact(
            args.manifest,
            database_url=db_url,
            allow_dirty=args.allow_dirty,
        )
    except RebuildExactError as exc:
        print(f"REBUILD EXACT FAIL: {exc}", file=sys.stderr)
        return 1

    print("StockBallDB Rebuild Exact")
    print("=========================")
    print(f"manifest: {report.manifest_path}")
    print(f"build_id: {report.build_id}")
    print(f"snapshots: {report.snapshot_count}")
    print(f"snapshot verification: {report.snapshot_verification}")
    print(f"validate_v1: {report.validation_result}")
    print(f"health: {report.health_status}")
    print(f"expected fingerprint: {report.expected_fingerprint}")
    print(f"actual fingerprint: {report.actual_fingerprint}")
    print(f"fingerprint match: {report.fingerprint_match}")
    print(f"runtime: {report.elapsed_ms:.0f} ms")
    print(f"STATUS: {report.status}")

    if args.report:
        args.report.write_text(
            json.dumps(report.as_dict(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    return 0 if report.status == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
