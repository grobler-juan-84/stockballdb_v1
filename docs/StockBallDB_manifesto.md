# StockBallDB — Manifesto

**Version 0.01**  
**Date:** 2026-08-23

> Companion docs: [index](StockBallDB_index.md) · [universe](StockBallDB_universe.md) · [schema](StockBallDB_schema.md)

## 1. What StockBallDB Is

StockBallDB is a **historical financial and market-context database**.

> **Collect, organize, derive, validate, and preserve useful historical data in one reliable and reproducible database.**

It is not a trading system, strategy, or prediction engine. It does not need to know which patterns will eventually prove useful. Its job is the foundation.

**StockBallDB** is the data foundation. **MoneyBallApp** is the future research and discovery environment that may use it. The database must not be designed around experiments that do not yet exist.

Priority: **data first** — a dependable historical foundation before pattern recognition, strategies, backtests, dashboards, or applications.

## 2. Observed vs Derived

**Observed data** — obtained from an external source (e.g. a closing price).  
**Derived data** — calculated deterministically from observed data (e.g. a 20-day return, month-end flags, forward returns).

Prefer the smallest reliable set of underlying facts and derive the rest ourselves. Always be able to answer: **Where did this value come from?**

## 3. Reproducibility

A clean installation should be able to reconstruct the database. Same project version, definitions, source data, and cutoff → equivalent databases.

**Pipeline:** Clone → Configure → Fetch → Normalize → Derive → Validate → Store → Ready

**Operations:** Build · Update · Validate · Rebuild

The repository is the recipe. The database is the result.

## 4. Architecture and Providers

**Local PostgreSQL** is the current environment; **PostgreSQL** is the architecture. Schema, migrations, pipelines, and config must stay portable (e.g. to hosted PostgreSQL / Supabase).

Providers supply facts; they do not define StockBallDB. Provider-specific formats stop at fetch/normalize. The schema remains ours and must survive provider replacement.

**Free → Reliable → Automated → Historically sufficient → Reproducible**, then pay only when a paid source adds clear value a free alternative cannot.

## 5. Historical Integrity

Prefer reliable, traceable information over convenient aggregation when it matters. Distinguish **what we know today about the past** from **what was known at the time**. Prefer point-in-time / vintage data when available. Never silently introduce future information into historical records.

Not every dataset starts on the same date. Do not invent unavailable history. A missing value may mean the information did not exist or cannot be reliably established.

## 6. Why `trading_days` Begins in 1957

The trading-day spine is intentionally longer than the initial asset histories. That does **not** mean all datasets must start in 1957.

1. **Future assets may predate SPY** (1993) — avoid rebuilding the calendar later.  
2. **Earlier history adds Saturday trading** — complexity StockBallDB does not need yet.  
3. **Modern S&P 500 began in 1957** — a sensible modern-era anchor.

> Make inexpensive foundational infrastructure comprehensive enough that reasonable future expansion does not require rebuilding the foundation.

## 7. Scope and Evolution

Collect what could reasonably describe historical market conditions — not everything an API offers. Current asset scope: [universe](StockBallDB_universe.md). Current tables: [schema](StockBallDB_schema.md).

The Version 1 schema will change as real data exposes weaknesses. Changes must be deliberate, documented, version-controlled, and reproducible.

**Priorities:** Correctness → Reproducibility → Coverage → Data quality → Maintainability → Performance → Interface

Future-proof cheap foundations (e.g. the 1957 calendar). Do not build for imaginary problems (real-time options, thousands of users, unused datasets).

## 8. Success

StockBallDB succeeds when it is trusted: reproducible, updatable, validated, provenance-clear, provider-replaceable. Discovery belongs to MoneyBallApp.

---

# The StockBallDB Rules

**Data before experiments.**  
**Facts before interpretations.**  
**Observed and derived data remain distinguishable.**  
**Prefer authoritative free sources when they are sufficient.**  
**Pay only when paying creates meaningful value.**  
**Never sacrifice historical integrity for convenience.**  
**Never invent unavailable history.**  
**Every derived value must be reproducible.**  
**Every provider must be replaceable.**  
**Every schema change must be deliberate.**  
**Build locally, remain portable.**  
**Future-proof cheap foundations without solving imaginary problems.**  
**The repository is the recipe. The database is the result.**

> **Build a database we can trust.**
