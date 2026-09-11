# StockBallDB — Schema

**Status:** Canonical V1 schema  
**Alembic head:** `a8f3c2d1b4e5`

> Companion docs: [index](StockBallDB_index.md) · [manifesto](StockBallDB_manifesto.md) · [universe](StockBallDB_universe.md) · [sources](StockBallDB_sources.md) · [definitions](StockBallDB_definitions.md) · [workflow](StockBallDB_workflow.md) · [validation](StockBallDB_validation.md)

## Purpose

Structural design of StockBallDB: tables, responsibilities, relationships, keys, and principal fields.

| Topic                              | Document                              |
| ---------------------------------- | ------------------------------------- |
| Philosophy and rules               | [manifesto](StockBallDB_manifesto.md) |
| Asset / indicator scope            | [universe](StockBallDB_universe.md)   |
| Providers                          | [sources](StockBallDB_sources.md)         |
| Build / update / derive / validate | [workflow](StockBallDB_workflow.md)       |
| Field formulas                     | [definitions](StockBallDB_definitions.md) |
| Validation / health / fingerprint  | [validation](StockBallDB_validation.md)   |

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
| `scheduled_events`  | event         | Scheduled-event occurrence calendar (intrinsic event facts)                          |
| `calendar_context`  | trading day   | Deterministic holiday/session/transition + retrospective event context               |

## Core Relationships

Date foreign keys to `trading_days.date` apply to trading-day-grained tables. `scheduled_events.event_date` is a calendar occurrence date and is **not** an FK to `trading_days`.

```text
trading_days.date
├── daily_market_data.date
├── market_outcomes.date
├── asset_regimes.date
├── macro_conditions.date
└── calendar_context.date

scheduled_events.event_date   (calendar date; no trading_days FK)
```

---

## 1. `trading_days`

**Grain:** One row per valid market trading day
**Primary key:** `date`

Valid trading dates against which other datasets align. Calendar begins **1957** (rationale: [manifesto §8](StockBallDB_manifesto.md#8-why-trading_days-begins-in-1957)); other datasets need not.

Authority: pinned `pandas_market_calendars` NYSE calendar (see sources). Early-close sessions remain rows here; shortened-session flags belong in `calendar_context`.

```text
date                      DATE PRIMARY KEY
weekday                   SMALLINT  -- ISO: Mon=1 … Fri=5
month                     SMALLINT  -- 1–12
quarter                   SMALLINT  -- 1–4
year                      SMALLINT
day_of_month              SMALLINT  -- 1–31
week_of_year              SMALLINT  -- ISO 8601 week number
trading_day_of_month      SMALLINT
trading_day_of_year       SMALLINT
days_to_month_end         SMALLINT  -- 0 on month-end trading day
is_month_end              BOOLEAN NOT NULL
is_quarter_end            BOOLEAN NOT NULL
is_year_end               BOOLEAN NOT NULL
prev_trading_date         DATE NULL  -- NULL on first row; no self-FK
next_trading_date         DATE NULL  -- NULL on last row; no self-FK
```

---

## 2. `daily_market_data`

**Grain:** date × symbol
**Primary key:** `(date, symbol)`
**FK:** `date → trading_days.date`

Stores the core daily market observations for each asset.

For Tiingo-sourced ETFs, raw prices, adjusted prices, volume, adjusted volume, dividends, and split information are collected together during the same acquisition step.

V1 loads **14 Tiingo ETFs** plus **WTI** (`DCOILWTICO`) as a close-only row: `close` holds the spot level; `open`/`high`/`low`/`volume`/all `adj_*`/corp-action columns are **NULL** (never copied from `close`). Migration `a8f3c2d1b4e5` relaxes NOT NULL and adds a row-shape CHECK enforcing full-OHLC ETF rows vs close-only context rows. Dates must exist in `trading_days`. Pre-inception history is simply absent (no fabricated rows).

### Observed — Raw Market Data

```text
open, high, low, close     NUMERIC NOT NULL
volume                     BIGINT NOT NULL
```

### Observed — Adjusted Market Data

```text
adj_open, adj_high, adj_low, adj_close   NUMERIC NOT NULL
adj_volume                               BIGINT NOT NULL
```

### Observed — Corporate Actions

```text
dividend_cash   NUMERIC NOT NULL   -- Tiingo divCash stored as observed (often 0.0)
split_factor    NUMERIC NOT NULL   -- Tiingo splitFactor stored as observed (often 1.0)
```

Canonical interpretation (locked; storage unchanged):

```text
dividend_cash = 0.0  → provider reports no cash dividend
split_factor  = 1.0  → provider reports no split
NULL                 → missing / unknown / not supplied
```

Do not rewrite existing `0.0` / `1.0` observations to `NULL`.

### Derived — Daily Price Behavior

```text
return_1d            NUMERIC NULL  -- ADJUSTED; NULL on first row per symbol
gap_pct              NUMERIC NULL  -- ADJUSTED; NULL on first row per symbol
intraday_return      NUMERIC NULL  -- RAW session
range_pct            NUMERIC NULL  -- RAW session
drawdown_from_high   NUMERIC NULL  -- ADJUSTED expanding max
```

Formulas locked in `StockBallDB_definitions.md`. Adjusted-based derived fields are retrospectively normalized economic history.

---

## 3. `market_outcomes`

**Grain:** date × symbol  
**Primary key:** `(date, symbol)`  
**FK:** `date → trading_days.date`

Forward outcomes after a trading date — **entirely retrospective labels**. Values were **NOT** information available on `date`.

Derived exclusively from canonical `daily_market_data` adjusted OHLC (close→future-close returns; high/low extrema for max up/down). Incomplete horizons → `NULL`.

```text
return_1d, return_3d, return_5d, return_10d, return_20d   NUMERIC NULL
max_up_5d, max_down_5d, max_up_20d, max_down_20d           NUMERIC NULL  -- signed
positive_1d, positive_5d, positive_20d                     BOOLEAN NULL
```

Formulas locked in `StockBallDB_definitions.md`.

---

## 4. `asset_regimes`

**Grain:** date × symbol  
**Primary key:** `(date, symbol)`  
**FK:** `date → trading_days.date`

Asset state on a trading day using only same-symbol observations with `date ≤ t`. Does **not** use `market_outcomes`.

Derived exclusively from canonical `daily_market_data`. Adjusted-derived fields are retrospectively normalized economic history.

```text
asset_type                                              TEXT NOT NULL  -- V1: "etf"

return_5d, return_20d, return_60d                       NUMERIC NULL  -- ADJUSTED
above_20dma, above_50dma, above_200dma                  BOOLEAN NULL
distance_20dma_pct, distance_50dma_pct, distance_200dma_pct  NUMERIC NULL
volatility_20d                                          NUMERIC NULL  -- annualized, ddof=1
drawdown_pct                                            NUMERIC NULL  -- mirrors drawdown_from_high

trend_regime                                            TEXT NULL  -- uptrend|downtrend|neutral
momentum_regime                                         TEXT NULL  -- positive|negative|mixed
volatility_regime                                       TEXT NULL  -- low|normal|high
```

Formulas locked in `StockBallDB_definitions.md`.

---

## 5. `macro_conditions`

**Grain:** trading day (1:1 with `trading_days`)  
**Primary key:** `date`  
**FK:** `date → trading_days.date`

Macroeconomic and monetary context available through date `t`. Point-in-time reconstruction for revised BLS series; market rates use dated observations without forward-fill.

`pmi` is **deferred from V1** (no satisfactory freely reproducible source). Column omitted.

```text
inflation_rate, core_inflation_rate     NUMERIC NULL  -- CPI YoY %, PIT
unemployment_rate                       NUMERIC NULL  -- UNRATE %, PIT
jobless_claims                          NUMERIC NULL  -- ICSA persons, PIT
fed_funds_rate                          NUMERIC NULL  -- DFF %
treasury_2y_yield, treasury_10y_yield   NUMERIC NULL  -- DGS2 / DGS10 %
yield_curve_10y_2y                      NUMERIC NULL  -- derived 10Y-2Y
fed_balance_sheet                       NUMERIC NULL  -- WALCL millions USD
credit_spread                           NUMERIC NULL  -- BAA10Y %
inflation_regime                        TEXT NULL     -- low|normal|high
rate_regime                             TEXT NULL     -- easing|stable|tightening
```

Formulas and series IDs: [StockBallDB_definitions.md](StockBallDB_definitions.md) / [StockBallDB_sources.md](StockBallDB_sources.md).

---

## 6. `scheduled_events`

**Grain:** event (one row per scheduled event occurrence)
**Primary key:** `event_id`
**FK:** none (`event_date` is a calendar occurrence date — **not** FK to `trading_days`)

Scheduled-event **occurrence calendar** of intrinsic event facts.

Not a surprise/result warehouse, not macro state, not trading-day-relative features, and not a full reconstruction of when every future calendar date first became knowable.

```text
event_id             TEXT PK   -- {type}:{date}:{ref_or_NA}:{symbol_or_MARKET}
event_type           TEXT      -- fomc | cpi | employment_situation | election
event_date           DATE      -- calendar occurrence date
symbol               TEXT NULL -- NULL = market-wide (all V1 rows)
reference_period     TEXT NULL -- YYYY-MM | presidential | midterm | NULL (fomc)
release_session      TEXT      -- pre_open | during_session | after_close | unknown
event_time_et        TIME NULL
source               TEXT
```

**V1 scope:** scheduled FOMC decision days; BLS CPI & Employment Situation releases; U.S. presidential + midterm Election Days.  
**Deferred / rejected:** earnings; unscheduled Fed actions; columns `actual` / `previous` / `consensus` / `surprise` / `importance`; forward `event_window` features (→ `calendar_context` owns retrospective distances only).

**Event definition (V1):** historically reconstructible, systematically knowable official/institutional occurrence — objective context only. Exclude news, disasters, earnings (V1), emergency Fed, consensus, surprise, importance, and market reactions.

Definitions and sources: [StockBallDB_definitions.md](StockBallDB_definitions.md) / [StockBallDB_sources.md](StockBallDB_sources.md).

---

## 7. `calendar_context`

**Grain:** trading day (1:1 with `trading_days`)
**Primary key:** `date`
**FK:** `date → trading_days.date`

Deterministic trading-day context: holiday/session geometry, ISO week counts, narrow month/quarter/year transitions, and retrospective event-distance context from `scheduled_events`.

**19 columns** in V1 (see field list below). Forward `days_to_next_*` / `days_until_next_*`, tax/payday, election periods, and earnings windows are **out of V1**. Ownership split: spine intrinsical fields remain on `trading_days`; context relationships live here.

```text
date                                         DATE PK FK → trading_days.date

is_day_before_holiday                        BOOLEAN NOT NULL
is_day_after_holiday                         BOOLEAN NOT NULL
holiday_name                                 TEXT NULL
holiday_type                                 TEXT NULL  -- regular | exceptional

is_shortened_trading_day                     BOOLEAN NOT NULL
is_shortened_week                            BOOLEAN NOT NULL
trading_days_in_week                         SMALLINT NOT NULL

is_turn_of_month                             BOOLEAN NOT NULL
is_quarter_transition                        BOOLEAN NOT NULL
is_year_transition                           BOOLEAN NOT NULL

is_fomc_day                                  BOOLEAN NOT NULL
days_since_last_fomc                         SMALLINT NULL

is_cpi_release_day                           BOOLEAN NOT NULL
days_since_last_cpi                          SMALLINT NULL

is_employment_situation_day                  BOOLEAN NOT NULL
days_since_last_employment_situation         SMALLINT NULL

is_election_day                              BOOLEAN NOT NULL
days_since_last_election                     SMALLINT NULL
```

Definitions locked in `StockBallDB_definitions.md`.

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

The seven-table V1 schema is **implemented and in use**.

Further schema changes must still be:

1. deliberate;
2. documented;
3. version controlled;
4. implemented through PostgreSQL migrations;
5. reflected in definitions and acquisition logic where applicable;
6. reproducible during a full database rebuild (including exact rebuild where Manifest 1.1 + snapshots apply).

The schema should evolve from evidence obtained while operating and validating StockBallDB, not from assumptions about future experiments, strategies, or trading systems.
