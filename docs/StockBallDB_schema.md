# StockBallDB — Schema

**Version:** 1  
**Status:** Initial Schema  
**Last Updated:** 2026-08-23

> Companion docs: [index](StockBallDB_index.md) · [manifesto](StockBallDB_manifesto.md) · [universe](StockBallDB_universe.md)

## Purpose

Structural design of StockBallDB: tables, responsibilities, relationships, keys, and principal fields.

| Topic | Document |
| ----- | -------- |
| Philosophy and rules | [manifesto](StockBallDB_manifesto.md) |
| Asset / indicator scope | [universe](StockBallDB_universe.md) |
| Providers | `StockBallDB_sources.md` |
| Build / update / derive / validate | `StockBallDB_workflow.md` |
| Field formulas | `StockBallDB_definitions.md` |

PostgreSQL migrations in Git are the authoritative implementation.

## Overview

Seven tables organized around a trading-day spine. Each owns a distinct category of historical information.

| Table               | Grain         | Responsibility                                       |
| ------------------- | ------------- | ---------------------------------------------------- |
| `trading_days`      | trading day   | Foundational market calendar                         |
| `daily_market_data` | date × symbol | Daily market observations and basic derived behavior |
| `market_outcomes`   | date × symbol | Forward market outcomes                              |
| `asset_regimes`     | date × symbol | Historical asset state and regime measurements       |
| `macro_conditions`  | trading day   | Macroeconomic and monetary context                   |
| `scheduled_events`  | event         | Scheduled market-relevant events                     |
| `calendar_context`  | trading day   | Calendar, holiday, seasonal, and transition context  |

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
**Primary key:** `(date, symbol)` · **FK:** `date → trading_days.date`

**Observed:** `open`, `high`, `low`, `close`, `volume`  
**Derived:** `return_1d`, `gap_pct`, `intraday_return`, `range_pct`, `drawdown_from_high`

---

## 3. `market_outcomes`

**Grain:** date × symbol  
**Primary key:** `(date, symbol)` · **FK:** `date → trading_days.date`

Forward outcomes after a trading date (research use; not information known on that date). All fields derived.

```text
return_1d, return_3d, return_5d, return_10d, return_20d
max_up_5d, max_down_5d, max_up_20d, max_down_20d
positive_1d, positive_5d, positive_20d
```

---

## 4. `asset_regimes`

**Grain:** date × symbol  
**Primary key:** `(date, symbol)` · **FK:** `date → trading_days.date`

Asset state on a trading day. Mostly derived from market observations.

```text
asset_type
return_5d, return_20d, return_60d
above_20dma, above_50dma, above_200dma
distance_20dma_pct, distance_50dma_pct, distance_200dma_pct
volatility_20d, drawdown_pct
trend_regime, momentum_regime, volatility_regime
```

---

## 5. `macro_conditions`

**Grain:** trading day  
**Primary key:** `date` · **FK:** `date → trading_days.date`

Macro / monetary context as of each trading day. Where point-in-time reconstruction is required, store what was publicly available then (see [manifesto §5](StockBallDB_manifesto.md#5-historical-integrity)).

```text
inflation_rate, core_inflation_rate
unemployment_rate, jobless_claims
fed_funds_rate, treasury_2y_yield, treasury_10y_yield, yield_curve_10y_2y
fed_balance_sheet, credit_spread, pmi
inflation_regime, rate_regime
```

---

## 6. `scheduled_events`

**Grain:** event  
**Primary key:** `event_id` · **FK:** `event_date → trading_days.date`

Multiple events may share a trading day (e.g. economic releases, central-bank events, elections).

```text
event_id, event_date
event_type, event_name, event_category
event_time, release_session, reference_period
source, country
```

---

## 7. `calendar_context`

**Grain:** trading day  
**Primary key:** `date` · **FK:** `date → trading_days.date`

Research-oriented calendar traits not part of the core `trading_days` definition.

```text
is_day_before_holiday, is_day_after_holiday, holiday_name, holiday_type
is_shortened_trading_day, is_shortened_week, trading_days_in_week
is_turn_of_month, days_to_tax_deadline
is_quarter_transition, is_year_transition
is_election_period, is_payday_period
```

---

## Evolution

Version 1 starting schema. Fields and tables may change via version-controlled migrations. Principles: [manifesto](StockBallDB_manifesto.md).
