# StockBallDB — V2 Scope

**Status:** Locked (planning baseline)  
**Authority:** Authoritative V2 scope boundary  
**Companion docs:** [index](StockBallDB_index.md) · [V2 decisions](StockBallDB_V2_decisions.md) · [V2 progress](StockBallDB_V2_progress.md) · [future / deferred](StockBallDB_future.md) · [V1 status](StockBallDB_V1_status.md) · [manifesto](StockBallDB_manifesto.md)

---

## 1. Central definition

> StockBallDB V2 is a local-first desktop application built on the existing certified StockBallDB foundation. Its purpose is to let the user view, filter, explore, inspect, understand, validate, maintain, update and reproduce the historical database through a coherent graphical interface.

V2 is an **evolution of certified V1**, not a rewrite of StockBallDB.

---

## 2. Core interaction model

```text
view → filter → explore → inspect → understand → maintain
```

| Stage | Intent |
| ----- | ------ |
| View | See what StockBallDB already stores |
| Filter | Narrow canonical rows by stored values, symbols, fields, and dates |
| Explore | Browse tables and coverage across the universe |
| Inspect | Drill into a date, symbol, definition, provenance, or health fact |
| Understand | Make meanings, units, missingness, and limitations clear |
| Maintain | Run or access existing validation, update, snapshot, and rebuild workflows safely |

---

## 3. What V2 may do

V2 may perform factual querying, comparison, filtering, and inspection of canonical StockBallDB data, including observed, derived, and retrospective fields already stored by StockBallDB.

Valid V2 functionality includes:

* view stored StockBallDB data;
* select symbols;
* select fields;
* select date ranges;
* filter canonical stored values;
* sort and paginate data;
* compare multiple symbols;
* add/remove/reorder symbols;
* add/remove/reorder displayed fields;
* inspect a particular date and symbol;
* inspect definitions, units, missingness, and coverage;
* inspect provenance and source information;
* inspect database/table/symbol coverage;
* run or view existing validation and health functionality;
* run or view fingerprints;
* access existing update functionality;
* access existing snapshot / rebuild / restore functionality;
* provide understandable setup and portability workflows for running StockBallDB on another computer.

### Filtering is allowed

Filtering canonical stored values is an inspection operation, not research.

Examples:

* `trend_regime = downtrend`
* `return_1d < -0.03`
* `is_fomc_day = true`

---

## 4. Explicit V2 boundary

V2 does **not** perform:

* hypothesis testing;
* experiments;
* backtesting;
* predictive modelling;
* machine-learning training;
* signal generation;
* security ranking;
* "best setup" discovery;
* expected-return analysis;
* probability-of-rise calculations;
* correlation-discovery tools intended to discover predictive relationships;
* strategy construction;
* portfolio construction;
* optimization;
* position sizing;
* P&L simulation;
* buy/sell recommendations;
* trading decisions.

### Decision test

> Is this helping the user inspect, understand, validate, reproduce, or maintain what StockBallDB contains — or is it trying to discover whether something in StockBallDB is useful for predicting something else?

| Belongs in V2 | Belongs outside V2 (future research / experiment system) |
| ------------- | -------------------------------------------------------- |
| Inspect, understand, validate, reproduce, or maintain what is stored | Discover whether stored facts predict other outcomes |

**Allowed:** filter dates where `SPY return_1d < -0.03`.

**Not allowed:** “When SPY fell more than 3%, what was the average 20-day return afterward?”

The second evaluates a predictive / outcome relationship and is deferred. See [StockBallDB_future.md](StockBallDB_future.md).

---

## 5. `market_outcomes`

`market_outcomes` remains canonical StockBallDB data.

Its retrospective fields may be **viewed, filtered, and inspected** in V2.

V2 must **not** turn those fields into an experiment, backtesting, or predictive-analysis engine.

These fields are **retrospective future labels** — not contemporaneously available information on the row’s `date`. Field semantics remain owned by [StockBallDB_definitions.md](StockBallDB_definitions.md).

---

## 6. Evolution rule

**V2 evolves the certified V1 StockBallDB system. It does not replace or recode the database foundation from scratch.**

Preserve where practical:

* PostgreSQL storage;
* canonical schema;
* Python acquisition / normalization / derivation;
* SQLAlchemy;
* Alembic;
* validation;
* health checks;
* fingerprints;
* provenance;
* snapshots;
* exact rebuild;
* update orchestration;
* existing tests.

The main V2 change is expected to be the **application / UI layer** and the interfaces needed to expose existing StockBallDB capabilities cleanly.

Certified V1 facts remain owned by the existing canonical documents and [StockBallDB_V1_status.md](StockBallDB_V1_status.md). Do not silently reinterpret those documents when planning V2 features.

---

## 7. Architecture status

**Foundation / portability / universe-distribution architecture decisions are locked** in [StockBallDB_V2_decisions.md](StockBallDB_V2_decisions.md).

**Backend / application architecture is locked** in [StockBallDB_V2_architecture.md](StockBallDB_V2_architecture.md): thin in-process `stockballdb.app` façade; Layer A/B/C; read vs maintenance safety; Explorer query foundation; maintenance adapters; narrow universe service.

**Frontend / communication architecture is locked:** React is the V2 (and intended V3/StockBallAPP) forward-facing UI; V1 Streamlit Explorer is retained; React talks only through a **localhost-only HTTP JSON transport** wrapping the façade.

**Not yet locked:** desktop packaging (Electron vs Tauri), exact ASGI framework, endpoint/DTO schemas, React state/data-grid/styling libraries, universe file format, GitHub sync/auth, backup/restore format, progress/cancellation mechanism, Fresh Build UX details.
