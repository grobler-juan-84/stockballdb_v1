# StockBallDB — Workflow

Canonical lifecycle and dependency workflow for **StockBallDB V1 as implemented**.

This document describes **how data moves through the system** and how build / update / rebuild relate. It does not define philosophy, schema, providers, field formulas, or the asset universe — see companions below.

| Concern | Doc |
| --- | --- |
| Why / principles | `StockBallDB_manifesto.md` |
| Tables / keys | `StockBallDB_schema.md` |
| Providers | `StockBallDB_sources.md` |
| Field definitions | `StockBallDB_definitions.md` |
| Universe | `StockBallDB_universe.md` |
| Operator update commands | `StockBallDB_operational_update.md` |
| Snapshots / exact rebuild | `StockBallDB_snapshots_and_rebuilds.md` |
| Update contract (audit lock) | `StockBallDB_phase10a_operational_workflow_contract.md` |
| Read-only inspection UI | `StockBallDB_explorer.md` |

Phase novel (0→2G and later) is archived in **git history**; this doc stays current-state only.

---

## 1. Purpose

StockBallDB is boring infrastructure that produces a **trusted historical dataset**: acquired, preserved, normalized, derived, validated, and inspectable.

The workflow must stay **simple, explicit, deterministic, validated, reproducible, and auditable**.

---

## 2. Core pipeline stages

Every population path follows the same durable stages:

```text
Sources
   ↓
Acquire
   ↓
Preserve (immutable snapshots of mutable provider bytes)
   ↓
Normalize
   ↓
Derive
   ↓
Validate
   ↓
Write (PostgreSQL canonical tables)
```

Data must not silently bypass stages when that would weaken provenance, validation, or reproducibility.

Conceptual flow:

```text
Provider-specific data
        ↓
Normalization
        ↓
StockBallDB canonical representation
```

The canonical layer must remain independent of experiments, predictions, strategies, and trading decisions.

---

## 3. Stage responsibilities

### Acquire

Retrieve bytes / observations from locked providers (Tiingo, FRED/ALFRED, Fed HTML, etc.). Acquisition records enough to know source, time, range, status, and success. Failed acquisition is never treated as valid missing data.

### Preserve

Mutable external responses are captured as **immutable, content-addressed snapshots** before parse/normalize:

```text
network fetch → snapshot → read snapshot → parse → normalize
```

Deterministic local sources (NYSE calendar pin, election statute) are not snapshotted; provenance is code + pins. Operator detail: `StockBallDB_snapshots_and_rebuilds.md`.

### Normalize

Convert provider shapes into canonical definitions (dates, identifiers, types, units, duplicates) without silently changing meaning. Provider assumptions stay isolated from the schema.

### Derive

Compute fields that cannot be acquired directly (returns, drawdowns, outcomes, regimes, calendar context) from locked definitions in `StockBallDB_definitions.md`:

```text
Canonical Inputs + Locked Definition → Derived Value
```

Derivation must not depend on research experiments.

### Validate

Trust requires explicit checks — not merely a successful HTTP call or insert. Structural, coverage, value, and (where used) cross-source checks apply. Prefer **STOP / FLAG / INVESTIGATE** over silent acceptance of questionable history.

### Write

Validated rows are written idempotently (upsert or delete+insert per stage). Same inputs + definitions must not corrupt or duplicate the trusted record.

---

## 4. Canonical dependency graph

```text
trading_days ─────────────────────────────────────────────┐
     │                                                     │
     ├──► daily_market_data (observed: Tiingo + WTI)       │
     │         │                                           │
     │         ├──► daily_market_data (derived fields)      │
     │         │         ├──► market_outcomes               │
     │         │         └──► asset_regimes                 │
     │         │                                            │
     │         └──► (wti_context repeats derive→outcomes→regimes for WTI)
     │                                                     │
     ├──► macro_conditions (1:1 trading_days)              │
     │                                                     │
scheduled_events ─────────────────────────────────────────┤
     │                                                     │
     └──────────────────────────► calendar_context ◄───────┘
                                  (1:1 trading_days)
```

**Load-bearing order:** ETF derive → outcomes → regimes complete before `wti_context`; macro / events / calendar run after all market symbols. `market_outcomes` and `asset_regimes` require **derived** `daily_market_data`, not observed alone.

---

## 5. FULL-REFETCH-BY-DESIGN

Operational refresh is **not** append-only incremental ingestion for mutable HTTP sources.

| Class | Examples | Behavior |
| --- | --- | --- |
| **FULL-REFETCH-BY-DESIGN** | Tiingo ETFs, WTI, FRED current, ALFRED vintages, Fed FOMC HTML | Full history / full pages every run — providers revise past values |
| **DETERMINISTIC-REBUILD** | `trading_days`, elections | Regenerate from code / pins through `run_as_of` |
| **DERIVED-RECOMPUTE** | derive, outcomes, regimes, `calendar_context` | Full symbol or full spine recompute |

**Why not tail-only for derive / outcomes / regimes:**

* `drawdown_from_high` uses cummax from inception
* Forward horizons (1/3/5/10/20d) fill NULLs on **prior** dates when new sessions arrive
* `volatility_regime` / SMA windows need long lookbacks (up to ~252 / 200 sessions)

No mutable HTTP source is treated as incremental-safe without revision risk. Detail: Phase 10A contract §§4–6.

---

## 6. Bootstrap vs incremental ops

| Situation | Command | Migrate? |
| --- | --- | --- |
| Empty / new database | `python -m stockballdb.build_v1` | Yes (`alembic upgrade head` as first stage) |
| Established primary DB refresh | `python -m stockballdb.update` | **No** — preflight requires Alembic already at head |
| Disaster recovery (byte-faithful) | `python -m stockballdb.rebuild_exact` | Separate path; offline snapshot replay |

Operator flags, exit codes, preflight list: `StockBallDB_operational_update.md`.  
Snapshots / verify / rebuild: `StockBallDB_snapshots_and_rebuilds.md`.

### Empty-DB build sequence (`build_v1`)

```text
preflight
    ↓
migrate
    ↓
trading_days
    ↓
daily_market_data
    ↓
derive_market_data
    ↓
market_outcomes
    ↓
asset_regimes
    ↓
wti_context
    ↓
macro_conditions
    ↓
scheduled_events
    ↓
calendar_context
    ↓
validate_v1 (+ health / fingerprint / Manifest 1.1 on success)
```

Live stages run inside snapshot capture context (`live_build_context`). Fail-fast: later stages do not run after a stage error; earlier committed stages remain; status is never “ready” on partial failure.

### Update stage order (`update`)

Same data stages as build, **without** `migrate`:

```text
preflight → advisory lock → fingerprint_before
    → trading_days → daily_market_data → derive_market_data
    → market_outcomes → asset_regimes → wti_context
    → macro_conditions → scheduled_events → calendar_context
    → validate_v1 → health → fingerprint_after
    → Manifest 1.1 (success only)
```

Hard gates: `validate_v1` must PASS; health must not be **UNHEALTHY**. Fingerprint before/after classifies `SUCCESS_UPDATED` vs `SUCCESS_NO_CHANGE`. Every run writes an operational report; success also writes Manifest 1.1.

Single run boundary: `run_as_of` (default today America/New_York). Provider publication lag (e.g. WTI) may trail the spine without failing the run when health marks expected lag as INFO.

---

## 7. Failure philosophy

Prefer:

```text
STOP / FLAG / INVESTIGATE
```

over silent bad or incomplete history.

* Failures name stage, dataset/asset, condition, and required action.
* A partially successful pipeline is **not** reported as success.
* Stage-level commits may leave **partial state**; recovery is **idempotent rerun** (no `--resume`).
* Catastrophic recovery is **`rebuild_exact`** from a successful Manifest 1.1 — not the normal update path.

---

## 8. Reproducibility levels

| Level | Status | Meaning |
| --- | --- | --- |
| **Structural** | Supported | Locked schema, definitions, transforms, PIT rules, universe, stage order |
| **Current-source rebuild** | Supported | `build_v1` / `update` rebuild from **live** provider responses (may differ over time as sources revise) |
| **Exact historical rebuild** | **Supported** | Offline `rebuild_exact` from Manifest 1.1 + content-addressed snapshots; certified path in `StockBallDB_snapshots_and_rebuilds.md` |

Do not claim current-source rebuild is byte-identical months later without snapshots. Exact rebuild **is** the supported DR / audit path when snapshots and a capable manifest exist.

Reproduction must not depend on undocumented manual steps, one machine, Cursor, DBeaver, or a personal pre-populated database (credentials/config excepted).

---

## 9. Provenance and coverage

Important canonical values should remain traceable:

```text
Canonical value → transform / definition → source observation → provider → retrieval / snapshot
```

Coverage (what exists vs missing, freshness, gaps) is first-class operational knowledge — inspectable via health tooling and Explorer. Absence must be distinguishable from provider failure, pipeline failure, genuine non-existence, and intentionally unsupported range.

Historical provider revisions are absorbed by full refetch + upsert/replace; successful runs record fingerprints and manifests so changes are detectable.

---

## 10. Schema migration

Structural change is owned by **Alembic**. `build_v1` may apply migrations on empty/bootstrap DBs. **`update` never auto-migrates** — mismatch fails preflight; operators run `alembic upgrade head` explicitly.

Manual DDL in a GUI client is not authoritative schema history.

---

## 11. Explorer (implemented)

StockBallDB includes a **read-only** local Explorer UI — not a future “Inspector”:

```text
python -m stockballdb.explorer
```

Six areas: Control Center, Data Explorer, Day Inspector, Coverage Explorer, Provenance Explorer, Validation Center. Operator guide: `StockBallDB_explorer.md`.

Explorer inspects trusted history; it does not research edges, predict, or trade.

---

## 12. Research / trading boundary

StockBallDB **ends at trusted history**.

```text
External Sources → StockBallDB → Trusted Historical Dataset
================================ BOUNDARY ================================
Research / experiments / models / predictions / strategies / trading
```

Future systems may depend on StockBallDB. StockBallDB must not depend on them. Research discoveries do not retroactively rewrite history to improve an experiment.

---

## 13. Guiding rule

> **Is this required to acquire, preserve, normalize, derive, validate, explain, update, or inspect trustworthy historical data?**

If yes, it may belong in StockBallDB. Hypothesis testing, edge discovery, prediction, ranking, strategy, and trade decisions belong **outside**.

---

## 14. Current principle

Keep the pipeline:

**simple → explicit → deterministic → validated → reproducible → auditable.**

Orchestrate existing stage capabilities; do not reimplement providers, validators, or snapshot store in every new command.
