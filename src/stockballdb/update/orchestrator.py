"""Operational update orchestration."""

from __future__ import annotations

import datetime as dt
import sys
import time
from dataclasses import dataclass
from typing import Any, TextIO

from sqlalchemy import text

from stockballdb.calendar.nyse import today_ny
from stockballdb.config import ConfigError, Settings, with_run_as_of
from stockballdb.db import get_engine, reset_engine
from stockballdb.fingerprint.compute import compute_database_fingerprint
from stockballdb.health.engine import run_health
from stockballdb.health.models import HealthStatus
from stockballdb.health.provenance import (
    MANIFEST_SCHEMA_1_1,
    git_provenance,
    manifest_from_health_report,
    write_build_manifest,
)
from stockballdb.logging_config import configure_logging, get_logger
from stockballdb.snapshots.context import (
    live_build_context,
    reset_context,
    snapshot_references,
)
from stockballdb.update.lock import AdvisoryLock
from stockballdb.update.preflight import UpdatePreflightError, run_update_preflight
from stockballdb.update.report import RunReport, StageRecord, new_run_id
from stockballdb.validate_v1 import ValidateV1Error, validate_v1_database
from stockballdb.v1.stages import StageError, UPDATE_STAGES


EXIT_SUCCESS = 0
EXIT_FAILED = 1
EXIT_PREFLIGHT = 2
EXIT_CONCURRENT = 3


@dataclass(frozen=True)
class UpdateResult:
    exit_code: int
    report: RunReport
    report_path: str | None = None
    manifest_path: str | None = None


def _emit(msg: str, *, stream: TextIO | None = None) -> None:
    target = stream if stream is not None else sys.stderr
    print(msg, file=target, flush=True)


def _pad(label: str, width: int = 28) -> str:
    dots = "." * max(2, width - len(label))
    return f"[{label}] {dots}"


def _print_stage(
    label: str,
    status: str,
    detail: str = "",
    *,
    stream: TextIO | None = None,
) -> None:
    line = f"{_pad(label)} {status}"
    if detail:
        line = f"{line}  {detail}"
    _emit(line, stream=stream)


def run_update(
    *,
    run_as_of: dt.date | None = None,
    json_output: bool = False,
) -> UpdateResult:
    """
    Execute the unified operational update workflow.

    Human progress logs go to stderr when ``json_output`` is True so stdout
    remains valid JSON.
    """
    configure_logging(stream=sys.stderr if json_output else None)
    logger = get_logger("stockballdb.update")
    log_stream = sys.stderr if json_output else sys.stdout

    started = dt.datetime.now(dt.timezone.utc)
    run_id = new_run_id(started)
    boundary = run_as_of or today_ny()
    command = "python -m stockballdb.update"

    report = RunReport(
        run_id=run_id,
        command=command,
        run_as_of=boundary.isoformat(),
        started_at=started,
        git=git_provenance(),
    )
    lock: AdvisoryLock | None = None
    settings: Settings | None = None
    snap_refs: list = []
    exit_code = EXIT_FAILED

    _emit("StockBallDB Update", stream=log_stream)
    _emit(f"Run: {run_id}", stream=log_stream)
    _emit(f"As of: {boundary.isoformat()}", stream=log_stream)
    _emit("", stream=log_stream)

    try:
        # --- preflight ---
        t0 = time.perf_counter()
        try:
            settings = run_update_preflight()
            settings = with_run_as_of(settings, boundary)
            reset_engine()
            engine = get_engine(settings)
            with engine.connect() as conn:
                report.alembic_head = conn.execute(
                    text("SELECT version_num FROM alembic_version")
                ).scalar_one()
        except UpdatePreflightError as exc:
            report.status = "FAILED"
            report.failure_kind = "FAILED_PRECHECK"
            report.failure_stage = "preflight"
            report.error = str(exc)
            report.stages.append(
                StageRecord(
                    name="preflight",
                    status="FAIL",
                    started_at=started.isoformat(),
                    finished_at=dt.datetime.now(dt.timezone.utc).isoformat(),
                    duration_ms=(time.perf_counter() - t0) * 1000,
                    error=str(exc),
                )
            )
            _print_stage("preflight", "FAIL", str(exc), stream=log_stream)
            exit_code = EXIT_PREFLIGHT
            return _finalize(report, exit_code, json_output, logger)

        report.stages.append(
            StageRecord(
                name="preflight",
                status="PASS",
                started_at=started.isoformat(),
                finished_at=dt.datetime.now(dt.timezone.utc).isoformat(),
                duration_ms=(time.perf_counter() - t0) * 1000,
            )
        )
        _print_stage("preflight", "PASS", stream=log_stream)

        assert settings is not None
        lock = AdvisoryLock(settings.database_url)

        # --- advisory lock ---
        t0 = time.perf_counter()
        if not lock.try_acquire():
            report.status = "FAILED"
            report.failure_kind = "FAILED_CONCURRENT"
            report.failure_stage = "lock"
            report.error = "another operational update is already running"
            report.stages.append(
                StageRecord(
                    name="lock",
                    status="FAIL",
                    started_at=dt.datetime.now(dt.timezone.utc).isoformat(),
                    finished_at=dt.datetime.now(dt.timezone.utc).isoformat(),
                    duration_ms=(time.perf_counter() - t0) * 1000,
                    error=report.error,
                )
            )
            _print_stage("lock", "FAIL", report.error, stream=log_stream)
            exit_code = EXIT_CONCURRENT
            return _finalize(report, exit_code, json_output, logger)

        report.stages.append(
            StageRecord(
                name="lock",
                status="PASS",
                started_at=dt.datetime.now(dt.timezone.utc).isoformat(),
                finished_at=dt.datetime.now(dt.timezone.utc).isoformat(),
                duration_ms=(time.perf_counter() - t0) * 1000,
            )
        )
        _print_stage("lock", "PASS", stream=log_stream)

        # --- fingerprint before ---
        t0 = time.perf_counter()
        reset_engine()
        engine = get_engine(settings)
        fp_before = compute_database_fingerprint(engine)
        report.fingerprint_before = fp_before.database_fingerprint
        report.stages.append(
            StageRecord(
                name="fingerprint_before",
                status="PASS",
                started_at=dt.datetime.now(dt.timezone.utc).isoformat(),
                finished_at=dt.datetime.now(dt.timezone.utc).isoformat(),
                duration_ms=(time.perf_counter() - t0) * 1000,
                detail=report.fingerprint_before,
            )
        )
        _print_stage("fingerprint_before", "PASS", stream=log_stream)

        # --- mutation stages with snapshot capture ---
        reset_context()
        stage_payload: list[dict[str, str]] = []
        try:
            with live_build_context():
                for stage in UPDATE_STAGES:
                    st_started = dt.datetime.now(dt.timezone.utc)
                    t_stage = time.perf_counter()
                    try:
                        detail = stage.run(settings)
                        st_finished = dt.datetime.now(dt.timezone.utc)
                        report.stages.append(
                            StageRecord(
                                name=stage.key,
                                status="PASS",
                                started_at=st_started.isoformat(),
                                finished_at=st_finished.isoformat(),
                                duration_ms=(time.perf_counter() - t_stage) * 1000,
                                detail=detail,
                            )
                        )
                        stage_payload.append(
                            {
                                "label": stage.label,
                                "status": "PASS",
                                "detail": detail,
                            }
                        )
                        _print_stage(stage.label, "PASS", detail, stream=log_stream)
                        logger.info("stage %s PASS %s", stage.key, detail)
                    except (StageError, ConfigError, Exception) as exc:
                        st_finished = dt.datetime.now(dt.timezone.utc)
                        msg = str(exc)
                        report.stages.append(
                            StageRecord(
                                name=stage.key,
                                status="FAIL",
                                started_at=st_started.isoformat(),
                                finished_at=st_finished.isoformat(),
                                duration_ms=(time.perf_counter() - t_stage) * 1000,
                                error=msg,
                            )
                        )
                        report.status = "FAILED"
                        report.failure_kind = "FAILED_STAGE"
                        report.failure_stage = stage.key
                        report.error = msg
                        _print_stage(stage.label, "FAIL", msg, stream=log_stream)
                        logger.error("stage %s failed: %s", stage.key, exc)
                        exit_code = EXIT_FAILED
                        return _finalize(report, exit_code, json_output, logger)
                snap_refs = snapshot_references()
        finally:
            reset_context()

        report.snapshot_count = len(snap_refs)

        # --- validate_v1 ---
        t0 = time.perf_counter()
        reset_engine()
        engine = get_engine(settings)
        try:
            validate_v1_database(engine)
            report.validation_result = "PASS"
            report.stages.append(
                StageRecord(
                    name="validate_v1",
                    status="PASS",
                    started_at=dt.datetime.now(dt.timezone.utc).isoformat(),
                    finished_at=dt.datetime.now(dt.timezone.utc).isoformat(),
                    duration_ms=(time.perf_counter() - t0) * 1000,
                )
            )
            stage_payload.append({"label": "validate_v1", "status": "PASS", "detail": ""})
            _print_stage("validate_v1", "PASS", stream=log_stream)
        except ValidateV1Error as exc:
            msg = str(exc)
            report.validation_result = "FAIL"
            report.status = "FAILED"
            report.failure_kind = "FAILED_VALIDATION"
            report.failure_stage = "validate_v1"
            report.error = msg
            report.stages.append(
                StageRecord(
                    name="validate_v1",
                    status="FAIL",
                    started_at=dt.datetime.now(dt.timezone.utc).isoformat(),
                    finished_at=dt.datetime.now(dt.timezone.utc).isoformat(),
                    duration_ms=(time.perf_counter() - t0) * 1000,
                    error=msg,
                )
            )
            _print_stage("validate_v1", "FAIL", msg, stream=log_stream)
            exit_code = EXIT_FAILED
            return _finalize(report, exit_code, json_output, logger)

        # --- health ---
        t0 = time.perf_counter()
        health_report = run_health(engine)
        report.health_status = health_report.status.value
        if health_report.status == HealthStatus.UNHEALTHY:
            msg = f"health status {health_report.status.value}"
            report.status = "FAILED"
            report.failure_kind = "FAILED_HEALTH"
            report.failure_stage = "health"
            report.error = msg
            report.stages.append(
                StageRecord(
                    name="health",
                    status="FAIL",
                    started_at=dt.datetime.now(dt.timezone.utc).isoformat(),
                    finished_at=dt.datetime.now(dt.timezone.utc).isoformat(),
                    duration_ms=(time.perf_counter() - t0) * 1000,
                    error=msg,
                )
            )
            _print_stage("health", "FAIL", msg, stream=log_stream)
            exit_code = EXIT_FAILED
            return _finalize(report, exit_code, json_output, logger)

        report.stages.append(
            StageRecord(
                name="health",
                status="PASS",
                started_at=dt.datetime.now(dt.timezone.utc).isoformat(),
                finished_at=dt.datetime.now(dt.timezone.utc).isoformat(),
                duration_ms=(time.perf_counter() - t0) * 1000,
                detail=health_report.status.value,
            )
        )
        stage_payload.append(
            {
                "label": "health",
                "status": "PASS",
                "detail": health_report.status.value,
            }
        )
        _print_stage("health", "PASS", health_report.status.value, stream=log_stream)

        # --- fingerprint after ---
        t0 = time.perf_counter()
        fp_after = compute_database_fingerprint(engine)
        report.fingerprint_after = fp_after.database_fingerprint
        report.stages.append(
            StageRecord(
                name="fingerprint_after",
                status="PASS",
                started_at=dt.datetime.now(dt.timezone.utc).isoformat(),
                finished_at=dt.datetime.now(dt.timezone.utc).isoformat(),
                duration_ms=(time.perf_counter() - t0) * 1000,
                detail=report.fingerprint_after,
            )
        )
        _print_stage("fingerprint_after", "PASS", stream=log_stream)

        if report.fingerprint_before == report.fingerprint_after:
            report.change_classification = "SUCCESS_NO_CHANGE"
            report.status = "SUCCESS_NO_CHANGE"
        else:
            report.change_classification = "SUCCESS_UPDATED"
            report.status = "SUCCESS_UPDATED"

        finished = dt.datetime.now(dt.timezone.utc)
        manifest_payload = manifest_from_health_report(
            health_report,
            command=command,
            started_at=started,
            finished_at=finished,
            success=True,
            stages=stage_payload,
            snapshots=snap_refs,
            database_fingerprint=fp_after,
            schema_version=MANIFEST_SCHEMA_1_1,
            build_id=run_id,
            run_as_of=boundary,
        )
        manifest_path = write_build_manifest(manifest_payload)
        if manifest_path:
            report.manifest_path = str(manifest_path)
            _emit(f"manifest: {manifest_path}", stream=log_stream)

        _emit("", stream=log_stream)
        _emit(f"Result: {report.status}", stream=log_stream)
        logger.info("update COMPLETE %s snapshots=%d", report.status, len(snap_refs))
        exit_code = EXIT_SUCCESS
        return _finalize(report, exit_code, json_output, logger)

    except Exception as exc:
        report.status = "FAILED"
        report.failure_kind = "FAILED_INTERNAL"
        report.error = str(exc)
        logger.exception("update internal failure")
        exit_code = EXIT_FAILED
        return _finalize(report, exit_code, json_output, logger)

    finally:
        if lock is not None:
            lock.release()


def _finalize(
    report: RunReport,
    exit_code: int,
    json_output: bool,
    logger: Any,
) -> UpdateResult:
    report.finished_at = dt.datetime.now(dt.timezone.utc)
    path = report.write()
    result = UpdateResult(
        exit_code=exit_code,
        report=report,
        report_path=str(path) if path else None,
        manifest_path=report.manifest_path,
    )
    if json_output:
        import json

        print(json.dumps(report.as_dict(), indent=2, sort_keys=True))
    if path:
        logger.info("run report: %s", path)
    return result
