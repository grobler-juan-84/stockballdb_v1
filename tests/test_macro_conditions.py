"""Deterministic tests for macro alignment, PIT, and regimes."""

from __future__ import annotations

import datetime as dt

import pandas as pd
import pytest

from stockballdb.macro.derive import (
    derive_inflation_regime,
    derive_rate_regime,
    derive_yield_curve,
)
from stockballdb.macro.pit import (
    VintageRow,
    as_of_value_map,
    build_current_series_on_trading_days,
    build_distinct_inflation_release_yoy,
    build_pit_level_series_on_trading_days,
    yoy_from_index_state,
)
from stockballdb.macro.series import INFLATION_REGIME_MIN_RELEASES
from stockballdb.macro.validate import (
    assert_alignment_helpers,
    assert_no_future_inflation_release_leak,
)


def test_release_alignment_conventions() -> None:
    assert_alignment_helpers()


def test_no_backward_fill_current_series() -> None:
    days = [dt.date(2024, 1, 2), dt.date(2024, 1, 3), dt.date(2024, 1, 4)]
    obs = [
        {"date": "2024-01-03", "value": "1.5"},
        {"date": "2024-01-04", "value": "1.6"},
    ]
    s = build_current_series_on_trading_days(
        obs, days, "observation_date", forward_fill=False
    )
    assert pd.isna(s.loc[dt.date(2024, 1, 2)])
    assert s.loc[dt.date(2024, 1, 3)] == pytest.approx(1.5)


def test_forward_fill_after_availability_only() -> None:
    days = [
        dt.date(2024, 1, 2),
        dt.date(2024, 1, 3),
        dt.date(2024, 1, 4),
        dt.date(2024, 1, 5),
    ]
    obs = [{"date": "2024-01-03", "value": "4.2"}]
    s = build_current_series_on_trading_days(
        obs, days, "pre_open", forward_fill=True
    )
    assert pd.isna(s.loc[dt.date(2024, 1, 2)])
    assert s.loc[dt.date(2024, 1, 3)] == pytest.approx(4.2)
    assert s.loc[dt.date(2024, 1, 5)] == pytest.approx(4.2)


def test_walcl_after_close_next_trading_day() -> None:
    days = [
        dt.date(2024, 1, 3),
        dt.date(2024, 1, 4),
        dt.date(2024, 1, 5),
        dt.date(2024, 1, 8),
    ]
    obs = [{"date": "2024-01-03", "value": "7000000"}]
    s = build_current_series_on_trading_days(
        obs, days, "after_close", forward_fill=True, walcl_release_lag=True
    )
    assert pd.isna(s.loc[dt.date(2024, 1, 3)])
    assert pd.isna(s.loc[dt.date(2024, 1, 4)])
    assert s.loc[dt.date(2024, 1, 5)] == pytest.approx(7000000.0)


def test_pit_cpi_revision_behavior() -> None:
    vintages = [
        VintageRow(
            ref_date=dt.date(2019, 1, 1),
            value=100.0,
            realtime_start=dt.date(2019, 2, 10),
            realtime_end=dt.date(9999, 12, 31),
        ),
        VintageRow(
            ref_date=dt.date(2020, 1, 1),
            value=110.0,
            realtime_start=dt.date(2020, 2, 13),
            realtime_end=dt.date(2020, 3, 10),
        ),
        VintageRow(
            ref_date=dt.date(2020, 1, 1),
            value=111.0,
            realtime_start=dt.date(2020, 3, 10),
            realtime_end=dt.date(9999, 12, 31),
        ),
    ]
    assert as_of_value_map(vintages, dt.date(2020, 2, 20))[dt.date(2020, 1, 1)] == 110.0
    assert as_of_value_map(vintages, dt.date(2020, 3, 15))[dt.date(2020, 1, 1)] == 111.0
    state = as_of_value_map(vintages, dt.date(2020, 2, 13))
    assert yoy_from_index_state(state, dt.date(2020, 1, 1)) == pytest.approx(10.0)


def test_pit_no_pre_release_leakage() -> None:
    vintages = [
        VintageRow(
            ref_date=dt.date(2020, 1, 1),
            value=4.0,
            realtime_start=dt.date(2020, 2, 7),
            realtime_end=dt.date(9999, 12, 31),
        )
    ]
    days = [dt.date(2020, 2, 5), dt.date(2020, 2, 6), dt.date(2020, 2, 7)]
    s = build_pit_level_series_on_trading_days(vintages, days, "pre_open")
    assert pd.isna(s.loc[dt.date(2020, 2, 5)])
    assert pd.isna(s.loc[dt.date(2020, 2, 6)])
    assert s.loc[dt.date(2020, 2, 7)] == pytest.approx(4.0)


def test_yield_curve_derivation_and_null_legs() -> None:
    frame = pd.DataFrame(
        {
            "treasury_10y_yield": [4.0, 4.0, None],
            "treasury_2y_yield": [3.5, None, 3.5],
        }
    )
    curve = derive_yield_curve(frame)
    assert curve.iloc[0] == pytest.approx(0.5)
    assert pd.isna(curve.iloc[1])
    assert pd.isna(curve.iloc[2])


def test_inflation_regime_distinct_releases_not_daily_duplicates() -> None:
    releases = [
        (dt.date(2020, 1, 1) + dt.timedelta(days=10 * i), 1.0 + 0.1 * i)
        for i in range(40)
    ]
    days = [dt.date(2020, 1, 1) + dt.timedelta(days=i) for i in range(500)]
    vals = []
    last = None
    rel_i = 0
    for d in days:
        while rel_i < len(releases) and releases[rel_i][0] <= d:
            last = releases[rel_i][1]
            rel_i += 1
        vals.append(last)
    s = pd.Series(vals, index=days)
    regimes = derive_inflation_regime(s, releases)
    first_idx = next(i for i, r in enumerate(regimes) if r is not None)
    d0 = days[first_idx]
    n = sum(1 for rd, _ in releases if rd <= d0)
    assert n >= INFLATION_REGIME_MIN_RELEASES
    assert len(releases) < int(s.notna().sum())


def test_inflation_regime_anti_future_leak() -> None:
    releases = [
        (dt.date(2018, 1, 15) + dt.timedelta(days=32 * i), float(i % 9))
        for i in range(50)
    ]
    days = pd.date_range("2018-01-01", periods=800, freq="B").date.tolist()
    vals = []
    last = None
    ri = 0
    for d in days:
        while ri < len(releases) and releases[ri][0] <= d:
            last = releases[ri][1]
            ri += 1
        vals.append(last)
    frame = pd.DataFrame({"date": days, "inflation_rate": vals})
    assert_no_future_inflation_release_leak(releases, frame)


def test_rate_regime_63_boundary() -> None:
    vals = [1.0] * 63 + [1.5]
    regimes = derive_rate_regime(pd.Series(vals))
    assert all(r is None for r in regimes[:63])
    assert regimes[63] == "tightening"
    vals2 = [2.0] * 63 + [1.5]
    r2 = derive_rate_regime(pd.Series(vals2))
    assert r2[63] == "easing"


def test_distinct_yoy_release_builder() -> None:
    vintages = []
    for ref, level, start in (
        (dt.date(2019, 1, 1), 100.0, dt.date(2019, 2, 12)),
        (dt.date(2020, 1, 1), 102.0, dt.date(2020, 2, 13)),
    ):
        vintages.append(
            VintageRow(
                ref_date=ref,
                value=level,
                realtime_start=start,
                realtime_end=dt.date(9999, 12, 31),
            )
        )
    days = pd.date_range("2019-02-01", periods=400, freq="B").date.tolist()
    releases = build_distinct_inflation_release_yoy(vintages, days, "pre_open")
    assert len(releases) == 1
    assert releases[0][1] == pytest.approx(2.0)
