"""Market-data active-span gap detection and findings."""

from __future__ import annotations

from stockballdb.health.limitations import (
    ETF_CONSECUTIVE_GAP_ERROR,
    ETF_LAG_INFO_MAX,
    ETF_LAG_WARNING_MAX,
    WTI_LAG_INFO_MAX,
    WTI_LAG_WARNING_MAX,
)
from stockballdb.health.models import (
    Finding,
    FreshnessClass,
    FreshnessResult,
    MissingnessClass,
    Severity,
    SymbolCoverage,
)
from stockballdb.market_data.universe import CLOSE_ONLY_SYMBOLS, PHASE_2A_ETF_SYMBOLS


def gap_findings(symbols: list[SymbolCoverage]) -> list[Finding]:
    findings: list[Finding] = []
    for s in symbols:
        if s.internal_missing_sessions == 0:
            continue
        missingness = (
            MissingnessClass.EXPECTED_PROVIDER_GAP
            if s.symbol in CLOSE_ONLY_SYMBOLS
            else MissingnessClass.UNEXPECTED_GAP
        )
        if s.symbol in CLOSE_ONLY_SYMBOLS:
            sev = Severity.INFO
            code = "WTI_PROVIDER_GAP"
        elif s.max_consecutive_missing >= ETF_CONSECUTIVE_GAP_ERROR:
            sev = Severity.ERROR
            code = "MARKET_INTERNAL_GAP"
            missingness = MissingnessClass.UNEXPECTED_GAP
        elif s.max_consecutive_missing >= ETF_LAG_WARNING_MAX:
            sev = Severity.WARNING
            code = "MARKET_INTERNAL_GAP"
        else:
            sev = Severity.INFO if s.internal_missing_sessions <= 3 else Severity.WARNING
            code = "MARKET_INTERNAL_GAP"
        findings.append(
            Finding(
                severity=sev,
                code=code,
                dataset=f"daily_market_data.{s.symbol}",
                message=(
                    f"{s.symbol} missing {s.internal_missing_sessions} sessions in active span "
                    f"({s.first_date}..{s.last_date}); max consecutive={s.max_consecutive_missing}"
                ),
                details={
                    "missingness": missingness.value,
                    "sample_missing_dates": s.sample_missing_dates,
                    "coverage_pct": s.coverage_pct,
                },
            )
        )
    return findings


def session_lag(anchor: str, latest: str, lag: int) -> tuple[Severity, FreshnessClass]:
    """Map session lag to severity for ETF/WTI."""
    if lag <= 0:
        return Severity.PASS, FreshnessClass.CURRENT
    if lag <= ETF_LAG_INFO_MAX:
        return Severity.INFO, FreshnessClass.EXPECTED_LAG
    if lag <= ETF_LAG_WARNING_MAX:
        return Severity.WARNING, FreshnessClass.STALE
    return Severity.ERROR, FreshnessClass.STALE


def wti_session_lag(lag: int) -> tuple[Severity, FreshnessClass]:
    if lag <= 0:
        return Severity.PASS, FreshnessClass.CURRENT
    if lag <= WTI_LAG_INFO_MAX:
        return Severity.INFO, FreshnessClass.EXPECTED_LAG
    if lag <= WTI_LAG_WARNING_MAX:
        return Severity.WARNING, FreshnessClass.STALE
    return Severity.ERROR, FreshnessClass.STALE


def etf_freshness_result(
    *,
    etf_max: str | None,
    spine_max: str,
    lag_sessions: int,
) -> FreshnessResult:
    sev, cls = session_lag("trading_days", etf_max or "", lag_sessions)
    missingness = MissingnessClass.EXPECTED_LAG if lag_sessions > 0 else None
    return FreshnessResult(
        dataset="etf_market_data",
        latest_observation=etf_max,
        freshness_anchor=spine_max,
        lag_sessions=lag_sessions,
        classification=cls,
        severity=sev if sev != Severity.PASS else Severity.PASS,
        missingness=missingness,
    )


def wti_freshness_result(
    *,
    wti_max: str | None,
    anchor: str,
    lag_sessions: int,
) -> FreshnessResult:
    sev, cls = wti_session_lag(lag_sessions)
    return FreshnessResult(
        dataset="wti_market_data",
        latest_observation=wti_max,
        freshness_anchor=anchor,
        lag_sessions=lag_sessions,
        classification=cls,
        severity=sev if sev != Severity.PASS else Severity.PASS,
        missingness=MissingnessClass.EXPECTED_LAG if lag_sessions > 0 else None,
    )
