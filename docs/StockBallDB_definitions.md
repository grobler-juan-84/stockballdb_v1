# StockBallDB — Definitions

**Version:** 0.02
**Status:** Initial Definitions
**Last Updated:** 2026-08-24

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

* raw prices
* raw volume
* adjusted prices
* adjusted volume
* dividend cash
* split factors
* interest rates
* economic releases

Provider-specific formats and field names are normalized before entering the canonical database.

## Derived Data

Derived data is calculated deterministically from observed data or other defined StockBallDB fields.

Examples:

* returns
* moving-average relationships
* drawdowns
* volatility
* trading-day counters
* regime classifications
* forward outcomes

Every derived field must have a reproducible definition.

## Raw vs Adjusted Market Data

StockBallDB preserves both **raw** and **adjusted** market observations when they are available from the selected provider.

**Raw prices** represent the prices reported for the security on the historical trading day.

**Adjusted prices** represent historical prices normalized by the provider for applicable corporate actions such as stock splits and dividends.

Raw and adjusted values are not interchangeable.

StockBallDB retains both because they answer different questions:

* raw data preserves the historical market observation;
* adjusted data provides a consistent historical series for calculations affected by corporate actions.

The exact adjustment methodology is provider-dependent and must be documented in `StockBallDB_sources.md`.

## Percentage Representation

Unless otherwise specified, percentage fields are stored as **decimal returns**.

Example:

```text
0.05 = +5%
-0.05 = -5%
```

**Exception — `macro_conditions` rate fields:** FRED-native **percentage points** (`3.0` = 3%, not `0.03`). See `StockBallDB_definitions.md` §5 and `StockBallDB_phase4a_macro_contract.md` (Phase 4A lock).

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

ISO weekday number for `date`.

```text
Monday = 1
…
Friday = 5
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

ISO 8601 week number for `date`.

```text
Weeks start on Monday.
Week 1 is the week containing the year's first Thursday.
```

Python: `date.isocalendar().week`  
PostgreSQL: `EXTRACT(WEEK FROM date)`

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

`NULL` on the earliest row in `trading_days`.

## `next_trading_date`

Immediately following valid trading date.

`NULL` on the latest row in `trading_days`.

---

# 2. `daily_market_data`

## Observed — Raw Market Data

### `open`

Raw opening price reported for the asset on `date`.

### `high`

Highest raw traded price reported during the session.

### `low`

Lowest raw traded price reported during the session.

### `close`

Raw closing price reported for the session.

### `volume`

Raw reported trading volume for the session.

Volume interpretation may vary by asset type and provider and must be documented in the source configuration.

---

## Observed — Adjusted Market Data

### `adj_open`

Adjusted opening price for the asset on `date`.

Represents the historical opening price after applying the provider's applicable corporate-action adjustments.

### `adj_high`

Adjusted session high.

### `adj_low`

Adjusted session low.

### `adj_close`

Adjusted closing price.

This provides a historically normalized closing-price series accounting for applicable corporate actions.

### `adj_volume`

Adjusted trading volume.

Adjustment may be required to maintain historical comparability across corporate actions such as stock splits.

The exact methodology used for all adjusted fields depends on the provider and must be documented in the source configuration.

StockBallDB stores these values as **observations received from the provider** rather than deriving them independently.

---

## Observed — Corporate Actions

### `dividend_cash`

Cash dividend associated with the security observation when applicable.

For Tiingo-sourced market data, this corresponds to Tiingo's `divCash` field on the daily EOD bar.

**Locked interpretation (storage unchanged):**

```text
0.0  → provider explicitly reports no cash dividend for the observation
NULL → value missing / unknown / not supplied
```

StockBallDB stores provider values as observed. Quiet Tiingo days use `0.0`, not `NULL`. Do not rewrite existing `0.0` observations to `NULL`.

### `split_factor`

Stock split or reverse-split factor associated with the observation when applicable.

For Tiingo-sourced market data, this corresponds to Tiingo's `splitFactor` field.

**Locked interpretation (storage unchanged):**

```text
1.0  → provider explicitly reports no split for the observation
NULL → value missing / unknown / not supplied
```

Quiet Tiingo days use `1.0`, not `NULL`. Do not rewrite existing `1.0` observations to `NULL`.

---

## Derived — Daily Price Behavior

Derived from **canonical StockBallDB observations** (not from live provider responses).

**Previous observation** = the previous available row for the **same symbol** ordered by `date` (trading-day sequence), not calendar-day arithmetic.

**Integrity:** Raw OHLCV preserves historical quoted prints. Tiingo adjusted OHLCV is a **retrospectively normalized** representation (corporate actions after date *t* can restate `adj_*` on *t*). Derived fields that use adjusted prices are therefore **retrospectively normalized economic history** — they must not be described as values that were necessarily available in that adjusted form on the historical date.

### `return_1d`

Economically continuous close-to-close return (adjusted basis).

```text
return_1d =
(adj_close_t / adj_close_{t-1}) - 1
```

`NULL` on the first available observation for each symbol.

### `gap_pct`

Economically continuous overnight / open-vs-prior-close gap (adjusted basis).

```text
gap_pct =
(adj_open_t / adj_close_{t-1}) - 1
```

`NULL` on the first available observation for each symbol.

Raw quoted gap remains computable from observed `open` / `close` if needed; this field is the continuous economic gap.

### `intraday_return`

Session open-to-close return from **raw** quoted prices (point-in-time session tape).

```text
intraday_return =
(close_t / open_t) - 1
```

Populated whenever the current row has usable `open` and `close` (including the symbol’s first row).

### `range_pct`

Session high–low range relative to the **raw** open.

```text
range_pct =
(high_t - low_t) / open_t
```

Populated whenever the current row has usable `open`, `high`, and `low` (including the symbol’s first row).

### `drawdown_from_high`

Drawdown of the current adjusted close from the expanding historical adjusted high for that symbol.

```text
historical_high_t =
MAX(adj_close through t)   -- same symbol, dates ≤ t

drawdown_from_high =
(adj_close_t / historical_high_t) - 1
```

Uses retrospectively normalized `adj_close`. Populated on every row with usable `adj_close` (including the first row, where the value is `0`).

---

## Phase 5 — Additional market context (`WTI`, `XAU/USD`, `DXY`)

**Phase 5A contract:** `StockBallDB_phase5a_market_context_contract.md`

These symbols share `daily_market_data` grain but often provide **one daily level**, not full OHLCV.

**Storage (Phase 5B):** canonical level in **`close`** (native units); `open`/`high`/`low`/`volume`/`adj_*`/`dividend_cash`/`split_factor` = **NULL**. Do not duplicate the level across OHLC fields.

| Symbol | Definition | Units | Status |
| --- | --- | --- | --- |
| `WTI` | EIA Cushing WTI **spot** (FRED DCOILWTICO) | USD/barrel | **LOCKED** |
| `XAU/USD` | USD gold per troy oz (LBMA PM fix target) | USD/troy oz | **UNRESOLVED** source |
| `DXY` | ICE U.S. Dollar Index | index points | **UNRESOLVED** source |

**Derived fields (close-only path, Phase 5B):** `return_1d` and `drawdown_from_high` from `close`; `gap_pct`/`intraday_return`/`range_pct` NULL when OHLC absent.

---

# 3. `market_outcomes`

`market_outcomes` contains **entirely retrospective future labels**.

These values were **NOT information available on `date`**. They may be joined to historical dates for research/labeling, but must never be treated as contemporaneous inputs.

Calculations use retrospectively normalized adjusted OHLC from canonical `daily_market_data` (same Phase 2B integrity distinction).

**Grain:** `date × symbol`  
**Horizon indexing:** `t+N` = the Nth subsequent `daily_market_data` row for the **same symbol**, ordered by `date` ascending — not calendar arithmetic and not a bare `trading_days` offset when a bar is missing.

## Forward Returns

All use adjusted close → future adjusted close:

```text
return_1d  = (adj_close_{t+1}  / adj_close_t) - 1
return_3d  = (adj_close_{t+3}  / adj_close_t) - 1
return_5d  = (adj_close_{t+5}  / adj_close_t) - 1
return_10d = (adj_close_{t+10} / adj_close_t) - 1
return_20d = (adj_close_{t+20} / adj_close_t) - 1
```

Each field is `NULL` unless the complete required future horizon of N same-symbol observations exists. Never compute a partial horizon and keep the `*_Nd` label.

Consistency with `daily_market_data` (within float tolerance):

```text
market_outcomes.return_1d(t) ≈ daily_market_data.return_1d(t+1)
```

## Maximum Favorable / Adverse Movement

Baseline: `adj_close_t`  
Window: `t+1` through `t+N` inclusive (`date t` excluded)  
Store as **signed returns** (`max_down_*` may be negative, zero, or positive).

```text
max_up_5d   = MAX(adj_high_{t+1..t+5})  / adj_close_t - 1
max_down_5d = MIN(adj_low_{t+1..t+5})   / adj_close_t - 1
max_up_20d  = MAX(adj_high_{t+1..t+20}) / adj_close_t - 1
max_down_20d= MIN(adj_low_{t+1..t+20})  / adj_close_t - 1
```

Require the complete N-observation future window; otherwise `NULL`.

## Positive Flags

```text
positive_1d  = return_1d > 0
positive_5d  = return_5d > 0
positive_20d = return_20d > 0
```

```text
return > 0   → true
return <= 0  → false   (exactly zero is false)
return NULL  → NULL
```

PostgreSQL `BOOLEAN` (nullable).

---

# 4. `asset_regimes`

`asset_regimes` describes **historical asset state using only information available through date `t`** (same-symbol `daily_market_data` rows with `date ≤ t`).

It must **not** use `market_outcomes` or any future observations.

Adjusted OHLC is retrospectively normalized economic history under Tiingo's current adjustment methodology. Adjusted-derived regime measures are historically continuous economic series, not necessarily values published in that adjusted form on date `t` (same Phase 2B distinction).

**Grain:** `date × symbol`  
**Indexing:** `t-N` = Nth previous same-symbol observation by `date` ascending.

## `asset_type`

Canonical lowercase vocabulary from StockBallDB universe/configuration mapping (not provider metadata).

For the current V1 ETF universe:

```text
asset_type = "etf"
```

Never `NULL` for supported symbols.

## Historical Returns

All use adjusted close:

```text
return_5d  = (adj_close_t / adj_close_{t-5})  - 1
return_20d = (adj_close_t / adj_close_{t-20}) - 1
return_60d = (adj_close_t / adj_close_{t-60}) - 1
```

```text
return_5d  → first 5 rows/symbol NULL
return_20d → first 20 rows/symbol NULL
return_60d → first 60 rows/symbol NULL
```

No partial-history returns.

---

## Moving Averages

```text
SMA20_t  = mean(adj_close over t and previous 19 observations)
SMA50_t  = mean(adj_close over t and previous 49 observations)
SMA200_t = mean(adj_close over t and previous 199 observations)
```

Complete windows only:

```text
SMA20-based fields  → first 19 rows NULL
SMA50-based fields  → first 49 rows NULL
SMA200-based fields → first 199 rows NULL
```

```text
above_20dma  = adj_close_t > SMA20_t
above_50dma  = adj_close_t > SMA50_t
above_200dma = adj_close_t > SMA200_t
```

Equality → `false`. Insufficient history → `NULL`.

```text
distance_20dma_pct  = (adj_close_t / SMA20_t)  - 1
distance_50dma_pct  = (adj_close_t / SMA50_t)  - 1
distance_200dma_pct = (adj_close_t / SMA200_t) - 1
```

---

## `volatility_20d`

Annualized realized historical volatility from a 20-trading-day return window:

```text
volatility_20d =
STDDEV_SAMPLE(return_1d for t-19 through t) × sqrt(252)
```

Uses canonical `daily_market_data.return_1d`. Explicit `ddof = 1`. First `return_1d` is NULL, so first valid `volatility_20d` needs 21 price observations → **first 20 rows/symbol NULL**.

## `drawdown_pct`

Identical to Phase 2B `daily_market_data.drawdown_from_high`:

```text
historical_high_t = MAX(adj_close through t)
drawdown_pct = (adj_close_t / historical_high_t) - 1
```

Implementation copies/reuses `drawdown_from_high` so `asset_regimes` remains query-complete. Deliberate duplication; not a second concept.

---

## Regime Classifications

### `trend_regime`

Lowercase: `uptrend` | `downtrend` | `neutral`

```text
if SMA50_t IS NULL or SMA200_t IS NULL:
    NULL
elif adj_close_t > SMA200_t and SMA50_t > SMA200_t:
    "uptrend"
elif adj_close_t < SMA200_t and SMA50_t < SMA200_t:
    "downtrend"
else:
    "neutral"
```

Equality falls into `neutral`. Semantic historical-state classification — not tuned against future returns.

### `momentum_regime`

Lowercase: `positive` | `negative` | `mixed`

```text
if return_20d IS NULL or return_60d IS NULL:
    NULL
elif return_20d > 0 and return_60d > 0:
    "positive"
elif return_20d < 0 and return_60d < 0:
    "negative"
else:
    "mixed"
```

Zero belongs to `mixed`. No magnitude thresholds.

### `volatility_regime`

Lowercase: `low` | `normal` | `high`

Expanding same-symbol empirical distribution of `volatility_20d` with `date ≤ t` (**current included**). Require `|H_t| ≥ 252`, else `NULL`.

```text
p_t = count(h in H_t where h <= volatility_20d_t) / |H_t|

p_t <= 1/3           → "low"
1/3 < p_t <= 2/3     → "normal"
p_t > 2/3            → "high"
```

Semantic equal-frequency categories. Never use future volatility, full-sample ranks, or `market_outcomes`.

---

# 5. `macro_conditions`

One row per `trading_days.date`. Values on date `t` use only information publicly available by `t`.

**Phase 4A contract:** `StockBallDB_phase4a_macro_contract.md` (authoritative source/PIT/alignment lock).

**PMI:** **UNRESOLVED** — deferred from V1; column omitted (no satisfactory freely reproducible source).

## Units (Phase 4A lock)

Macro **rate/spread/YoY** fields use **percentage points** (`3.0` = 3%), not decimal `0.03`. Jobless claims = persons; WALCL = millions USD.

## Series map (locked)

| Field | Series | Notes |
| --- | --- | --- |
| `inflation_rate` | CPIAUCSL | Headline CPI YoY % from PIT index levels |
| `core_inflation_rate` | CPILFESL | Core CPI YoY % from PIT index levels |
| `unemployment_rate` | UNRATE | SA percent; ALFRED PIT |
| `jobless_claims` | ICSA | Initial claims, SA, persons; ALFRED PIT (sparse vintages before ~2009) |
| `fed_funds_rate` | DFF | Effective federal funds rate, % |
| `treasury_2y_yield` | DGS2 | %; no history before 1976-06-01 |
| `treasury_10y_yield` | DGS10 | % |
| `fed_balance_sheet` | WALCL | Total Fed assets, millions USD |
| `credit_spread` | BAA10Y | Baa − 10Y Treasury, %; current FRED only (see Phase 4A caveats) |

## Availability & forward-fill

- Reference period ≠ availability. No pre-release leakage.
- Pre-open releases (CPI/employment/claims): first trading day on/after release calendar date.
- After-close (H.4.1 / WALCL): Wednesday level → Thursday release calendar → first trading day **strictly after** that Thursday.
- Ambiguous timing → next trading day (conservative).
- Forward-fill after availability: inflation, core, unemployment, claims, balance sheet.
- **No** forward-fill: fed funds, Treasuries, credit spread.

## `yield_curve_10y_2y`

```text
treasury_10y_yield - treasury_2y_yield
```

Percentage points (`1.00` = 100 bp). NULL if either leg NULL. Derived in StockBallDB (not `T10Y2Y`).

## `inflation_regime` / `rate_regime`

**Phase 4A scope:** observed inputs only — regime definitions are **not re-locked** in Phase 4A. Below documents existing V1 behavior for reference; deliberate redesign is a future phase.

### `inflation_regime`

`low` | `normal` | `high`

`H_t` = distinct PIT headline CPI YoY **releases** with availability ≤ `t` (each monthly release once — not daily forward-filled duplicates). Require `|H_t| ≥ 36`. Then empirical terciles of current `inflation_rate` vs `H_t`. Regime carries with the inflation observation until the next release.

### `rate_regime`

`easing` | `stable` | `tightening`

```text
delta = fed_funds_rate_t - fed_funds_rate_{t-63}
```

where `t-63` is the 63rd previous **non-NULL** `fed_funds_rate` observation.  
`delta ≤ -0.25` → easing; `≥ +0.25` → tightening; else stable. Effective-rate stance proxy (not FOMC target).

---

# 6. `scheduled_events`

**Responsibility:** scheduled-event **occurrence calendar** of intrinsic event facts.

A row records a trustworthy scheduled event occurrence reconstructed from authoritative historical sources.

Historical **occurrence** is generally reconstructible. Complete historical reconstruction of when every future event date first became known to market participants is **outside V1**.

Not a surprise/result warehouse, not `macro_conditions` state, not trading-day features (`calendar_context`), and not an unscheduled-catalyst table.

## `event_id`

Deterministic, provider-independent, stable across rebuilds:

```text
{event_type}:{event_date}:{reference_period_or_NA}:{symbol_or_MARKET}
```

Examples: `fomc:2020-04-29:NA:MARKET`, `cpi:2020-03-11:2020-02:MARKET`,
`employment_situation:2020-03-06:2020-02:MARKET`,
`election:2020-11-03:presidential:MARKET`.

## `event_type` (V1 vocabulary)

| Type | Meaning |
| --- | --- |
| `fomc` | Regularly scheduled FOMC meeting **policy-decision / statement day** (final day of multi-day meeting). Unscheduled/emergency, conference calls, notation votes, cancelled meetings **excluded**. |
| `cpi` | BLS CPI **news-release occurrence** for a reference month (first-print date). Values live in `macro_conditions`, not here. |
| `employment_situation` | BLS Employment Situation **news-release occurrence** (not ICSA/jobless claims). |
| `election` | U.S. presidential or midterm **general Election Day** only. |

**Deferred:** `earnings`; unscheduled Fed actions; consensus expectations; surprise values; `importance` ratings.

Phase 6A PIT contract: `StockBallDB_phase6a_scheduled_events_contract.md` — occurrence vs reference period, timezone rules, schedule-revision limits, Phase 6B readiness.

Do not use ambiguous `jobs`.

## `event_date`

Calendar date of the occurrence. **Not** required to be a `trading_days` date. No FK to `trading_days`.

## `symbol`

V1: always `NULL` (market-wide). Never fan out one macro/Fed/election event across ETFs. Nullable for future symbol-specific types.

## `reference_period`

- CPI / Employment Situation: `YYYY-MM` (reference month)
- Election: `presidential` | `midterm`
- FOMC: `NULL` (encoded as `NA` in `event_id`)

## `release_session` / `event_time_et`

| Type | Session | Time |
| --- | --- | --- |
| CPI / Employment Situation from 1990-01-01 | `pre_open` | `08:30` ET when convention is treated as justified; else time `NULL` |
| CPI / Employment Situation before 1990-01-01 | `pre_open` | `NULL` |
| FOMC from 2013-03-20 | `during_session` | `14:00` ET (Fed 2013-03-13 standardization) |
| FOMC before 2013-03-20 | `unknown` | `NULL` (do not infer modern convention) |
| Election | `unknown` | `NULL` (all-day statutory event) |

## Coverage semantics

No “no-event” rows. Within validated coverage for a type, absence ⇒ no qualifying scheduled event. Outside coverage ⇒ unknown/incomplete — not “no event.”

## Relationship boundaries

- `macro_conditions`: PIT macro **state** on trading days (levels/regimes).
- `calendar_context`: trading-day-relative holiday/session/transition context and retrospective `days_since_last_*` (forward `days_to_next_*` deferred).

---

# 7. `calendar_context`

One row per `trading_days.date` (exact 1:1). Deterministic trading-day context derived from `trading_days`, pinned NYSE calendar metadata, and `scheduled_events`.

**Phase 7A contract:** `StockBallDB_phase7a_calendar_context_contract.md` — authoritative audit, boundary, effective-session rules, PIT classification.

**Not in V1:** `days_to_next_*`, `days_to_tax_deadline`, `is_payday_period`, `is_election_period`, earnings windows, broad pre/post event windows.

## Holiday / session

**Holiday/full closure:** Mon–Fri calendar date with no `trading_days` row. Weekends alone are not holidays.

**`is_day_before_holiday`:** true iff ∃ weekday closed date strictly between `date` and `next_trading_date`.

**`is_day_after_holiday`:** symmetric using `prev_trading_date`.

**`holiday_name`:** adjacent weekday closure label(s) from NYSE rules / adhoc; multiple distinct labels joined with `|` in chronological order; `NULL` when neither before nor after.

**`holiday_type`:** `regular` | `exceptional` | `NULL`. Any exceptional closure in the adjacent gap → `exceptional`.

**`is_shortened_trading_day`:** membership in `nyse.early_closes(schedule)` (pinned `pandas_market_calendars` NYSE). Full closures are not shortened sessions.

## Week

ISO 8601 identity: `(iso_year, iso_week) = date.isocalendar()[:2]` — **not** `(trading_days.year, week_of_year)`.

`trading_days_in_week` = count of trading sessions in that ISO week (1–5). Half-sessions count as one day.  
`is_shortened_week` = `trading_days_in_week < 5`.

## Narrow transitions

```text
is_turn_of_month =
  is_month_end OR trading_day_of_month = 1

is_quarter_transition =
  is_quarter_end OR first trading session of calendar quarter

is_year_transition =
  is_year_end OR first trading session of calendar year
```

## Event context (retrospective)

**`is_*_day`:** true iff `scheduled_events` has matching `event_type` with `event_date = date`. Occurrence on this trading date only — off-calendar events do not set flags.

**`days_since_last_*`:** trading-session distance from the event’s **effective session** to `date`.

```text
if event_date is a trading day:
  effective_session = event_date
else:
  effective_session = first trading day strictly after event_date

days_since = index(date) - index(effective_session)   # 0 on effective session
```

`NULL` before the first known event of that type. No future events. No `release_session` remapping.

Forward `days_to_next_*` deferred: Phase 2F is an occurrence calendar, not complete advance-schedule PIT knowledge.

---

# Missing Data and Insufficient History

Observed data that is unavailable from the selected provider must not be fabricated.

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

# Corporate Actions and Historical Continuity

Corporate actions can create discontinuities between raw historical observations that do not represent equivalent economic price movements.

StockBallDB therefore preserves:

```text
raw OHLCV
adjusted OHLCV
dividend_cash
split_factor
```

rather than retaining only one representation of market history.

Raw observations preserve what was reported for the historical trading session.

Adjusted observations provide a normalized historical series based on the provider's adjustment methodology.

Dividend and split fields preserve the underlying corporate-action information separately.

Derived calculations must explicitly define whether they use raw or adjusted observations. This convention must not be left implicit in pipeline code.

---

# Provider Normalization

Provider field names do not define StockBallDB field names.

Provider observations are mapped into canonical StockBallDB fields during normalization.

For Tiingo-sourced ETF observations, the normalized daily dataset includes:

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

The precise mapping between Tiingo API fields and these canonical names belongs in `StockBallDB_sources.md` and/or pipeline configuration.

---

# Definition Changes

Definitions are part of StockBallDB's reproducibility contract.

Changing a formula, price basis, adjustment convention, or classification rule can change historical values even when the underlying observed data has not changed.

Therefore, material definition changes must be:

1. deliberate;
2. documented;
3. version controlled;
4. reflected in the relevant pipeline;
5. reproducible during a full database rebuild.

During the initial schema-population phase, definitions marked **TBD** should be resolved using actual source data and documented decisions rather than silently assumed.

> **A field name tells us what a value is called. This document tells us exactly what that value means.**
