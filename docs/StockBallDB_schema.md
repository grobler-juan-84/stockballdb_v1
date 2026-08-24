# StockBallDB — Schema

**Version:** 1
**Status:** Initial Schema
**Last Updated:** 2026-08-24

> Companion docs: [index](StockBallDB_index.md) · [manifesto](StockBallDB_manifesto.md) · [universe](StockBallDB_universe.md)

## Purpose

Structural design of StockBallDB: tables, responsibilities, relationships, keys, and principal fields.

| Topic                              | Document                              |
| ---------------------------------- | ------------------------------------- |
| Philosophy and rules               | [manifesto](StockBallDB_manifesto.md) |
| Asset / indicator scope            | [universe](StockBallDB_universe.md)   |
| Providers                          | `StockBallDB_sources.md`              |
| Build / update / derive / validate | `StockBallDB_workflow.md`             |
| Field formulas                     | `StockBallDB_definitions.md`          |

PostgreSQL migrations in Git are the authoritative implementation.

## Overview

Seven tables organized around a trading-day spine. Each owns a distinct category of historical information.

| Table               | Grain         | Responsibility                                                                       |
| ------------------- | ------------- | ------------------------------------------------------------------------------------ |
| `trading_days`      | trading day   | Foundational market calendar                                                         |
| `daily_market_data` | date × symbol | Daily market observations, corporate-action observations, and basic derived behavior |
| `market_outcomes`   | date × symbol | Forward market outcomes                                                              |
| `asset_regimes`     | date × symbol | Historical asset state and regime measurements                                       |
| `macro_conditions`  | trading day   | Macroeconomic and monetary context                                                   |
| `scheduled_events`  | event         | Scheduled market-relevant events                                                     |
| `calendar_context`  | trading day   | Calendar, holiday, seasonal, and transition context                                  |

## Core Relationships

All date foreign keys reference `trading_days.date`.

```text
trading_days.date
├── daily_market_data.date
├── market_outcomes.date
├── asset_regimes.date
├── macro_conditions.date
├── scheduled_events.event_date
└── calendar_context.date
```

---

## 1. `trading_days`

**Grain:** One row per valid market trading day
**Primary key:** `date`

Valid trading dates against which other datasets align. Calendar begins **1957** (rationale: [manifesto §6](StockBallDB_manifesto.md#6-why-trading_days-begins-in-1957)); other datasets need not.

```text
date
weekday, month, quarter, year, day_of_month, week_of_year
trading_day_of_month, trading_day_of_year, days_to_month_end
is_month_end, is_quarter_end, is_year_end
prev_trading_date, next_trading_date
```

---

## 2. `daily_market_data`

**Grain:** date × symbol
**Primary key:** `(date, symbol)`
**FK:** `date → trading_days.date`

Stores the core daily market observations for each asset.

For Tiingo-sourced ETFs, raw prices, adjusted prices, volume, adjusted volume, dividends, and split information are collected together during the same acquisition step.

### Observed — Raw Market Data

```text
open
high
low
close
volume
```

These represent the raw market observations reported for the trading session.

### Observed — Adjusted Market Data

```text
adj_open
adj_high
adj_low
adj_close
adj_volume
```

Adjusted observations normalize historical market data for applicable corporate actions such as stock splits and dividends.

Raw and adjusted observations are intentionally preserved separately.

### Observed — Corporate Actions

```text
dividend_cash
split_factor
```

`dividend_cash` records the cash dividend associated with the observation when applicable.

`split_factor` records the stock split or reverse-split factor associated with the observation when applicable.

These fields are retained as underlying observations rather than inferred from adjusted prices.

### Derived — Daily Price Behavior

```text
return_1d
gap_pct
intraday_return
range_pct
drawdown_from_high
```

Derived values are calculated internally by StockBallDB according to `StockBallDB_definitions.md`.

---

## 3. `market_outcomes`

**Grain:** date × symbol
**Primary key:** `(date, symbol)`
**FK:** `date → trading_days.date`

Forward outcomes after a trading date.

These fields are calculated retrospectively and represent information that was **not known on the associated trading date**.

All fields are derived.

```text
return_1d
return_3d
return_5d
return_10d
return_20d

max_up_5d
max_down_5d
max_up_20d
max_down_20d

positive_1d
positive_5d
positive_20d
```

---

## 4. `asset_regimes`

**Grain:** date × symbol
**Primary key:** `(date, symbol)`
**FK:** `date → trading_days.date`

Asset state on a trading day. Mostly derived from historical market observations available through that date.

```text
asset_type

return_5d
return_20d
return_60d

above_20dma
above_50dma
above_200dma

distance_20dma_pct
distance_50dma_pct
distance_200dma_pct

volatility_20d
drawdown_pct

trend_regime
momentum_regime
volatility_regime
```

---

## 5. `macro_conditions`

**Grain:** trading day
**Primary key:** `date`
**FK:** `date → trading_days.date`

Macroeconomic and monetary context associated with each trading day.

Where point-in-time reconstruction is required, StockBallDB stores or reconstructs the information that was publicly available at that time rather than silently substituting later revisions.

```text
inflation_rate
core_inflation_rate
unemployment_rate
jobless_claims

fed_funds_rate
treasury_2y_yield
treasury_10y_yield
yield_curve_10y_2y

fed_balance_sheet
credit_spread
pmi

inflation_regime
rate_regime
```

---

## 6. `scheduled_events`

**Grain:** event
**Primary key:** `event_id`
**FK:** `event_date → trading_days.date`

Stores scheduled market-relevant events.

Multiple events may occur on the same trading day.

Examples include economic releases, central-bank events, and elections.

```text
event_id
event_date

event_type
event_name
event_category

event_time
release_session
reference_period

source
country
```

---

## 7. `calendar_context`

**Grain:** trading day
**Primary key:** `date`
**FK:** `date → trading_days.date`

Research-oriented calendar traits that are not part of the foundational definition of a valid trading day.

```text
is_day_before_holiday
is_day_after_holiday
holiday_name
holiday_type

is_shortened_trading_day
is_shortened_week
trading_days_in_week

is_turn_of_month
days_to_tax_deadline

is_quarter_transition
is_year_transition

is_election_period
is_payday_period
```

---

## Observed vs Derived Boundary

StockBallDB intentionally distinguishes external observations from internally calculated values.

### Observed

Examples include:

```text
raw prices
raw volume
adjusted prices
adjusted volume
dividend cash
split factors
macroeconomic observations
scheduled event information
```

Observed data enters StockBallDB through provider-specific acquisition and normalization pipelines.

### Derived

Examples include:

```text
returns
gaps
price ranges
drawdowns
moving averages
volatility
regimes
forward outcomes
calendar flags
```

Derived data is calculated deterministically by StockBallDB from defined underlying observations.

Provider-calculated values should not replace internally derived values when StockBallDB can reproduce the calculation reliably from underlying observations.

---

## Missing Data

Not every asset or dataset begins on the first StockBallDB trading date.

Missing historical observations remain missing.

StockBallDB does not fabricate unavailable history.

Derived values requiring unavailable historical or future observations remain `NULL` until sufficient data exists.

Examples:

```text
insufficient history for 200-day moving average
→ above_200dma = NULL

insufficient future history for 20-day outcome
→ return_20d = NULL
```

---

## Provider Independence

The schema belongs to StockBallDB, not to Tiingo, FRED, ALFRED, or any other provider.

Provider-specific field names are normalized into canonical StockBallDB fields before storage.

For example, a Tiingo response may provide the observations used for:

```text
open
high
low
close
volume

adj_open
adj_high
adj_low
adj_close
adj_volume

dividend_cash
split_factor
```

The provider's naming convention does not determine the canonical database naming convention.

Replacing a provider should ideally require acquisition and normalization changes rather than redesigning the schema.

---

## Evolution

Version 1 is a starting schema.

The initial population of the seven tables is also an experimental schema-validation phase. Real data may expose fields that should be added, removed, renamed, separated, or redefined.

Schema changes must be:

1. deliberate;
2. documented;
3. version controlled;
4. implemented through PostgreSQL migrations;
5. reflected in definitions and acquisition logic where applicable;
6. reproducible during a full database rebuild.

The schema should evolve from evidence obtained while building and validating StockBallDB rather than assumptions about future experiments.
