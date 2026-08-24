# StockBallDB — Manifesto

**Version 0.02**
**Date:** 2026-08-24

> Companion docs: [index](StockBallDB_index.md) · [universe](StockBallDB_universe.md) · [schema](StockBallDB_schema.md) · [sources](StockBallDB_sources.md) · [definitions](StockBallDB_definitions.md)

## 1. What StockBallDB Is

StockBallDB is a **historical financial and market-context database**.

Its purpose is to:

> **Collect, reconstruct, organize, derive, validate, and preserve the information that describes market conditions as they existed through history.**

It is not a trading system, strategy, prediction engine, or experiment.

StockBallDB does not need to know which patterns will eventually prove useful. Its responsibility is to provide a trustworthy historical foundation upon which future research can be performed.

**StockBallDB is the data foundation. MoneyBallApp is the future research and discovery environment that may use it.**

The database must therefore not be designed around experiments, strategies, or conclusions that do not yet exist.

**Priority: data first.**

Build the historical record before trying to explain it.

---

## 2. The Historical Point-of-Time Principle

StockBallDB should represent the information that **could actually have been known on a given historical date**.

This is fundamental.

If an economic statistic was reported as **4.0% on Day X**, then 4.0% represents the information available to the market on Day X.

If that statistic was later revised to **4.2% on Day Y**, the revision may affect the market from Day Y onward, but it must not silently replace the information available on Day X.

Otherwise StockBallDB would give historical research information that real market participants did not possess.

Therefore:

> **Historical truth for StockBallDB means point-in-time truth, not merely today's best estimate of the past.**

Where data can be revised, StockBallDB should preserve or reconstruct vintages whenever reasonably possible.

Release date, reference period, revision date, and observation date must not be treated as interchangeable concepts.

Future information must never leak backward into historical market conditions.

---

## 3. Observed vs Derived

StockBallDB distinguishes between two fundamental classes of data.

### Observed data

Information obtained from an external source.

Examples:

* prices
* volume
* interest rates
* unemployment
* inflation
* economic releases
* scheduled events

Observed values should preserve sufficient provenance to determine where they came from and, where relevant, **when they became publicly knowable**.

### Derived data

Information calculated deterministically by StockBallDB from observed data.

Examples:

* returns
* moving averages
* drawdowns
* volatility
* market regimes
* calendar flags
* forward outcomes

Prefer storing reliable underlying facts and deriving calculations ourselves when practical.

Every value should ultimately answer:

> **Where did this value come from, and could it have been known at this point in history?**

---

## 4. Historical Integrity Before Convenience

StockBallDB should never make historical data cleaner by making history less truthful.

Not every dataset begins on the same date.

Not every historical observation exists.

Not every series has remained defined identically through time.

Not every value available today was available historically.

Missing information must remain missing when it cannot be reliably established.

Do not fabricate history merely to create complete tables.

Do not silently substitute proxies and label them as the original asset or indicator.

Do not backfill revised information into periods where that revision was not yet known.

When compromises are necessary, they must be explicit and documented.

---

## 5. Preservation and Reproducibility

Reproducibility remains important, but it is subordinate to historical integrity.

A clean StockBallDB installation should be able to recreate an **equivalent historical database from the preserved inputs, definitions, transformations, and project version**.

However, external providers are not guaranteed to return identical historical data forever.

Providers may:

* revise historical observations;
* correct errors;
* alter methodologies;
* change adjusted prices;
* modify APIs;
* remove datasets;
* change licensing or access.

Therefore:

> **The live API is an acquisition source, not necessarily the permanent historical record.**

Where necessary, StockBallDB should preserve immutable source snapshots or equivalent raw inputs used to construct a database version.

This creates two distinct capabilities:

### Build

Construct StockBallDB from approved source data.

### Rebuild

Reconstruct a historical StockBallDB version from preserved source inputs and deterministic transformations.

A future fresh fetch may produce a newer dataset. That does not invalidate the historical snapshot from which an earlier database version was built.

The repository contains the **recipe**.

Snapshots preserve the **ingredients actually used**.

The database is the **result**.

---

## 6. Data Lineage

StockBallDB should make historical values traceable.

Where appropriate, we should be able to determine:

```text
Provider
    ↓
Raw observation / snapshot
    ↓
Normalization
    ↓
Canonical observation
    ↓
Derived calculations
    ↓
Validation
    ↓
StockBallDB
```

For historically sensitive datasets, lineage may also include:

```text
reference period
release date
vintage date
revision date
retrieval date
source snapshot
```

The objective is not metadata for its own sake.

The objective is confidence that StockBallDB can explain **why a value exists and what information it represents**.

---

## 7. Architecture and Providers

**Local PostgreSQL** is the current environment.

**PostgreSQL** is the architecture.

Schema, migrations, pipelines, definitions, snapshots, and configuration should remain portable to other PostgreSQL environments such as hosted PostgreSQL or Supabase.

Providers supply facts.

They do not define StockBallDB.

Provider-specific formats, symbols, naming conventions, and API structures stop at the acquisition and normalization layer.

The canonical schema remains ours.

A provider should be replaceable without redesigning StockBallDB.

Source preference remains:

> **Free → Reliable → Historically correct → Automated → Sufficient coverage → Reproducible**

Pay only when a paid source provides meaningful historical quality, coverage, reliability, or automation that cannot reasonably be achieved otherwise.

---

## 8. Why `trading_days` Begins in 1957

The trading-day spine intentionally extends further back than the initial ETF histories.

That does **not** mean every StockBallDB dataset must begin in 1957.

The calendar begins in 1957 because:

1. **Future datasets may predate SPY's 1993 inception.**
   The foundational calendar should not need rebuilding simply because older assets are introduced.

2. **Earlier market history introduces additional calendar complexity.**
   Going substantially further back introduces periods such as regular Saturday trading and structural differences that StockBallDB does not currently need.

3. **1957 provides a practical modern-market anchor.**
   It provides substantial historical capacity while remaining reasonably comparable with the modern U.S. trading environment.

General principle:

> **Make inexpensive foundational infrastructure broad enough that reasonable future expansion does not require rebuilding the foundation.**

---

## 9. Scope and Evolution

StockBallDB should collect information that could reasonably help describe historical market conditions.

It should not collect data merely because an API makes that data available.

The Version 1 universe and schema are starting points.

They will change as real acquisition, validation, and research expose weaknesses.

Changes are expected.

Uncontrolled changes are not.

Material changes to:

* schema;
* definitions;
* sources;
* normalization;
* historical reconstruction;
* derivation;
* validation

must be deliberate, documented, version-controlled, and reproducible.

StockBallDB should evolve from evidence gathered while building it rather than assumptions about what future research might require.

---

## 10. Snapshots Are Part of the Historical Record

Snapshots are not merely backups.

When source data can change, an immutable snapshot records **the exact source material StockBallDB used at a particular point in its development**.

Snapshots allow us to distinguish:

```text
What the provider returns today

from

What StockBallDB actually used when a database version was built
```

This protects research from silent upstream changes.

Snapshots should be introduced where their value justifies the storage and operational complexity.

Not every trivial or perfectly deterministic source requires permanent raw duplication.

But datasets subject to revision, correction, disappearing history, or point-in-time reconstruction should strongly favor preservation.

---

## 11. Priorities

When principles conflict, StockBallDB should generally prefer:

**Historical integrity → Correctness → Provenance → Reproducibility → Coverage → Data quality → Maintainability → Performance → Interface**

A larger database is not necessarily a better database.

A perfectly complete historical table built using future information is worse than an incomplete table that truthfully represents what was knowable at the time.

---

## 12. Success

StockBallDB succeeds when its historical data can be trusted.

For any historical date, we should eventually be able to ask:

> **What did the market look like on this day, using only information that could reasonably have been known by then?**

And StockBallDB should provide the most accurate answer we can reasonably construct.

It should be:

* historically faithful;
* provenance-clear;
* validated;
* reproducible;
* updatable;
* provider-replaceable;
* portable;
* explicit about missing or uncertain history.

Discovery belongs elsewhere.

StockBallDB's job is to preserve the playing field on which that discovery can happen.

---

# The StockBallDB Rules

**Data before experiments.**

**Historical integrity before convenience.**

**Point-in-time truth before today's revised version of history.**

**Never allow future information to leak backward into historical conditions.**

**Facts before interpretations.**

**Observed and derived data remain distinguishable.**

**Preserve provenance.**

**Preserve historical source snapshots when upstream data can materially change.**

**Never invent unavailable history.**

**Missing data is better than fabricated certainty.**

**Every derived value must be reproducible.**

**Every material definition must be explicit.**

**Every provider must be replaceable.**

**Every material schema or pipeline change must be deliberate and version-controlled.**

**Prefer authoritative free sources when they are sufficient.**

**Pay only when paying creates meaningful value.**

**Build locally, remain portable.**

**Future-proof cheap foundations without solving imaginary problems.**

**The repository is the recipe. Snapshots preserve the ingredients. The database is the result.**

> **Build the history that the market actually experienced.**
