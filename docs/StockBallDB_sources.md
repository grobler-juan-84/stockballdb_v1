# StockBallDB — Sources

**Version:** 0.02
**Status:** Initial Source Plan
**Last Updated:** 2026-08-24

> Companion docs: [index](StockBallDB_index.md) · [manifesto](StockBallDB_manifesto.md) · [universe](StockBallDB_universe.md) · [schema](StockBallDB_schema.md)

## Purpose

Defines where StockBallDB obtains observed data, how providers are accessed, and how sources are selected.

StockBallDB does not depend on a single universal provider. Different datasets may have different authoritative sources.

Providers supply facts. StockBallDB owns the schema, normalization, derivation, validation, and storage.

Source selection follows the manifesto:

**Free → Reliable → Automated → Historically sufficient → Reproducible**

A paid source should only be introduced when it provides meaningful value that cannot reasonably be obtained from a free source.

---

## Source Principles

### 1. Prefer authoritative practical sources

Use the most authoritative source that can be acquired reliably and reproducibly.

Direct sources such as exchanges, government agencies, and central banks are preferred when they materially improve accuracy or historical integrity.

Reliable aggregation APIs may be preferred when they substantially simplify automated acquisition without compromising required data quality.

### 2. Providers must remain replaceable

Provider-specific symbols, formats, field names, and API structures belong in the acquisition and normalization layer.

They must not dictate the StockBallDB schema.

```text
Provider
    ↓
Fetch
    ↓
Normalize
    ↓
Validate
    ↓
StockBallDB Schema
```

Changing a provider should not require redesigning the database.

### 3. Preserve provenance

For observed data, StockBallDB should be able to determine where the value originated.

Where appropriate, document:

* provider;
* provider series / ticker;
* retrieval method;
* historical coverage;
* frequency;
* known limitations;
* adjustment methodology;
* revision behavior;
* point-in-time considerations.

### 4. Historical integrity takes priority

The newest known historical value is not always the value that was known at the time.

For datasets subject to revisions, StockBallDB should use vintage or point-in-time data when historical reconstruction requires it.

For market data, raw and adjusted observations must remain distinguishable.

### 5. Derived data belongs to StockBallDB

If a value can be deterministically calculated from reliable underlying observations, prefer storing the underlying facts and deriving the value ourselves.

Examples include returns, moving averages, drawdowns, volatility, regimes, forward outcomes, and calendar flags.

Provider-supplied adjusted market observations are an exception to this general principle because adjustment methodology incorporates corporate-action information and is useful as an independently supplied historical representation.

StockBallDB therefore preserves both raw and adjusted market observations where available.

### 6. Fetch related observations together when practical

When a provider supplies multiple required observations through the same acquisition request, StockBallDB should collect them together rather than deliberately discarding fields and retrieving them through separate workflow stages later.

This reduces unnecessary API calls and keeps acquisition workflows simpler and more reproducible.

---

# Provider Overview

| Provider / Source            | Primary Use                                                          | Access                 | Authentication    | Tier                             | Status                |
| ---------------------------- | -------------------------------------------------------------------- | ---------------------- | ----------------- | -------------------------------- | --------------------- |
| **Tiingo**                   | ETF raw/adjusted daily market data and corporate-action observations | REST API               | API token         | Free tier available              | Primary               |
| **FRED**                     | Macro / monetary data                                                | REST API               | API key           | Free                             | Primary               |
| **ALFRED**                   | Historical macro vintages                                            | FRED API               | API key           | Free                             | Primary when required |
| **NYSE / exchange calendar** | Trading calendar verification                                        | Public data / calendar | Usually none      | Free                             | Primary verification  |
| **Federal Reserve**          | FOMC / Fed events                                                    | Public data / APIs     | Dataset dependent | Free                             | Authoritative         |
| **EIA**                      | WTI fallback (`PET.RWTC.D`)                                          | REST API               | API key           | Free                             | WTI fallback          |
| **Cboe**                     | VIX                                                                  | Historical data        | Dataset dependent | Public historical data available | Future                |
| **ICE Data Indices**         | DXY (US Dollar Index)                                                | Commercial API         | License           | Paid                             | **Unresolved**        |
| **IBA / LBMA**               | XAU/USD gold benchmark                                               | Licensed               | License           | Paid                             | **Unresolved**        |
| **StockBallDB**              | Derived fields                                                       | Internal calculation   | —                 | Free                             | Internal              |

Provider pricing, limits, and access policies can change. Values recorded here describe the provider at the time of the documented decision and should be rechecked before upgrades or licensing decisions.

---

# 1. Tiingo

**Primary responsibility:** ETF daily market observations, adjusted observations, and corporate-action observations
**Access:** REST API
**Authentication:** API token
**Tier:** Free tier available
**Status:** Primary

Tiingo is the initial provider for daily ETF market data.

Initial coverage:

```text
SPY   QQQ   IWM

XLB   XLC   XLE   XLF
XLI   XLK   XLP   XLU
XLV   XLY   XLRE
```

## V1 Tiingo Observations

StockBallDB V1 collects the complete set of currently required Tiingo daily observations during the same acquisition step.

### Raw OHLCV

```text
open
high
low
close
volume
```

OHLCV means:

```text
Open
High
Low
Close
Volume
```

These fields preserve the raw historical market observations.

### Adjusted OHLCV

```text
adj_open
adj_high
adj_low
adj_close
adj_volume
```

These observations provide historical prices and volume adjusted according to Tiingo's applicable corporate-action methodology.

Raw and adjusted observations are intentionally retained separately.

### Corporate Actions

```text
dividend_cash
split_factor
```

These fields preserve dividend and split information supplied alongside the daily market observations.

They should not be reconstructed from adjusted prices when the underlying observations are already available directly from Tiingo.

## Canonical Field Mapping

Verified against live Tiingo EOD JSON (`GET /tiingo/daily/{ticker}/prices`) on 2026-08-27:

| Tiingo field   | StockBallDB field |
| -------------- | ----------------- |
| `date`         | `date`            |
| `open`         | `open`            |
| `high`         | `high`            |
| `low`          | `low`             |
| `close`        | `close`           |
| `volume`       | `volume`          |
| `adjOpen`      | `adj_open`        |
| `adjHigh`      | `adj_high`        |
| `adjLow`       | `adj_low`         |
| `adjClose`     | `adj_close`       |
| `adjVolume`    | `adj_volume`      |
| `divCash`      | `dividend_cash`   |
| `splitFactor`  | `split_factor`    |

**Request note:** omitting `startDate` returns only the latest bar. Phase 2A requests `startDate=1957-01-01` so each ETF returns its full available history (actual first observation is ETF-dependent).

**Auth:** `Authorization: Token <TIINGO_API_KEY>`.

## Raw vs Adjusted

Raw observations represent prices and volume as reported for the historical trading session (quoted prints).

Adjusted observations normalize historical values according to Tiingo's corporate-action adjustment methodology. Tiingo’s `adj_*` series is **restated**: corporate actions after historical date *t* can change the adjusted values stored for *t*.

StockBallDB therefore preserves:

```text
raw OHLCV
+
adjusted OHLCV
+
dividend information
+
split information
```

**Integrity distinction (locked):**

* raw OHLCV = historical quoted market observations;
* Tiingo adjusted OHLCV = retrospectively normalized historical representation;
* derived fields that use adjusted prices = retrospectively normalized economic history;
* those derived fields must **not** be described as values that were necessarily available in that adjusted form on the historical date.

### Corporate-action stored values (locked)

```text
dividend_cash = 0.0  → no cash dividend reported for the bar
split_factor  = 1.0  → no split reported for the bar
NULL                 → missing / unknown / not supplied
```

Storage mirrors the provider; StockBallDB does not rewrite `0.0`/`1.0` to `NULL`.

## Acquisition Rule

The V1 Tiingo acquisition should retrieve all required daily observations together.

Conceptually:

```text
Tiingo API
    ↓
Single ETF daily-data acquisition stage
    ↓
Raw OHLCV
Adjusted OHLCV
Dividend cash
Split factor
    ↓
Normalize
    ↓
Validate
    ↓
daily_market_data
```

StockBallDB should not intentionally retrieve only raw OHLCV during one workflow stage and return to Tiingo later for adjusted observations that could have been acquired during the same stage.

This rule simplifies:

```text
Build
Update
Validate
Rebuild
```

and reduces unnecessary provider interaction.

## Connection

Create a Tiingo account and obtain an API token.

Store the credential locally:

```text
TIINGO_API_KEY=<secret>
```

StockBallDB accesses Tiingo through HTTPS REST requests.

```text
StockBallDB
    ↓
Tiingo API
    ↓
Raw provider response
    ↓
Normalize
    ↓
Validate
    ↓
Store
```

## Tier

The initial free tier is expected to be sufficient for StockBallDB's small Version 1 ETF universe.

The active ETF universe currently contains 14 Tiingo-sourced ETFs, leaving substantial room relative to the free tier for future expansion.

Provider limits must nevertheless be treated as operational configuration rather than permanent assumptions.

They should be checked before major universe expansion or full rebuild workflows.

## Additional Tiingo Data

Tiingo may provide additional datasets or metadata beyond the fields currently included in StockBallDB V1.

Potential examples include:

```text
security metadata
additional stocks and ETFs
forex
cryptocurrency
intraday market data
additional corporate-action information
```

Availability does not automatically justify inclusion.

These should be evaluated during future schema reviews according to the StockBallDB source-selection criteria.

V1 deliberately collects the inexpensive underlying daily observations already required for the current universe without expanding the database simply because additional Tiingo data exists.

## Rule

Tiingo is a provider, not the definition of market data.

If Tiingo is replaced later, the canonical StockBallDB schema should remain unchanged wherever practical.

---

# 2. FRED

**Primary responsibility:** Macroeconomic and monetary data
**Access:** REST API
**Authentication:** API key
**Tier:** Free
**Status:** Primary

FRED is the preferred initial provider for much of `macro_conditions`.

Expected categories include:

```text
inflation
core inflation
unemployment
jobless claims
Federal Funds rate
2-year Treasury yield
10-year Treasury yield
Federal Reserve balance sheet
credit spreads
```

Additional series may be introduced as StockBallDB expands.

## Connection

Create a FRED account and obtain an API key.

```text
FRED_API_KEY=<secret>
```

StockBallDB accesses FRED through its HTTPS REST API.

```text
StockBallDB
    ↓
FRED API
    ↓
Series observations
    ↓
Normalize
    ↓
Align
    ↓
Validate
    ↓
Store
```

Each StockBallDB macro field should eventually map to an explicitly approved FRED series ID.

```text
StockBallDB field        → FRED series

inflation_rate           → CPIAUCSL (PIT index → YoY %)
core_inflation_rate      → CPILFESL (PIT index → YoY %)
unemployment_rate        → UNRATE (ALFRED PIT)
jobless_claims           → ICSA (ALFRED PIT; sparse vintages before ~2009)
fed_funds_rate           → DFF
treasury_2y_yield        → DGS2
treasury_10y_yield       → DGS10
fed_balance_sheet        → WALCL
credit_spread            → BAA10Y (LOCKED Phase 4A; current FRED daily; see caveats)
```

`pmi` — **UNRESOLVED** (no column in V1). ISM PMI removed from FRED; no alternative meets free reproducible automatable requirements. See `StockBallDB_phase4a_macro_contract.md` §6.

**Phase 4A authoritative contract:** `StockBallDB_phase4a_macro_contract.md` — field matrix, PIT rules, alignment, units, unresolved items.

`yield_curve_10y_2y` is derived in StockBallDB as `treasury_10y_yield - treasury_2y_yield`.

## Original-source verification

FRED aggregates information originating from institutions including:

```text
Federal Reserve
U.S. Treasury
Bureau of Labor Statistics
Bureau of Economic Analysis
Energy Information Administration
```

The originating institution may be used for verification where necessary, while FRED provides a consistent automated acquisition interface.

---

# 3. ALFRED

**Primary responsibility:** Point-in-time macroeconomic history
**Access:** FRED API
**Authentication:** FRED API key
**Tier:** Free
**Status:** Primary when historical vintages matter

Economic statistics are frequently revised after their original publication.

StockBallDB must distinguish:

```text
What is currently known about a historical period

vs.

What was publicly known on that historical date
```

Where that distinction materially affects historical research, ALFRED should be used to obtain or reconstruct vintage data.

This is especially relevant to datasets such as:

```text
employment
inflation
GDP
other revised economic indicators
```

## Connection

ALFRED data is available through the FRED API infrastructure.

The existing credential can therefore be reused:

```text
FRED_API_KEY=<secret>
```

Conceptually:

```text
FRED API
   ├── Current historical series → FRED
   │
   └── Historical vintages → ALFRED
```

ALFRED should be preferred whenever using today's revised history would introduce look-ahead bias.

---

# 4. Trading Calendar

**Primary responsibility:** `trading_days`
**Access:** Local generation via pinned `pandas_market_calendars` (`NYSE`)
**Authentication:** None
**Tier:** Free (Python package)
**Status:** Primary / Locked for Phase 1

The StockBallDB trading calendar must not depend on the existence of a particular ETF such as SPY.

The calendar begins in **1957** according to the scope established in the manifesto.

**Calendar authority:** `pandas_market_calendars==5.4.0` (pin upgrades deliberately; treat version changes as reviewed events).

```text
pandas_market_calendars NYSE
        ↓
Generate trading-day spine (1957 → last session ≤ today America/New_York)
        ↓
Derive columns (ISO week, ordinals, prev/next, period-end flags)
        ↓
Upsert into trading_days (idempotent)
        ↓
Validate (spot closures/sessions + structural checks)
```

NYSE holiday rules, historical rule changes, exceptional full closures, and early-close sessions are taken from the pinned library. Shortened sessions remain valid `trading_days` rows; early-close and holiday-adjacency flags live in `calendar_context` (Phase 2G). Same authority — no second calendar source.

The trading-day spine remains independent from Tiingo or any other market-price provider.

---

# 5. WTI Crude Oil

**Identifier:** `WTI`  
**Phase 5A status:** **LOCKED**

**Canonical definition:** Daily WTI **spot** crude at Cushing, Oklahoma (FOB cash/reference market) — not NYMEX CL futures, not USO.

**Source:** FRED **DCOILWTICO** (U.S. EIA spot prices; dollars per barrel).  
**Fallback (equivalent):** EIA API `PET.RWTC.D` via `EIA_API_KEY` if needed.

**Coverage:** from **1986-01-02**; pre-inception NULL on `trading_days` spine.  
**Date semantics:** observation date; align to `trading_days` only when obs date is a trading day; no forward-fill.

Authoritative detail: `StockBallDB_phase5a_market_context_contract.md` §4.

---

# 6. Spot Gold

**Identifier:** `XAU/USD`  
**Phase 5A status:** **UNRESOLVED** (definition locked; source not locked)

**Canonical definition:** USD **spot gold** per troy ounce — institutional benchmark (target: **LBMA Gold Price PM fix**), not GLD/COMEX futures.

**Source:** No free reproducible FRED/API path remains after ICE removed LBMA series from FRED (2022). IBA/LBMA license required for authoritative automated history.

ETF proxies (GLD) and futures substitutes are **not** acceptable as canonical XAU/USD.

Authoritative detail: `StockBallDB_phase5a_market_context_contract.md` §5.

---

# 7. U.S. Dollar Index

**Identifier:** `DXY`  
**Phase 5A status:** **UNRESOLVED**

**Canonical definition:** ICE **U.S. Dollar Index (USDX)** — not Fed trade-weighted indexes (**DTWEXBGS** / **DTWEXAFEGS**), not UUP ETF.

**Source:** ICE Data Indices (commercial license). No acceptable free FRED substitute that equals DXY.

Do not label DTWEX* series as `DXY`.

Authoritative detail: `StockBallDB_phase5a_market_context_contract.md` §6.

---

# 8. Federal Reserve Events

**Primary responsibility:** Scheduled FOMC meeting decision/statement days for `scheduled_events`
**Primary source:** Federal Reserve
**Access:** Public HTML historical materials / calendars
**Tier:** Free
**Status:** Locked (Phase 2F)

Acquisition:

* Years **1957–2020:** `https://www.federalreserve.gov/monetarypolicy/fomchistorical{YYYY}.htm`
* Years **2021+:** `https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm`

Include only headings/rows that are regularly scheduled **Meetings**. Exclude **unscheduled**, **conference call**, **notation vote**, and **cancelled**.

Multi-day meetings → one event on the **final** day.

`event_time_et = 14:00` / `during_session` only from **2013-03-20** onward (Fed Board release 2013-03-13). Earlier FOMC timing remains `unknown`.

Unscheduled/emergency Fed actions are **deferred** (not V1 `scheduled_events`).

---

# 9. Economic Releases

**Preferred source:** BLS via ALFRED first-print dates (FRED API)
**Access:** `FRED_API_KEY`
**Tier:** Free
**Status:** Locked (Phase 2F) for CPI and Employment Situation occurrence dates

| Event type | Series for first-print dates | FRED release id (context) | Notes |
| --- | --- | --- | --- |
| `cpi` | CPIAUCSL | 10 | First `realtime_start` per reference month; revisions are not new events |
| `employment_situation` | UNRATE | 50 | Same Employment Situation release; not ICSA |

Store occurrence facts only. Macro **values** remain in `macro_conditions`.

Consensus expectations and surprise values are **deferred** (no free reproducible market-consensus history approved for V1).

BLS `08:30` ET / `pre_open`: applied from **1990-01-01**; earlier releases keep `pre_open` with `event_time_et = NULL`.

**Elections:** statutory federal Election Day (2 U.S.C. §7 / USA.gov / FEC) — presidential (`year % 4 == 0`) and midterm (`year % 4 == 2`) only. `release_session = unknown`, `event_time_et = NULL`.

**Earnings:** deferred from V1 (ETF universe; no approved scheduled-date + consensus pipeline).

Phase 6A contract (`StockBallDB_phase6a_scheduled_events_contract.md`): **`actual`**, **`consensus`**, **`surprise`**, and **`importance`** are **rejected** — not in schema. Jobless claims **provisionally locked** for Phase 6B; GDP and other releases **deferred**.

---

# 10. VIX

**Status:** Future candidate
**Preferred source:** Cboe
**Secondary source:** FRED
**Tier:** Public historical data available

VIX is not part of the initial Version 1 universe but is a likely future addition.

Because Cboe creates and maintains the VIX methodology, Cboe should be considered the preferred authoritative source.

If VIX enters the active universe, its exact acquisition method, licensing restrictions, update process, and historical coverage should be reviewed before ingestion.

---

# Derived Data

The following categories should normally be calculated internally rather than sourced from external providers:

```text
daily returns
multi-day returns
gaps
intraday returns
ranges
drawdowns

moving averages
distance from moving averages
momentum
historical volatility

trend regimes
momentum regimes
volatility regimes

forward returns
maximum favorable movement
maximum adverse movement

month / quarter / year transitions
trading-day counters
calendar-derived flags
```

Definitions and formulas belong in `StockBallDB_definitions.md`.

Adjusted OHLCV is **not** treated as a StockBallDB-derived category. It is preserved as provider-supplied observed data alongside raw OHLCV and corporate-action observations.

---

# Secrets and Configuration

API credentials must never be hard-coded into pipelines or committed to Git.

Local credentials should live in environment configuration:

```text
TIINGO_API_KEY=...
FRED_API_KEY=...
EIA_API_KEY=...
```

The repository may provide:

```text
.env.example
```

containing empty placeholders:

```text
TIINGO_API_KEY=
FRED_API_KEY=
EIA_API_KEY=
```

The real environment file must remain excluded through `.gitignore`.

This supports the reproducibility principle:

```text
Clone repository
      ↓
Supply credentials
      ↓
Build
      ↓
Fetch
      ↓
Normalize
      ↓
Derive
      ↓
Validate
      ↓
StockBallDB ready
```

A reproducible database must not depend on undocumented credentials, manually downloaded mystery files, or secrets stored inside source code.

---

# Source Selection Checklist

Before adding a provider or series, evaluate:

1. **Authority** — Who originally creates the information?
2. **Accuracy** — Is the dataset sufficiently reliable?
3. **Historical coverage** — Does it cover the required period?
4. **Definition stability** — Has the meaning of the series changed?
5. **Frequency** — Does the available frequency meet the requirement?
6. **Automation** — Can it be fetched reproducibly?
7. **Revision history** — Could revisions introduce future information?
8. **Availability** — Is the source likely to remain accessible?
9. **Cost** — Is a free source sufficient?
10. **Replaceability** — Could another provider replace it without redesigning StockBallDB?
11. **Workflow efficiency** — Can related required observations be acquired together without unnecessary repeat provider calls?

---

# Provider Tier Rule

Provider tiers are operational details, not database architecture.

```text
FREE SOURCE / TIER
        ↓
Reliable?
        ↓
Sufficient history?
        ↓
Automatable?
        ↓
Limits sufficient?
        ↓
      YES
        ↓
      USE IT

       NO
        ↓
Evaluate replacement
or paid tier
```

Moving from a free source or tier to a paid provider should ideally require only acquisition/configuration changes — **not schema changes**.

---

# Current Decisions

## Locked

* **Tiingo** — initial ETF provider for raw OHLCV, adjusted OHLCV, dividend cash, and split factors.
* **Tiingo acquisition** — required V1 daily ETF observations should be collected together during the same acquisition stage rather than split across separate workflow stages.
* **Raw and adjusted market observations** — both are preserved.
* **Corporate-action observations** — dividend cash and split factors are preserved separately from adjusted prices.
* **FRED** — primary macroeconomic data provider.
* **ALFRED** — point-in-time macro / vintage data where required.
* **Trading calendar** — generated with pinned `pandas_market_calendars` (`NYSE`), independently of ETF price history; spot-validated against known NYSE closures/sessions.
* **Federal Reserve** — preferred authority for Federal Reserve events.
* **StockBallDB** — calculates deterministic derived fields internally.
* **API credentials** — environment configuration only; never committed to Git.
* **`scheduled_events` V1** — occurrence calendar for `fomc`, `cpi`, `employment_situation`, `election` only (Phase 2F). Earnings, unscheduled Fed actions, consensus/surprise deferred. No `event_date` FK to `trading_days`.
* **WTI** — FRED `DCOILWTICO` (EIA Cushing spot, USD/bbl, from 1986-01-02); Phase 5A — see `StockBallDB_phase5a_market_context_contract.md`

## Provisional

* *(none)*

## Unresolved (Phase 5A)

* **XAU/USD** — definition locked (LBMA PM fix target); source UNRESOLVED (IBA license; FRED LBMA removed 2022)
* **DXY** — definition locked (ICE USDX); source UNRESOLVED (commercial ICE Data; do not substitute DTWEXBGS)

## Requires Research (other)

* **`macro_conditions` Phase 4A contract** — locked; `pmi` **UNRESOLVED**
* Fallback provider for ETF market data
* Exact source and acquisition method for each `scheduled_events` category — **locked** (Phase 2F)
* Exact canonical handling of Tiingo no-dividend and no-split observations — **locked** (0.0 / 1.0 interpretation; storage unchanged)
* Exact raw-versus-adjusted price basis for StockBallDB derived market fields — **locked** (Phase 2B definitions)
* Forward `market_outcomes` use retrospectively adjusted OHLC by design (Phase 2C) — not point-in-time available on `date`
* `asset_regimes` derived only from `daily_market_data` through date `t` (Phase 2D); `asset_type` from StockBallDB universe map

---

# Evolution

This document is a source map, not a permanent provider contract.

Sources may change when better data becomes available, providers alter access, historical weaknesses are discovered, or StockBallDB expands.

The initial table-population phase should also be used to test these source decisions against real provider data. Findings may justify adding, removing, or changing fields before the V1 schema is considered mature.

Provider changes must preserve the principles established in the manifesto:

**Correctness → Reproducibility → Coverage → Data quality → Maintainability**

> **The provider supplies the fact. StockBallDB decides how that fact belongs in the database.**
