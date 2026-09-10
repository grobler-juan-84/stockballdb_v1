"""Coverage Explorer service — wraps Phase 8 health coverage."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.engine import Connection

from stockballdb.health.coverage import collect_symbol_coverage, collect_table_coverage, load_trading_days
from stockballdb.health.freshness import collect_freshness
from stockballdb.health.gaps import gap_findings
from stockballdb.health.limitations import EXPECTED_LIMITATIONS, UNRESOLVED_MACRO, UNRESOLVED_SYMBOLS
from stockballdb.health.models import Finding, FreshnessResult, SymbolCoverage, TableCoverage


@dataclass
class CoverageSnapshot:
    tables: list[TableCoverage]
    symbols: list[SymbolCoverage]
    freshness: list[FreshnessResult]
    gap_findings: list[Finding]
    limitations: tuple[str, ...]
    unresolved_symbols: tuple[str, ...]
    unresolved_macro: tuple[str, ...]


def load_coverage(conn: Connection) -> CoverageSnapshot:
    trading_days = load_trading_days(conn)
    tables = collect_table_coverage(conn)
    symbols = collect_symbol_coverage(conn, trading_days)
    freshness, _fresh_findings = collect_freshness(conn)
    gaps = gap_findings(symbols)
    return CoverageSnapshot(
        tables=tables,
        symbols=symbols,
        freshness=freshness,
        gap_findings=gaps,
        limitations=EXPECTED_LIMITATIONS,
        unresolved_symbols=UNRESOLVED_SYMBOLS,
        unresolved_macro=UNRESOLVED_MACRO,
    )
