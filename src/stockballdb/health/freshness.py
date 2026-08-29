"""Dataset-aware freshness evaluation."""

from __future__ import annotations

import datetime as dt

from sqlalchemy import text
from sqlalchemy.engine import Connection

from stockballdb.health.gaps import etf_freshness_result, wti_freshness_result
from stockballdb.health.limitations import (
    EVENT_FAMILY_FLOORS,
    MACRO_DAILY_STALE_SESSIONS,
    MACRO_FIELD_FLOORS,
    MACRO_MONTHLY_STALE_SESSIONS,
    MACRO_MONTHLY_FIELDS,
    MACRO_WEEKLY_FIELDS,
    MACRO_WEEKLY_STALE_SESSIONS,
    SPINE_LAG_WARNING,
    event_type_list,
)
from stockballdb.health.models import (
    Finding,
    FreshnessClass,
    FreshnessResult,
    MissingnessClass,
    Severity,
)
from stockballdb.market_data.universe import CLOSE_ONLY_SYMBOLS


def _sessions_between(conn: Connection, after: dt.date, through: dt.date) -> int:
    if after >= through:
        return 0
    return conn.execute(
        text(
            """
            SELECT COUNT(*) FROM trading_days
            WHERE date > :after AND date <= :through
            """
        ),
        {"after": after, "through": through},
    ).scalar_one()


def collect_freshness(conn: Connection) -> tuple[list[FreshnessResult], list[Finding]]:
    results: list[FreshnessResult] = []
    findings: list[Finding] = []

    spine_max = conn.execute(text("SELECT MAX(date) FROM trading_days")).scalar_one()
    etf_max = conn.execute(
        text(
            """
            SELECT MAX(date) FROM daily_market_data
            WHERE symbol <> ALL(:close_only)
            """
        ),
        {"close_only": list(CLOSE_ONLY_SYMBOLS)},
    ).scalar_one()
    wti_max = conn.execute(
        text(
            """
            SELECT MAX(date) FROM daily_market_data
            WHERE symbol = ANY(:close_only)
            """
        ),
        {"close_only": list(CLOSE_ONLY_SYMBOLS)},
    ).scalar_one()
    macro_max = conn.execute(text("SELECT MAX(date) FROM macro_conditions")).scalar_one()
    cal_max = conn.execute(text("SELECT MAX(date) FROM calendar_context")).scalar_one()
    events_max = conn.execute(
        text("SELECT MAX(event_date) FROM scheduled_events")
    ).scalar_one()

    etf_lag = _sessions_between(conn, etf_max, spine_max) if etf_max and spine_max else 0
    etf_fr = etf_freshness_result(
        etf_max=etf_max.isoformat() if etf_max else None,
        spine_max=spine_max.isoformat() if spine_max else "",
        lag_sessions=etf_lag,
    )
    results.append(etf_fr)
    if etf_fr.severity == Severity.INFO:
        findings.append(
            Finding(
                severity=Severity.INFO,
                code="ETF_EXPECTED_LAG",
                dataset="etf_market_data",
                message=f"ETF data lags spine by {etf_lag} trading session(s)",
                details={
                    "latest_observation": etf_fr.latest_observation,
                    "freshness_anchor": etf_fr.freshness_anchor,
                    "lag_sessions": etf_lag,
                    "missingness": MissingnessClass.EXPECTED_LAG.value,
                },
            )
        )
    elif etf_fr.severity in (Severity.WARNING, Severity.ERROR):
        findings.append(
            Finding(
                severity=etf_fr.severity,
                code="ETF_STALE",
                dataset="etf_market_data",
                message=f"ETF data lags spine by {etf_lag} trading session(s)",
                details={"lag_sessions": etf_lag},
            )
        )

    wti_anchor = etf_max or spine_max
    wti_lag = (
        _sessions_between(conn, wti_max, wti_anchor)
        if wti_max and wti_anchor
        else 0
    )
    wti_fr = wti_freshness_result(
        wti_max=wti_max.isoformat() if wti_max else None,
        anchor=wti_anchor.isoformat() if wti_anchor else "",
        lag_sessions=wti_lag,
    )
    results.append(wti_fr)
    if wti_fr.severity == Severity.INFO:
        findings.append(
            Finding(
                severity=Severity.INFO,
                code="WTI_EXPECTED_LAG",
                dataset="wti_market_data",
                message=f"WTI lags market anchor by {wti_lag} trading session(s)",
                details={
                    "missingness": MissingnessClass.EXPECTED_LAG.value,
                    "lag_sessions": wti_lag,
                },
            )
        )
    elif wti_fr.severity in (Severity.WARNING, Severity.ERROR):
        findings.append(
            Finding(
                severity=wti_fr.severity,
                code="WTI_STALE",
                dataset="wti_market_data",
                message=f"WTI lags anchor by {wti_lag} session(s)",
                details={"lag_sessions": wti_lag},
            )
        )

    if macro_max != spine_max:
        findings.append(
            Finding(
                severity=Severity.ERROR,
                code="MACRO_SPINE_MISMATCH",
                dataset="macro_conditions",
                message=f"macro max {macro_max} != spine max {spine_max}",
                details={},
            )
        )
    results.append(
        FreshnessResult(
            dataset="macro_conditions_row",
            latest_observation=macro_max.isoformat() if macro_max else None,
            freshness_anchor=spine_max.isoformat() if spine_max else None,
            lag_sessions=0 if macro_max == spine_max else None,
            classification=FreshnessClass.CURRENT
            if macro_max == spine_max
            else FreshnessClass.STALE,
            severity=Severity.PASS if macro_max == spine_max else Severity.ERROR,
        )
    )

    if cal_max != spine_max:
        findings.append(
            Finding(
                severity=Severity.ERROR,
                code="CALENDAR_SPINE_MISMATCH",
                dataset="calendar_context",
                message=f"calendar max {cal_max} != spine max {spine_max}",
                details={},
            )
        )
    results.append(
        FreshnessResult(
            dataset="calendar_context",
            latest_observation=cal_max.isoformat() if cal_max else None,
            freshness_anchor=spine_max.isoformat() if spine_max else None,
            lag_sessions=0 if cal_max == spine_max else None,
            classification=FreshnessClass.CURRENT
            if cal_max == spine_max
            else FreshnessClass.STALE,
            severity=Severity.PASS if cal_max == spine_max else Severity.ERROR,
        )
    )

    for field, floor in MACRO_FIELD_FLOORS.items():
        row = conn.execute(
            text(
                f"""
                SELECT MAX(date) FILTER (WHERE {field} IS NOT NULL) AS last_nn
                FROM macro_conditions
                """
            )
        ).one()
        last_nn = row[0]
        if last_nn is None:
            continue
        lag = _sessions_between(conn, last_nn, spine_max) if spine_max else 0
        if field in MACRO_MONTHLY_FIELDS:
            stale_limit = MACRO_MONTHLY_STALE_SESSIONS
        elif field in MACRO_WEEKLY_FIELDS:
            stale_limit = MACRO_WEEKLY_STALE_SESSIONS
        else:
            stale_limit = MACRO_DAILY_STALE_SESSIONS
        if lag <= 3:
            cls, sev = FreshnessClass.CURRENT, Severity.PASS
        elif lag <= stale_limit:
            cls, sev = FreshnessClass.EXPECTED_LAG, Severity.INFO
        else:
            cls, sev = FreshnessClass.STALE, Severity.WARNING
        results.append(
            FreshnessResult(
                dataset=f"macro.{field}",
                latest_observation=last_nn.isoformat(),
                freshness_anchor=spine_max.isoformat() if spine_max else None,
                lag_sessions=lag,
                classification=cls,
                severity=sev,
                missingness=MissingnessClass.NOT_YET_PUBLISHED if lag > 3 else None,
            )
        )

    for etype in event_type_list():
        last_ev = conn.execute(
            text(
                """
                SELECT MAX(event_date) FROM scheduled_events WHERE event_type = :t
                """
            ),
            {"t": etype},
        ).scalar_one()
        results.append(
            FreshnessResult(
                dataset=f"scheduled_events.{etype}",
                latest_observation=last_ev.isoformat() if last_ev else None,
                freshness_anchor=spine_max.isoformat() if spine_max else None,
                lag_sessions=None,
                classification=FreshnessClass.UNKNOWN,
                severity=Severity.PASS,
                missingness=MissingnessClass.NOT_APPLICABLE,
            )
        )

    results.append(
        FreshnessResult(
            dataset="scheduled_events",
            latest_observation=events_max.isoformat() if events_max else None,
            freshness_anchor=spine_max.isoformat() if spine_max else None,
            lag_sessions=None,
            classification=FreshnessClass.UNKNOWN,
            severity=Severity.PASS,
        )
    )

    return results, findings
