"""Trading-day availability mapping for macro releases."""

from __future__ import annotations

import datetime as dt
from bisect import bisect_left, bisect_right

from stockballdb.macro.series import ReleaseTiming


def _parse_date(value: str | dt.date) -> dt.date:
    if isinstance(value, dt.date):
        return value
    return dt.date.fromisoformat(str(value)[:10])


class TradingDayIndex:
    """Sorted trading-day calendar helpers."""

    def __init__(self, trading_days: list[dt.date]):
        self.days = sorted(trading_days)
        if not self.days:
            raise ValueError("trading_days is empty")

    def contains(self, d: dt.date) -> bool:
        i = bisect_left(self.days, d)
        return i < len(self.days) and self.days[i] == d

    def on_or_next(self, d: dt.date) -> dt.date | None:
        i = bisect_left(self.days, d)
        if i >= len(self.days):
            return None
        return self.days[i]

    def strictly_after(self, d: dt.date) -> dt.date | None:
        i = bisect_right(self.days, d)
        if i >= len(self.days):
            return None
        return self.days[i]


def map_availability_to_trading_day(
    calendar_date: str | dt.date,
    timing: ReleaseTiming,
    td: TradingDayIndex,
) -> dt.date | None:
    """
    Map a provider/release calendar date onto the trading_days spine.

    pre_open:
      release calendar date on trading day t -> t; else next trading day.
    after_close:
      first trading day strictly after the release calendar date.
    observation_date:
      trading day only if calendar_date itself is a trading day (else None).
    """
    d = _parse_date(calendar_date)
    if timing == "observation_date":
        return d if td.contains(d) else None
    if timing == "pre_open":
        return td.on_or_next(d)
    if timing == "after_close":
        return td.strictly_after(d)
    raise ValueError(f"unknown timing={timing!r}")
