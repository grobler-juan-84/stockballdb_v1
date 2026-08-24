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
| **EIA**                      | WTI / energy data                                                    | REST API               | API key           | Free                             | Candidate             |
| **Cboe**                     | VIX                                                                  | Historical data        | Dataset dependent | Public historical data available | Future                |
| **Gold source**              | XAU/USD                                                              | TBD                    | TBD               | TBD                              | Research required     |
| **DXY source**               | U.S. Dollar Index                                                    | TBD                    | TBD               | TBD                              | Research required     |
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

Tiingo's provider-specific field names are normalized into StockBallDB's canonical naming convention.

Conceptually:

| Tiingo observation | StockBallDB field |
| ------------------ | ----------------- |
| `open`             | `open`            |
| `high`             | `high`            |
| `low`              | `low`             |
| `close`            | `close`           |
| `volume`           | `volume`          |
| adjusted open      | `adj_open`        |
| adjusted high      | `adj_high`        |
| adjusted low       | `adj_low`         |
| adjusted close     | `adj_close`       |
| adjusted volume    | `adj_volume`      |
| dividend cash      | `dividend_cash`   |
| split factor       | `split_factor`    |

The acquisition implementation should verify the exact Tiingo API field names before the mapping is locked into pipeline configuration.

## Raw vs Adjusted

Raw observations represent prices and volume as reported for the historical trading session.

Adjusted observations normalize historical values according to Tiingo's corporate-action adjustment methodology.

For example, a stock split may cause raw historical prices before and after the split to appear discontinuous even though the split itself did not represent an equivalent economic loss.

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

This allows future calculations to explicitly choose the appropriate price basis rather than permanently discarding one representation.

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

inflation_rate           → <series_id>
unemployment_rate        → <series_id>
fed_funds_rate           → <series_id>
treasury_10y_yield       → <series_id>
```

Exact series IDs should be documented once individually reviewed.

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
**Access:** Exchange calendar logic + authoritative exchange verification
**Authentication:** None for normal local generation
**Tier:** Free
**Status:** Primary

The StockBallDB trading calendar must not depend on the existence of a particular ETF such as SPY.

The calendar begins in **1957** according to the scope established in the manifesto.

Initial approach:

```text
Exchange calendar logic
        ↓
Generate trading-day spine
        ↓
Verify holidays / exceptional closures
        ↓
Validate
        ↓
Store in trading_days
```

NYSE information should be used where authoritative verification is necessary, particularly for:

* market holidays;
* shortened trading sessions;
* exceptional market closures;
* unusual historical calendar behavior.

The trading-day spine remains independent from Tiingo or any other market-price provider.

---

# 5. WTI Crude Oil

**Identifier:** `WTI`
**Preferred sources:** FRED / EIA
**Access:** REST API
**Authentication:** FRED or EIA API key
**Tier:** Free
**Status:** Provisional

FRED and the U.S. Energy Information Administration are the preferred candidates.

If EIA is selected:

```text
EIA_API_KEY=<secret>
```

Before locking the source, StockBallDB should define precisely which WTI observation is represented and ensure sufficient consistency and historical coverage.

Selection priorities:

* long historical coverage;
* consistent definition;
* reliable daily observations;
* reproducible automated acquisition.

The FRED and EIA alternatives should be compared before the canonical series is selected.

---

# 6. Spot Gold

**Identifier:** `XAU/USD`
**Access:** TBD
**Authentication:** TBD
**Tier:** TBD
**Status:** Research required

A canonical source has not yet been selected.

StockBallDB must first define exactly what constitutes the daily gold observation.

Potential definitions include a recognized reference price or a consistent daily spot-market observation.

The selected source should provide:

* long historical coverage;
* clear price definition;
* consistent methodology;
* daily observations where possible;
* reproducible acquisition.

ETF proxies such as GLD should not replace spot gold merely because they are easier to acquire.

---

# 7. U.S. Dollar Index

**Identifier:** `DXY`
**Access:** TBD
**Authentication:** TBD
**Tier:** TBD
**Status:** Research required

A canonical source has not yet been selected.

The official U.S. Dollar Index and alternative broad dollar indices are not automatically interchangeable.

Before implementation, StockBallDB must determine:

* which dollar index is intended;
* authoritative historical source;
* available historical coverage;
* licensing / access limitations;
* whether automated acquisition is practical.

A substitute dollar index must not silently be labelled `DXY`.

---

# 8. Federal Reserve Events

**Primary responsibility:** FOMC and Federal Reserve events
**Primary source:** Federal Reserve
**Access:** Public Federal Reserve data / APIs where available
**Tier:** Free
**Status:** Authoritative

Potential events include:

```text
FOMC meetings
interest-rate decisions
scheduled Federal Reserve announcements
```

These records may populate `scheduled_events`.

The Federal Reserve should be treated as the source of truth for its own events.

FRED may supplement the original source where useful, but StockBallDB should avoid unnecessary scraping when a stable structured source exists.

The acquisition method may differ by dataset and should be documented when implemented.

---

# 9. Economic Releases

**Preferred source:** Original publishing agency / FRED
**Access:** Dataset dependent
**Tier:** Primarily free
**Status:** Provisional

Potential releases include:

```text
CPI
PPI
employment report
jobless claims
GDP
PMI
retail sales
other major scheduled economic releases
```

The institution responsible for the release is the preferred authority where practical.

FRED release metadata may provide a reproducible acquisition path where sufficiently reliable.

StockBallDB must distinguish:

```text
reference period
release date
release time
data availability
later revisions
```

These concepts must not be treated as interchangeable.

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
* **Trading calendar** — generated independently of ETF price history and verified against authoritative exchange information.
* **Federal Reserve** — preferred authority for Federal Reserve events.
* **StockBallDB** — calculates deterministic derived fields internally.
* **API credentials** — environment configuration only; never committed to Git.

## Provisional

* **WTI** — FRED / EIA.
* **Economic release calendar** — original agencies supplemented by FRED where appropriate.

## Requires Research

* **XAU/USD / Spot Gold**
* **DXY / U.S. Dollar Index**
* Exact FRED / ALFRED series IDs for `macro_conditions`
* Fallback provider for ETF market data
* Exact source and acquisition method for each `scheduled_events` category
* Exact canonical handling of Tiingo no-dividend and no-split observations
* Exact raw-versus-adjusted price basis for StockBallDB derived market fields

---

# Evolution

This document is a source map, not a permanent provider contract.

Sources may change when better data becomes available, providers alter access, historical weaknesses are discovered, or StockBallDB expands.

The initial table-population phase should also be used to test these source decisions against real provider data. Findings may justify adding, removing, or changing fields before the V1 schema is considered mature.

Provider changes must preserve the principles established in the manifesto:

**Correctness → Reproducibility → Coverage → Data quality → Maintainability**

> **The provider supplies the fact. StockBallDB decides how that fact belongs in the database.**
