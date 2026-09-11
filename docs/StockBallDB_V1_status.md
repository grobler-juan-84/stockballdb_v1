# StockBallDB — V1 Status

**Version:** V1  
**Status:** RELEASE CANDIDATE — pending final baseline declaration  
**Purpose:** Concise statement of what StockBallDB V1 contains, what has been completed, and what remains intentionally outside or unresolved.

---

## 1. V1 Objective

StockBallDB V1 was created to establish a trustworthy historical data foundation before building research, experiment, prediction, or trading systems.

The objective was not to collect every possible financial dataset.

The objective was to prove that StockBallDB can reliably:

**acquire → preserve → normalize → derive → validate → store → update → reproduce → inspect**

historical market and market-context data while maintaining explicit definitions, provenance, point-in-time discipline, and reproducibility.

That foundation is now implemented.

---

## 2. Current V1 Database

StockBallDB contains seven canonical PostgreSQL tables:

* `trading_days`
* `daily_market_data`
* `market_outcomes`
* `asset_regimes`
* `macro_conditions`
* `scheduled_events`
* `calendar_context`

The implemented market universe contains:

* 14 U.S. equity ETFs
* WTI spot crude oil

The database also contains:

* NYSE trading-calendar history from 1957
* point-in-time / historically aligned macroeconomic conditions
* FOMC events
* CPI releases
* Employment Situation releases
* U.S. presidential and midterm elections
* deterministic market-derived fields
* forward market outcomes
* historical asset regimes
* calendar and event context

XAU/USD, DXY, and PMI remain intentionally unresolved because acceptable reproducible sources have not been approved.

Their absence is not a V1 defect.

---

## 3. V1 Infrastructure Completed

V1 includes:

* PostgreSQL canonical storage
* Alembic-controlled schema migrations
* Python acquisition and normalization pipelines
* deterministic derivation
* point-in-time macro handling
* immutable content-addressed source snapshots
* Manifest 1.1 build provenance
* exact offline rebuild capability
* deterministic database fingerprints
* whole-database validation
* health and coverage reporting
* operational database updates
* provider revision handling through full-refetch-by-design
* separated disposable test database for mutating integration tests
* read-only local StockBallDB Explorer
* automated pytest coverage
* documented sources, definitions, schema, workflow, validation, and operational procedures

The repository is the reproducible recipe; preserved snapshots retain mutable source inputs; PostgreSQL contains the canonical result.

---

## 4. Current Certified Baseline

Current certification records:

| Check                             | Result                                                                    |
| --------------------------------- | ------------------------------------------------------------------------- |
| `validate_v1`                     | PASS                                                                      |
| `health`                          | HEALTHY                                                                   |
| Full pytest suite                 | 220 passed, 2 skipped                                                     |
| Explorer tests                    | 70 passed                                                                 |
| Explorer functional certification | Phase 11C completed                                                       |
| Database fingerprint              | `sha256:5055ae10f216ff33141eb137fc396ce29481e896c3ea828983e4ca8b12291aca` |
| Snapshot verification             | 91 checked, 0 missing, 0 corrupt                                          |
| Alembic head                      | `a8f3c2d1b4e5`                                                            |
| Exact rebuild capability          | Supported                                                                 |
| Explorer database mutation        | None                                                                      |

Current canonical coverage:

| Dataset             | Coverage / Rows                       |
| ------------------- | ------------------------------------- |
| `trading_days`      | 1957-01-02 → 2026-08-31 — 17,533 rows |
| `daily_market_data` | 99,633 rows                           |
| `market_outcomes`   | 99,633 rows                           |
| `asset_regimes`     | 99,633 rows                           |
| `macro_conditions`  | 17,533 rows                           |
| `calendar_context`  | 17,533 rows                           |
| `scheduled_events`  | 2,641 rows                            |

Known health information includes expected ETF/provider publication lag and documented WTI provider gaps. These are classified by the health system and are not currently integrity failures.

---

## 5. V1 Boundaries

StockBallDB V1 ends at trusted historical data.

It does not perform:

* hypothesis discovery
* experiments
* backtesting
* prediction
* security ranking
* signal generation
* portfolio construction
* strategy evaluation
* trading decisions

Those capabilities belong to future systems that may consume StockBallDB.

StockBallDB itself must remain experiment-agnostic.

---

## 6. Intentionally Unresolved / Deferred

The following do not prevent V1 completion:

* XAU/USD — canonical definition established; acceptable source unresolved
* DXY — canonical definition established; acceptable source unresolved
* PMI — acceptable reproducible source unresolved
* future universe expansion
* hosted PostgreSQL / Supabase
* automated scheduled updates
* additional datasets and indicators
* research and experimentation systems

StockBallDB is intended to grow after V1. V1 completion does not mean the database is permanently finished.

It means the foundation is sufficiently trustworthy, reproducible, maintainable, and extensible to serve as the baseline for future development.

---

## 7. Remaining V1 Closeout

Before declaring the V1 baseline final:

1. Normalize stale version/status headers in surviving canonical documentation.
2. Confirm the test-database separation and repair decisions are documented.
3. Run the final V1 certification procedure against the canonical database.
4. Record the resulting fingerprint, validation, health, tests, snapshot status, and coverage as the final V1 baseline.
5. Tag / commit the final V1 baseline in Git.

After these gates pass, change this document to:

**Status: V1 COMPLETE — CERTIFIED BASELINE**

and treat subsequent material database changes as post-V1 evolution.

---

## 8. Completion Definition

V1 is complete when we can credibly say:

> StockBallDB has a validated, reproducible, updatable, provenance-aware historical database; its canonical data can be rebuilt and independently inspected; its operational and test environments are safely separated; and future exploration can build on it without changing its responsibility into a research or trading system.

At that point, V2 can begin from a stable foundation.

V2 should focus on:

**view → filter → explore → inspect**

—not experiments.

---

## Related documents

| Topic | Document |
| ----- | -------- |
| Validation & current certification detail | [StockBallDB_validation.md](StockBallDB_validation.md) |
| Lifecycle / build vs update | [StockBallDB_workflow.md](StockBallDB_workflow.md) |
| Operational update & test-DB boundary | [StockBallDB_operational_update.md](StockBallDB_operational_update.md) |
| Snapshots & exact rebuild | [StockBallDB_snapshots_and_rebuilds.md](StockBallDB_snapshots_and_rebuilds.md) |
| Explorer | [StockBallDB_explorer.md](StockBallDB_explorer.md) |
| Universe / unresolved assets | [StockBallDB_universe.md](StockBallDB_universe.md) |
| Docs index | [StockBallDB_index.md](StockBallDB_index.md) |
