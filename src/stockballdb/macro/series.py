"""StockBallDB-owned FRED/ALFRED series configuration for macro_conditions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ReleaseTiming = Literal["pre_open", "after_close", "observation_date"]


@dataclass(frozen=True)
class MacroSeriesSpec:
    """Canonical mapping from a macro_conditions field to a FRED series."""

    field: str
    series_id: str
    pit_vintage: bool
    forward_fill: bool
    timing: ReleaseTiming
    compute_yoy_pc1: bool = False
    units_note: str = ""


# PMI deferred from V1 — no satisfactory freely reproducible source.
MACRO_SERIES: tuple[MacroSeriesSpec, ...] = (
    MacroSeriesSpec(
        field="inflation_rate",
        series_id="CPIAUCSL",
        pit_vintage=True,
        forward_fill=True,
        timing="pre_open",
        compute_yoy_pc1=True,
        units_note="percent YoY (1.0 = 1 percentage point)",
    ),
    MacroSeriesSpec(
        field="core_inflation_rate",
        series_id="CPILFESL",
        pit_vintage=True,
        forward_fill=True,
        timing="pre_open",
        compute_yoy_pc1=True,
        units_note="percent YoY (1.0 = 1 percentage point)",
    ),
    MacroSeriesSpec(
        field="unemployment_rate",
        series_id="UNRATE",
        pit_vintage=True,
        forward_fill=True,
        timing="pre_open",
        units_note="percent",
    ),
    MacroSeriesSpec(
        field="jobless_claims",
        series_id="ICSA",
        pit_vintage=True,
        forward_fill=True,
        timing="pre_open",
        units_note="persons (initial claims, SA)",
    ),
    MacroSeriesSpec(
        field="fed_funds_rate",
        series_id="DFF",
        pit_vintage=False,
        forward_fill=False,
        timing="observation_date",
        units_note="percent (effective federal funds rate)",
    ),
    MacroSeriesSpec(
        field="treasury_2y_yield",
        series_id="DGS2",
        pit_vintage=False,
        forward_fill=False,
        timing="observation_date",
        units_note="percent",
    ),
    MacroSeriesSpec(
        field="treasury_10y_yield",
        series_id="DGS10",
        pit_vintage=False,
        forward_fill=False,
        timing="observation_date",
        units_note="percent",
    ),
    MacroSeriesSpec(
        field="fed_balance_sheet",
        series_id="WALCL",
        pit_vintage=False,
        forward_fill=True,
        timing="after_close",
        units_note="millions of USD (Fed total assets, Wednesday level)",
    ),
    MacroSeriesSpec(
        field="credit_spread",
        series_id="BAA10Y",
        pit_vintage=False,
        forward_fill=False,
        timing="observation_date",
        units_note="percent (Baa minus 10Y Treasury)",
    ),
)

MACRO_SERIES_BY_FIELD = {s.field: s for s in MACRO_SERIES}

INFLATION_REGIME_MIN_RELEASES = 36
RATE_REGIME_LOOKBACK = 63
RATE_REGIME_THRESHOLD = 0.25

ICSA_VINTAGE_LIMITATION = (
    "ICSA ALFRED vintage depth on FRED is sparse/incomplete before approximately 2009; "
    "pre-~2009 PIT reconstruction is best-effort from available vintages only."
)
