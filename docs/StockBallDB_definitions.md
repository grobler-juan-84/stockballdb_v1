# StockBallDB — Definitions

**Version:** 0.01
**Status:** Initial Definitions
**Last Updated:** 2026-08-23

> Companion docs: [index](StockBallDB_index.md) · [manifesto](StockBallDB_manifesto.md) · [universe](StockBallDB_universe.md) · [schema](StockBallDB_schema.md)

## Purpose

This document defines the **meaning, calculation, and interpretation of StockBallDB fields**.

The schema determines **what fields exist**.
This document determines **what those fields mean**.

Its purpose is to prevent ambiguity and ensure that derived values can be reproduced consistently across builds, machines, providers, and future applications.

Definitions should be explicit enough that two independent implementations using the same underlying observations produce equivalent results.

Where a definition has not yet been finalized, it is marked **TBD** rather than assumed.

---

# General Conventions

## Observed Data

Observed data is obtained from an external source and stored after normalization.

Examples:

* open
* high
* low
* close
* volume
* interest rates
* economic releases

Provider-specific formats are normalized before entering the canonical database.

## Derived Data

Derived data is calculated deterministically from observed data or other defined StockBallDB fields.

Examples:

* returns
* moving-average relationships
* drawdowns
* volatility
* trading-day counters
* regime classifications

Every derived field must have a reproducible definition.

## Percentage Representation

Unless otherwise specified, percentage fields are stored as **decimal returns**.

Example:

```text
0.05 = +5%
-0.05 = -5%
```

## Trading-Day Windows

Unless explicitly stated otherwise, periods such as:

```text
5d
20d
60d
200d
```

refer to **trading days**, not calendar days.

---

# 1. `trading_days`

## `date`

Valid market trading date.

One row exists for each recognized trading day in the StockBallDB trading calendar.

## `weekday`

Day of the week for `date`.

```text
Monday → Friday
```

## `month`

Calendar month number.

```text
January = 1
December = 12
```

## `quarter`

Calendar quarter.

```text
Q1 = 1
Q2 = 2
Q3 = 3
Q4 = 4
```

## `year`

Four-digit calendar year.

## `day_of_month`

Calendar day number within the month.

## `week_of_year`

Calendar week number.

Exact week-number convention: **TBD**.

## `trading_day_of_month`

Sequential trading-day number within the calendar month.

```text
First trading day = 1
Second trading day = 2
...
```

## `trading_day_of_year`

Sequential trading-day number within the calendar year.

```text
First trading day = 1
```

## `days_to_month_end`

Number of remaining trading days after the current date before the final trading day of the month.

Therefore:

```text
month-end trading day = 0
previous trading day = 1
```

## `is_month_end`

`true` when `date` is the final trading day of its calendar month.

## `is_quarter_end`

`true` when `date` is the final trading day of its calendar quarter.

## `is_year_end`

`true` when `date` is the final trading day of its calendar year.

## `prev_trading_date`

Immediately preceding valid trading date.

## `next_trading_date`

Immediately following valid trading date.

---

# 2. `daily_market_data`

## Observed Fields

### `open`

Opening price for the asset on `date`.

### `high`

Highest traded price during the session.

### `low`

Lowest traded price during the session.

### `close`

Closing price for the session.

### `volume`

Reported trading volume for the session.

Volume interpretation may vary by asset type and provider and must be documented in the source configuration.

---

## Derived Fields

### `return_1d`

Close-to-close return from the previous available trading observation.

```text
return_1d =
(close_t / close_t-1) - 1
```

### `gap_pct`

Difference between the current session open and previous session close.

```text
gap_pct =
(open_t / close_t-1) - 1
```

### `intraday_return`

Return from the current session open to close.

```text
intraday_return =
(close_t / open_t) - 1
```

### `range_pct`

Size of the session's high-low range relative to the opening price.

```text
range_pct =
(high_t - low_t) / open_t
```

### `drawdown_from_high`

Percentage decline of the current close from the historical high available through `date`.

```text
historical_high_t =
MAX(close through t)

drawdown_from_high =
(close_t / historical_high_t) - 1
```

Exact price basis for the historical high remains subject to final confirmation.

---

# 3. `market_outcomes`

`market_outcomes` contains **forward-looking labels calculated retrospectively**.

These values were not known on `date` and must never be treated as information available at that time.

## Forward Returns

### `return_1d`

```text
(close_t+1 / close_t) - 1
```

### `return_3d`

```text
(close_t+3 / close_t) - 1
```

### `return_5d`

```text
(close_t+5 / close_t) - 1
```

### `return_10d`

```text
(close_t+10 / close_t) - 1
```

### `return_20d`

```text
(close_t+20 / close_t) - 1
```

All offsets refer to subsequent valid trading observations for that symbol.

Exact entry-price convention may be revised if StockBallDB later standardizes outcomes around next-session open rather than current close.

## `max_up_5d`

Maximum favorable price movement occurring during the following 5 trading sessions.

Exact calculation and price basis: **TBD**.

## `max_down_5d`

Maximum adverse price movement occurring during the following 5 trading sessions.

Exact calculation and price basis: **TBD**.

## `max_up_20d`

Maximum favorable price movement occurring during the following 20 trading sessions.

Exact calculation and price basis: **TBD**.

## `max_down_20d`

Maximum adverse price movement occurring during the following 20 trading sessions.

Exact calculation and price basis: **TBD**.

## `positive_1d`

```text
return_1d > 0
```

## `positive_5d`

```text
return_5d > 0
```

## `positive_20d`

```text
return_20d > 0
```

A return of exactly zero is **not positive**.

---

# 4. `asset_regimes`

## Historical Returns

### `return_5d`

Trailing 5-trading-day return.

```text
(close_t / close_t-5) - 1
```

### `return_20d`

Trailing 20-trading-day return.

```text
(close_t / close_t-20) - 1
```

### `return_60d`

Trailing 60-trading-day return.

```text
(close_t / close_t-60) - 1
```

---

## Moving Averages

Simple moving averages are calculated using closing prices.

### `above_20dma`

```text
close_t > SMA20_t
```

### `above_50dma`

```text
close_t > SMA50_t
```

### `above_200dma`

```text
close_t > SMA200_t
```

Equality is classified as `false`.

### `distance_20dma_pct`

```text
(close_t / SMA20_t) - 1
```

### `distance_50dma_pct`

```text
(close_t / SMA50_t) - 1
```

### `distance_200dma_pct`

```text
(close_t / SMA200_t) - 1
```

---

## `volatility_20d`

Historical volatility calculated from the previous 20 daily returns.

Exact statistical convention and annualization rule: **TBD**.

## `drawdown_pct`

Current decline from the asset's historical peak.

Exact peak-price basis: **TBD**.

---

## Regime Classifications

### `trend_regime`

Categorical description of the asset's prevailing trend.

Exact classification rules: **TBD**.

Potential states may eventually include:

```text
uptrend
downtrend
neutral
```

These labels are illustrative only until formally defined.

### `momentum_regime`

Categorical description of recent price momentum.

Exact classification rules: **TBD**.

### `volatility_regime`

Categorical description of the current volatility environment.

Exact classification rules: **TBD**.

---

# 5. `macro_conditions`

Macro fields represent the economic information associated with a trading date.

Historical integrity is especially important here because economic data may be revised after its original publication.

Where practical, StockBallDB should distinguish between:

* the value known at the time;
* later revised values;
* the reference period;
* the release date.

## Observed Macro Fields

Definitions and source-specific timing rules remain to be finalized for:

```text
inflation_rate
core_inflation_rate
unemployment_rate
jobless_claims
fed_funds_rate
treasury_2y_yield
treasury_10y_yield
fed_balance_sheet
credit_spread
pmi
```

## `yield_curve_10y_2y`

Difference between the 10-year and 2-year U.S. Treasury yields.

```text
yield_curve_10y_2y =
treasury_10y_yield - treasury_2y_yield
```

## `inflation_regime`

Categorical interpretation of the inflation environment.

Definition: **TBD**.

## `rate_regime`

Categorical interpretation of the interest-rate environment.

Definition: **TBD**.

---

# 6. `scheduled_events`

## `event_id`

Unique identifier for an event.

## `event_date`

Trading date associated with the event.

## `event_type`

Standardized type of event.

Classification vocabulary: **TBD**.

## `event_name`

Human-readable event name.

## `event_category`

Broader standardized grouping of related event types.

Classification vocabulary: **TBD**.

## `event_time`

Scheduled or known event time when available.

Timezone convention: **TBD**.

## `release_session`

Relationship between the event time and the normal trading session.

Potential classifications may include:

```text
pre_market
market_hours
post_market
unknown
```

Final vocabulary: **TBD**.

## `reference_period`

Economic or reporting period to which the event relates, when applicable.

## `source`

Origin of the event information.

## `country`

Country primarily associated with the event.

---

# 7. `calendar_context`

## `is_day_before_holiday`

`true` when the next scheduled trading session is separated from the current session by a recognized market holiday.

Exact holiday handling: **TBD**.

## `is_day_after_holiday`

`true` when the previous scheduled trading session was separated from the current session by a recognized market holiday.

## `holiday_name`

Name of the relevant holiday.

## `holiday_type`

Classification of the holiday.

Definition: **TBD**.

## `is_shortened_trading_day`

`true` when the scheduled regular trading session is shorter than a normal session.

## `is_shortened_week`

`true` when the trading week contains fewer normal trading sessions than a standard five-session week.

Exact treatment of shortened sessions: **TBD**.

## `trading_days_in_week`

Number of valid trading sessions belonging to the relevant trading week.

## `is_turn_of_month`

Identifies dates surrounding the transition between calendar months.

Exact window: **TBD**.

## `days_to_tax_deadline`

Number of days until the relevant tax deadline.

Calendar-day versus trading-day convention and applicable tax deadline: **TBD**.

## `is_quarter_transition`

Identifies dates surrounding the transition between calendar quarters.

Exact window: **TBD**.

## `is_year_transition`

Identifies dates surrounding the transition between calendar years.

Exact window: **TBD**.

## `is_election_period`

Identifies dates falling within a defined election-related period.

Exact election types and window: **TBD**.

## `is_payday_period`

Identifies dates associated with defined common payroll periods.

Exact rule: **TBD**.

---

# Missing Data and Insufficient History

Derived values must not be fabricated when insufficient historical data exists.

Example:

An asset with only 100 historical observations cannot yet have a valid 200-day moving average.

In such cases:

```text
above_200dma = NULL
distance_200dma_pct = NULL
```

The same principle applies to forward outcomes near the end of the available dataset.

If 20 future trading observations do not exist:

```text
return_20d = NULL
```

Missing information remains missing rather than being estimated unless an explicit future StockBallDB rule defines an estimation method.

---

# Definition Changes

Definitions are part of StockBallDB's reproducibility contract.

Changing a formula or classification rule can change historical values even when the underlying observed data has not changed.

Therefore, material definition changes must be:

1. deliberate;
2. documented;
3. version controlled;
4. reflected in the relevant pipeline;
5. reproducible during a full database rebuild.

> **A field name tells us what a value is called. This document tells us exactly what that value means.**
