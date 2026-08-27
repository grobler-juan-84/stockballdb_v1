"""Console / optional file reporting for V1 builds."""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import pandas_market_calendars as mcal

from stockballdb import __version__
from stockballdb.market_data.universe import PHASE_2A_ETF_SYMBOLS
from stockballdb.v1.preflight import REQUIRED_CALENDAR_VERSION, V1_ALEMBIC_HEAD


def _pad(label: str, width: int = 28) -> str:
    dots = "." * max(2, width - len(label))
    return f"[{label}] {dots}"


def print_header() -> None:
    print("StockBallDB V1 Build", flush=True)
    print(flush=True)


def print_stage(label: str, status: str, detail: str = "") -> None:
    line = f"{_pad(label)} {status}"
    if detail:
        line = f"{line}  {detail}"
    print(line, flush=True)


def print_final_status(
    *,
    ready: bool,
    failed_stage: str | None = None,
    reason: str | None = None,
) -> None:
    print(flush=True)
    if ready:
        print("STATUS: V1 READY", flush=True)
        return
    print("STATUS: PARTIAL", flush=True)
    if failed_stage:
        print(f"FAILED STAGE: {failed_stage}", flush=True)
    if reason:
        print(f"REASON: {reason}", flush=True)


def write_build_report(
    *,
    status: str,
    stages: list[tuple[str, str, str]],
    diagnostics: dict | None,
    failed_stage: str | None = None,
    reason: str | None = None,
    reports_dir: Path | None = None,
) -> Path | None:
    """Write an optional text report under build_reports/ (gitignored)."""
    root = Path(__file__).resolve().parents[3]
    out_dir = reports_dir or (root / "build_reports")
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        return None

    ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    path = out_dir / f"v1_{ts}.txt"
    lines = [
        f"StockBallDB V1 build report — {ts}",
        f"package_version={__version__}",
        f"calendar=pandas_market_calendars=={mcal.__version__} "
        f"(required {REQUIRED_CALENDAR_VERSION})",
        f"expected_alembic_head={V1_ALEMBIC_HEAD}",
        f"universe={','.join(PHASE_2A_ETF_SYMBOLS)}",
        f"status={status}",
    ]
    if failed_stage:
        lines.append(f"failed_stage={failed_stage}")
    if reason:
        lines.append(f"reason={reason}")
    lines.append("stages:")
    for label, st, detail in stages:
        lines.append(f"  {label}: {st} {detail}".rstrip())
    if diagnostics:
        lines.append("diagnostics:")
        for k, v in diagnostics.items():
            lines.append(f"  {k}={v}")
    lines.append("")
    lines.append(
        "Reproducibility: structural=YES; current-source rebuild=YES; "
        "exact snapshot=NO (live providers; no durable raw archive)."
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
