# StockBallDB — V1 Status

**Version:** V1  
**Status:** V1 COMPLETE — CERTIFIED BASELINE  
**Certification date:** 2026-09-11  
**Purpose:** Concise statement of what StockBallDB V1 contains, what has been completed, what V1 guarantees, known limitations, and what remains intentionally outside or unresolved.

---

## 1. V1 Objective

StockBallDB V1 was created to establish a trustworthy historical data foundation before building research, experiment, prediction, or trading systems.

The objective was not to collect every possible financial dataset.

The objective was to prove that StockBallDB can reliably:

**acquire → preserve → normalize → derive → validate → store → update → reproduce → inspect**

historical market and market-context data while maintaining explicit definitions, provenance, point-in-time discipline, and reproducibility.

That foundation is now implemented and **certified**.

---

## 2. What V1 Contains

StockBallDB contains seven canonical PostgreSQL tables:

* `trading_days`
* `daily_market_data`
* `market_outcomes`
* `asset_regimes`
* `macro_conditions`
* `scheduled_events`
* `calendar_context`

The certified market universe contains **15 symbols**:

* 14 U.S. equity ETFs: SPY, QQQ, IWM, XLB, XLC, XLE, XLF, XLI, XLK, XLP, XLU, XLV, XLY, XLRE
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

## 3. What V1 Guarantees

V1 includes and certifies:

* PostgreSQL canonical storage
* Alembic-controlled schema migrations (head `a8f3c2d1b4e5`)
* Python acquisition and normalization pipelines
* deterministic derivation
* point-in-time macro handling
* immutable content-addressed source snapshots
* Manifest 1.1 build provenance
* exact offline rebuild capability (`exact_rebuild_capable: true`)
* deterministic database fingerprints
* whole-database validation (`validate_v1`)
* health and coverage reporting
* operational database updates (`python -m stockballdb.update`)
* provider revision handling through full-refetch-by-design
* separated disposable test database for mutating integration tests (`STOCKBALLDB_TEST_DATABASE_URL`)
* read-only local StockBallDB Explorer
* automated pytest coverage
* documented sources, definitions, schema, workflow, validation, and operational procedures

The repository is the reproducible recipe; preserved snapshots retain mutable source inputs; PostgreSQL contains the canonical result.

---

## 4. Certified Baseline (2026-09-11)

| Check | Result |
| ----- | ------ |
| Full pytest suite | **220 passed, 2 skipped, 0 failed** |
| Explorer tests (within suite) | 70 collected/executed as part of suite |
| `validate_v1` | **PASS** (`V1 VALID`) |
| `health` | **HEALTHY** (WARNING/ERROR/FATAL = 0) |
| Snapshot verification (latest successful manifest) | **PASS** — checked 91, missing 0, corrupt 0, invalid metadata 0 |
| Snapshot verification (all referenced) | **PASS** — checked 455, missing 0, corrupt 0, invalid metadata 0 |
| Exact rebuild capability | **True** (`exact_rebuild_capable`) |
| Database fingerprint | `sha256:5055ae10f216ff33141eb137fc396ce29481e896c3ea828983e4ca8b12291aca` |
| Alembic head | `a8f3c2d1b4e5` (script head = DB revision) |
| Explorer functional certification | Phase 11C completed (prior); primary fingerprint unchanged through this certification |
| Primary mutation by pytest | **None** (fingerprint before = after) |

### Health INFO findings (not failures)

| Code | Finding |
| ---- | ------- |
| `ETF_EXPECTED_LAG` | ETF expected lag: **1** trading session |
| `WTI_EXPECTED_LAG` | WTI expected lag: **3** trading sessions |
| `WTI_PROVIDER_GAP` | WTI provider gaps: **39** sessions, max consecutive **2** |

These are classified by the health system as INFO and are **not** integrity failures.

### Canonical coverage

| Dataset | Coverage / Rows |
| ------- | --------------- |
| `trading_days` | 1957-01-02 → 2026-08-31 — **17,533** rows |
| `daily_market_data` | 1986-01-02 → 2026-08-28 — **99,633** rows |
| `market_outcomes` | 1986-01-02 → 2026-08-28 — **99,633** rows |
| `asset_regimes` | 1986-01-02 → 2026-08-28 — **99,633** rows |
| `macro_conditions` | 1957-01-02 → 2026-08-31 — **17,533** rows |
| `calendar_context` | 1957-01-02 → 2026-08-31 — **17,533** rows |
| `scheduled_events` | 1957-01-08 → 2026-08-12 — **2,641** rows |

### Latest successful update / run

| Field | Value |
| ----- | ----- |
| Run ID | `20260831T145447-9be32508` |
| Status | `SUCCESS_UPDATED` |
| `run_as_of` | `2026-08-31` |
| Manifest | `build_reports/manifest_20260831T145447-9be32508.json` |
| Fingerprint after | `sha256:5055ae10f216ff33141eb137fc396ce29481e896c3ea828983e4ca8b12291aca` |

---

## 5. V1 Boundaries (explicitly outside)

StockBallDB V1 ends at trusted historical data.

It does **not** perform:

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

## 6. Known Limitations / Deferred (not defects)

The following do **not** prevent V1 completion:

* XAU/USD — canonical definition established; acceptable source unresolved
* DXY — canonical definition established; acceptable source unresolved
* PMI — acceptable reproducible source unresolved
* future universe expansion
* hosted PostgreSQL / Supabase
* automated scheduled triggering of `update` (the update command itself is implemented)
* additional datasets and indicators
* research and experimentation systems
* Phase 11D Explorer desktop presentation: implemented; manual UX certification still pending (functional/read-only Explorer already certified in 11C)

StockBallDB is intended to grow after V1. V1 completion does not mean the database is permanently finished.

It means the foundation is sufficiently trustworthy, reproducible, maintainable, and extensible to serve as the baseline for future development.

---

## 7. Post-certification rule

Subsequent material database, schema, universe, or provenance changes are **post-V1 evolution**.

Future development begins from this certified baseline. Do not reopen V1 as unfinished implementation work without a deliberate version decision.

V2 (when started) should focus on:

**view → filter → explore → inspect**

—not experiments.

---

## 8. Completion Definition (satisfied)

> StockBallDB has a validated, reproducible, updatable, provenance-aware historical database; its canonical data can be rebuilt and independently inspected; its operational and test environments are safely separated; and future exploration can build on it without changing its responsibility into a research or trading system.

---

## Related documents

| Topic | Document |
| ----- | -------- |
| Validation & certification detail | [StockBallDB_validation.md](StockBallDB_validation.md) |
| Lifecycle / build vs update | [StockBallDB_workflow.md](StockBallDB_workflow.md) |
| Operational update & test-DB boundary | [StockBallDB_operational_update.md](StockBallDB_operational_update.md) |
| Snapshots & exact rebuild | [StockBallDB_snapshots_and_rebuilds.md](StockBallDB_snapshots_and_rebuilds.md) |
| Explorer | [StockBallDB_explorer.md](StockBallDB_explorer.md) |
| Universe / unresolved assets | [StockBallDB_universe.md](StockBallDB_universe.md) |
| Docs index | [StockBallDB_index.md](StockBallDB_index.md) |
