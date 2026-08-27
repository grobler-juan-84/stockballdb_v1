"""Canonical StockBallDB V1 full build orchestrator."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from stockballdb.config import ConfigError
from stockballdb.db import get_engine, reset_engine
from stockballdb.logging_config import configure_logging, get_logger
from stockballdb.v1.preflight import PreflightError, run_preflight
from stockballdb.v1.report import (
    print_final_status,
    print_header,
    print_stage,
    write_build_report,
)
from stockballdb.v1.stages import BUILD_STAGES, StageError, collect_diagnostics
from stockballdb.validate_v1 import ValidateV1Error, validate_v1_database


def _repo_root() -> Path:
    # src/stockballdb/build_v1.py -> repo root
    return Path(__file__).resolve().parents[2]


def run_build_v1(*, run_pytest: bool = True) -> int:
    """
    Execute the full V1 build pipeline. Returns process exit code.

    Fail-fast: stops at first stage failure; never reports V1 READY on partial.
    """
    configure_logging()
    logger = get_logger("stockballdb.build_v1")
    logger.info("StockBallDB starting build_v1")
    print_header()

    stage_log: list[tuple[str, str, str]] = []
    diagnostics: dict | None = None

    try:
        settings = run_preflight()
        print_stage("preflight", "PASS")
        stage_log.append(("preflight", "PASS", ""))
    except PreflightError as exc:
        print_stage("preflight", "FAIL")
        stage_log.append(("preflight", "FAIL", str(exc)))
        print_final_status(ready=False, failed_stage="preflight", reason=str(exc))
        write_build_report(
            status="PARTIAL",
            stages=stage_log,
            diagnostics=None,
            failed_stage="preflight",
            reason=str(exc),
        )
        logger.error("preflight failed: %s", exc)
        return 1

    for stage in BUILD_STAGES:
        try:
            detail = stage.run(settings)
            print_stage(stage.label, "PASS", detail)
            stage_log.append((stage.label, "PASS", detail))
            logger.info("stage %s PASS %s", stage.key, detail)
        except (StageError, ConfigError, Exception) as exc:
            print_stage(stage.label, "FAIL")
            stage_log.append((stage.label, "FAIL", str(exc)))
            print_final_status(
                ready=False, failed_stage=stage.label, reason=str(exc)
            )
            write_build_report(
                status="PARTIAL",
                stages=stage_log,
                diagnostics=None,
                failed_stage=stage.label,
                reason=str(exc),
            )
            logger.error("stage %s failed: %s", stage.key, exc)
            return 1

    try:
        reset_engine()
        engine = get_engine(settings)
        diag_lines = validate_v1_database(engine)
        diagnostics = collect_diagnostics(engine)
        print_stage("validate_v1", "PASS")
        stage_log.append(("validate_v1", "PASS", "; ".join(diag_lines[:4])))
    except ValidateV1Error as exc:
        print_stage("validate_v1", "FAIL")
        stage_log.append(("validate_v1", "FAIL", str(exc)))
        print_final_status(ready=False, failed_stage="validate_v1", reason=str(exc))
        write_build_report(
            status="PARTIAL",
            stages=stage_log,
            diagnostics=diagnostics,
            failed_stage="validate_v1",
            reason=str(exc),
        )
        logger.error("validate_v1 failed: %s", exc)
        return 1

    if run_pytest:
        repo = _repo_root()
        try:
            proc = subprocess.run(
                [sys.executable, "-m", "pytest", "-q", "--tb=line"],
                cwd=str(repo),
                check=False,
                capture_output=True,
                text=True,
            )
            if proc.returncode != 0:
                detail = ((proc.stdout or "") + (proc.stderr or ""))[-800:]
                print_stage("pytest", "FAIL")
                stage_log.append(("pytest", "FAIL", detail.strip()[:300]))
                print_final_status(
                    ready=False,
                    failed_stage="pytest",
                    reason=detail.strip()[:500],
                )
                write_build_report(
                    status="PARTIAL",
                    stages=stage_log,
                    diagnostics=diagnostics,
                    failed_stage="pytest",
                    reason=detail.strip()[:500],
                )
                logger.error("pytest failed")
                return 1
            print_stage("pytest", "PASS")
            stage_log.append(("pytest", "PASS", ""))
        except Exception as exc:
            print_stage("pytest", "FAIL")
            stage_log.append(("pytest", "FAIL", str(exc)))
            print_final_status(ready=False, failed_stage="pytest", reason=str(exc))
            write_build_report(
                status="PARTIAL",
                stages=stage_log,
                diagnostics=diagnostics,
                failed_stage="pytest",
                reason=str(exc),
            )
            return 1

    print_final_status(ready=True)
    report_path = write_build_report(
        status="V1 READY",
        stages=stage_log,
        diagnostics=diagnostics,
    )
    if report_path:
        print(f"report: {report_path}")
    logger.info("build_v1 COMPLETE V1 READY")
    return 0


def main() -> int:
    return run_build_v1(run_pytest=True)


if __name__ == "__main__":
    sys.exit(main())
