"""Human-readable and JSON health report rendering."""

from __future__ import annotations

import json
from typing import Any

from stockballdb.health.models import HealthReport, Severity


def report_to_dict(report: HealthReport) -> dict[str, Any]:
    counts = report.finding_counts()
    return {
        "status": report.status.value,
        "generated_at": report.generated_at.isoformat(),
        "runtime_ms": round(report.runtime_ms, 2),
        "database": {
            "connected": report.database_connected,
            "alembic_head": report.alembic_head,
            "expected_alembic_head": report.expected_alembic_head,
            "calendar_version": report.calendar_version,
        },
        "migration": {
            "alembic_head": report.alembic_head,
            "expected": report.expected_alembic_head,
            "match": report.alembic_head == report.expected_alembic_head,
        },
        "coverage": {
            "tables": [
                {
                    "table": t.table,
                    "grain": t.grain,
                    "row_count": t.row_count,
                    "first_date": t.first_date.isoformat() if t.first_date else None,
                    "last_date": t.last_date.isoformat() if t.last_date else None,
                }
                for t in report.tables
            ],
            "symbols": [
                {
                    "symbol": s.symbol,
                    "asset_type": s.asset_type,
                    "first_date": s.first_date.isoformat(),
                    "last_date": s.last_date.isoformat(),
                    "row_count": s.row_count,
                    "eligible_sessions": s.eligible_sessions,
                    "coverage_pct": s.coverage_pct,
                    "internal_missing_sessions": s.internal_missing_sessions,
                    "max_consecutive_missing": s.max_consecutive_missing,
                    "sample_missing_dates": s.sample_missing_dates,
                }
                for s in report.symbols
            ],
        },
        "freshness": [
            {
                "dataset": f.dataset,
                "latest_observation": f.latest_observation,
                "freshness_anchor": f.freshness_anchor,
                "lag_sessions": f.lag_sessions,
                "classification": f.classification.value,
                "severity": f.severity.value,
                "missingness": f.missingness.value if f.missingness else None,
            }
            for f in report.freshness
        ],
        "provenance": report.provenance,
        "integrity": report.integrity,
        "findings": [
            {
                "severity": f.severity.value,
                "code": f.code,
                "dataset": f.dataset,
                "message": f.message,
                "details": f.details,
            }
            for f in report.findings
            if f.severity != Severity.PASS
        ],
        "finding_counts": counts,
        "validate_v1_pass": report.validate_v1_pass,
    }


def render_json(report: HealthReport) -> str:
    return json.dumps(report_to_dict(report), indent=2, sort_keys=True) + "\n"


def render_human(report: HealthReport) -> str:
    lines = [
        "StockBallDB Health",
        "==================",
        "",
        f"STATUS: {report.status.value}",
        f"Generated: {report.generated_at.isoformat()}  ({report.runtime_ms:.0f} ms)",
        "",
        "Database",
        "--------",
        f"  connected: {report.database_connected}",
        f"  alembic: {report.alembic_head} (expected {report.expected_alembic_head})",
        f"  calendar: pandas_market_calendars {report.calendar_version}",
        f"  validate_v1: {'PASS' if report.validate_v1_pass else 'FAIL'}",
        "",
        "Coverage",
        "--------",
    ]
    for t in report.tables:
        lines.append(
            f"  {t.table}: rows={t.row_count} {t.first_date} -> {t.last_date} ({t.grain.replace(chr(0xD7), 'x')})"
        )
    lines.extend(["", "Market symbols", "--------------"])
    for s in report.symbols:
        gap_note = ""
        if s.internal_missing_sessions:
            gap_note = f" gaps={s.internal_missing_sessions} max_run={s.max_consecutive_missing}"
        lines.append(
            f"  {s.symbol} ({s.asset_type}): {s.row_count} rows "
            f"{s.first_date}->{s.last_date} cov={s.coverage_pct}%{gap_note}"
        )

    lines.extend(["", "Freshness", "---------"])
    for f in report.freshness:
        if f.dataset.startswith("macro.") and f.severity == Severity.PASS:
            continue
        if f.classification.value == "UNKNOWN" and f.dataset.startswith("scheduled_events."):
            continue
        lag = f" lag={f.lag_sessions}" if f.lag_sessions is not None else ""
        lines.append(
            f"  {f.severity.value:7} {f.dataset}: {f.classification.value}{lag}"
        )

    lines.extend(["", "Integrity", "---------"])
    for k, v in report.integrity.items():
        lines.append(f"  {k}: {v}")

    counts = report.finding_counts()
    lines.extend(
        [
            "",
            "Findings",
            "--------",
            f"  INFO: {counts.get('INFO', 0)}",
            f"  WARNING: {counts.get('WARNING', 0)}",
            f"  ERROR: {counts.get('ERROR', 0)}",
            f"  FATAL: {counts.get('FATAL', 0)}",
        ]
    )
    for f in report.findings:
        if f.severity in (Severity.INFO, Severity.WARNING, Severity.ERROR, Severity.FATAL):
            lines.append(f"  {f.severity.value} {f.code} [{f.dataset}] {f.message}")

    if report.provenance.get("git"):
        g = report.provenance["git"]
        if g.get("available"):
            lines.extend(
                [
                    "",
                    "Provenance",
                    "----------",
                    f"  git commit: {g.get('commit', 'n/a')[:12]} dirty={g.get('dirty')}",
                ]
            )

    lines.append("")
    return "\n".join(lines)
