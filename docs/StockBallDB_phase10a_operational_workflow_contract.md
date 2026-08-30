# StockBallDB — Phase 10A: Operational Workflow Audit & Contract

**Version:** 1.0 (Phase 10A lock)  
**Date:** 2026-08-29  
**Status:** Authoritative contract for Phase 10B implementation  
**Prerequisite:** Phase 9 COMPLETE (immutable snapshots, Manifest 1.1, offline REBUILD EXACT certified)

---

## 1. Purpose and scope

### 1.1 Purpose

Phase 10 turns StockBallDB from a collection of individually working build commands into **one boring, reliable, safe operational workflow** for maintaining the primary database:

```text
python -m stockballdb.update
```

(or repository-equivalent module name — **locked for 10B**).

Phase 10 **orchestrates existing capabilities**. It does **not** reimplement providers, normalization, sync logic, validators, snapshot store, fingerprinting, or exact rebuild.

### 1.2 Phase structure

| Sub-phase | Scope | Status after 10A |
| --- | --- | --- |
| **10A** | Audit + operational contract (this document) | **COMPLETE** |
| **10B** | Unified `update` implementation | **IMPLEMENTED** (2026-08-29) |
| **10C** | Operational certification | **NOT STARTED** |

### 1.3 Non-goals (Phase 10 overall)

Locked **OUT** (see §21): Airflow, Celery, Kafka, Redis, Docker/Kubernetes orchestration, cron/Task Scheduler configuration, cloud deployment, remote monitoring, alerts, daemons, web services, snapshot GC/retention automation, object storage, new datasets (XAU, DXY, PMI, GDP), research/UI/experiments.

Phase 10 is **not** a DevOps expansion.

### 1.4 Core principle

```text
ORCHESTRATE EXISTING CAPABILITIES
≠ REIMPLEMENT EXISTING CAPABILITIES
```

Phase 10B must reuse:

- Provider modules (`providers/tiingo.py`, `fred.py`, `fed.py`)
- Snapshot infrastructure (`snapshots/context.py`, `store.py`)
- Normalization and `sync_*` pipelines
- `validate_v1`, `run_health`, `compute_database_fingerprint`
- Manifest 1.1 provenance (`health/provenance.py`)
- `rebuild_exact` (disaster recovery — not part of normal update)

---

## 2. Current operational inventory

### 2.1 Package CLI entry points

All operational commands today are `python -m stockballdb.<module>` (no `[project.scripts]` in `pyproject.toml`).

| Command | Module | Network | Snapshots | Canonical DB writes | Recompute scope | Idempotency | Validation | Operational role (10B) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `build_v1` | `build_v1.py` | Yes (preflight + live stages) | Yes (live context) | All 7 tables + alembic | Full pipeline | Stage upsert/delete patterns; safe rerun | Per-stage + validate_v1 + pytest | **Wrap / evolve into `update`** |
| `build_trading_days` | `build_trading_days.py` | No | No | `trading_days` | Full spine `[1957, today_ny]` | Upsert + delete OOR rows | Frame + DB validators | **Reuse** (`stage_trading_days`) |
| `build_daily_market_data` | `build_daily_market_data.py` | Yes (Tiingo) | If live context | `daily_market_data` observed | Full history per symbol | Upsert only; no stale delete | Frame + DB | **Reuse** |
| `derive_daily_market_data` | `derive_daily_market_data.py` | No | No | `daily_market_data` derived | Full symbol scope | Upsert derived cols; CLI double-run check | Derived frame + DB | **Reuse** |
| `build_market_outcomes` | `build_market_outcomes.py` | No | No | `market_outcomes` | Full symbol scope | Upsert; double-run check | Frame + DB | **Reuse** |
| `build_asset_regimes` | `build_asset_regimes.py` | No | No | `asset_regimes` | Full symbol scope | Upsert; double-run check | Frame + DB + PIT checks | **Reuse** |
| `build_wti` | `build_wti.py` | Yes (FRED) | If live context | WTI rows in dmd/mo/ar | Full WTI symbol | Upsert chain | Per-symbol validators | **Retire as standalone ops path** — folded into `build_v1` `wti_context` stage; update uses stage |
| `build_macro_conditions` | `build_macro_conditions.py` | Yes (FRED+ALFRED) | If live context | `macro_conditions` | Full table replace | Delete+insert; double-run | Macro validators + PIT | **Reuse** |
| `build_scheduled_events` | `build_scheduled_events.py` | Yes (Fed+FRED) | If live context | `scheduled_events` | Full table replace | Delete+insert; double-run | Event validators | **Reuse** |
| `build_calendar_context` | `build_calendar_context.py` | No | No | `calendar_context` | Full spine replace | Delete+insert; double-run | Calendar validators | **Reuse** |
| `validate_v1` | `validate_v1.py` | No | No | None | N/A | N/A | Whole-DB invariants | **Reuse** (mandatory gate) |
| `health` | `health/__main__.py` | No | No | None | N/A | N/A | Coverage/freshness/gaps + validate_v1 | **Reuse** (mandatory gate) |
| `fingerprint` | `fingerprint/__main__.py` | No | No | None | N/A | N/A | N/A | **Reuse** |
| `snapshots` (verify) | `snapshots/__main__.py` | No | Reads disk | None | N/A | N/A | Payload/sidecar integrity | **Reuse** (post-success optional / cert) |
| `rebuild_exact` | `rebuild_exact.py` | **Forbidden** | Replay only | Rebuild target DB | Full truncate + stages | Exact rebuild | validate_v1 + health + fingerprint | **Keep separate** (DR, not update) |
| `check_db` | `check_db.py` | No (DB only) | No | None | N/A | N/A | SELECT 1 | **Reuse** (preflight) |

### 2.2 Audit scripts (`scripts/`)

Development/audit only — **not** part of operational update: `phase4b_macro_audit.py`, `phase5b_wti_audit.py`, `phase6b_scheduled_events_audit.py`, `phase7b_calendar_context_audit.py`, `phase8a_health_audit.py`.

### 2.3 `build_v1` detailed audit

**Entry:** `python -m stockballdb.build_v1` → `run_build_v1()`.

**Current stage order** (`v1/stages.py` → `BUILD_STAGES`):

| # | Stage key | Label | Network | Snapshots | DB pattern | Tables touched |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | `migrate` | migrate | No | No | Alembic DDL | schema |
| 1 | `trading_days` | 1/9 trading_days | No | No | Delete OOR + upsert | `trading_days` |
| 2 | `daily_market_data` | 2/9 daily_market_data | Yes (Tiingo ×14) | Yes | Upsert observed | `daily_market_data` |
| 3 | `derive_market_data` | 3/9 derive_market_data | No | No | Upsert derived | `daily_market_data` |
| 4 | `market_outcomes` | 4/9 market_outcomes | No | No | Upsert | `market_outcomes` |
| 5 | `asset_regimes` | 5/9 asset_regimes | No | No | Upsert | `asset_regimes` |
| 5b | `wti_context` | 5b/9 wti_context | Yes (FRED) | Yes | Upsert chain | dmd + mo + ar (WTI) |
| 6 | `macro_conditions` | 6/9 macro_conditions | Yes (FRED+ALFRED) | Yes | Delete all + insert | `macro_conditions` |
| 7 | `scheduled_events` | 7/9 scheduled_events | Yes (Fed+FRED) | Yes | Delete all + insert | `scheduled_events` |
| 8 | `calendar_context` | 8/9 calendar_context | No | No | Delete all + insert | `calendar_context` |

**Post-stages (in `build_v1.py`, outside `BUILD_STAGES`):**

1. `validate_v1_database()` — mandatory for success
2. `pytest -q` (optional disable in tests via `run_pytest=False`)
3. `run_health()` — printed; **does not fail build_v1 exit code today**
4. Manifest 1.1 + `database_fingerprint` — **only on full success**

**Snapshot capture:** Wrapped in `live_build_context()` for all `BUILD_STAGES`. Snapshot refs captured at end of context; written to manifest on success.

**Failure propagation:** Fail-fast. First `StageError` → `STATUS: PARTIAL`, `write_build_report(PARTIAL)`, exit `1`. **No manifest on failure.** Earlier stages remain committed.

**Phase 10 verdict on `build_v1`:** Not a simple rename. The **stage sequence and reuse pattern** are correct for a full refresh update, but operational `update` must add: explicit `run_as_of`, preflight/concurrency/change-detection, health gate on exit, failed-run reporting, primary-DB identity guard, and optional `--as-of`. **`build_v1` remains available for development and full certification builds.**

---

## 3. Canonical dependency graph

### 3.1 Table-level dependencies (derived from code)

```text
trading_days ─────────────────────────────────────────────┐
     │                                                     │
     ├──► daily_market_data (observed: Tiingo + WTI)       │
     │         │                                           │
     │         ├──► daily_market_data (derived fields)      │
     │         │         ├──► market_outcomes               │
     │         │         └──► asset_regimes                 │
     │         │                                            │
     │         └──► (WTI stage repeats derive→outcomes→regimes for WTI)
     │                                                     │
     ├──► macro_conditions (1:1 trading_days)              │
     │                                                     │
scheduled_events ─────────────────────────────────────────┤
     │                                                     │
     └──────────────────────────► calendar_context ◄───────┘
                                  (1:1 trading_days)
```

**Notes:**

- `market_outcomes` and `asset_regimes` depend on **derived** `daily_market_data`, not raw observed alone.
- `macro_conditions` and `calendar_context` are **independent branches** after spine (macro needs spine only; calendar needs spine + events).
- `wti_context` inserts between ETF regimes and macro — **order is load-bearing** (ETF derive/outcomes/regimes complete before WTI; macro/events/calendar after all market symbols).

### 3.2 Required operational execution order

Locked for Phase 10B (matches proven `BUILD_STAGES` with explicit pre/post hooks):

```text
PRECHECK
→ establish run_as_of / run boundary
→ migrate guard (Alembic head check; no silent upgrade in update — see §8)
→ trading_days (through run_as_of)
→ daily_market_data (ETFs)
→ derive_market_data (ETFs)
→ market_outcomes (ETFs)
→ asset_regimes (ETFs)
→ wti_context
→ macro_conditions
→ scheduled_events
→ calendar_context
→ validate_v1          [HARD GATE]
→ health               [HARD GATE for update exit]
→ fingerprint_after (+ compare to fingerprint_before)
→ snapshot verify (optional quick check on captured snapshots)
→ Manifest 1.1 (success only) + operational run report (always)
→ SUCCESS / SUCCESS_NO_CHANGE / FAILED
```

**Parallelism:** None in 10B. Single-threaded sequential stages.

---

## 4. Source classification

| Source / component | Primary class | Why | Phase 10B decision |
| --- | --- | --- | --- |
| Tiingo ETFs (14) | **FULL-REFETCH-BY-DESIGN** | Full history per symbol; `adj_*` restated by corp actions | Keep full refetch every update |
| WTI (DCOILWTICO) | **FULL-REFETCH-BY-DESIGN** | FRED revises history | Keep full refetch |
| FRED current (DFF, DGS2/10, WALCL, BAA10Y) | **FULL-REFETCH-BY-DESIGN** | FRED revises observations | Keep full refetch |
| ALFRED PIT (CPI, core CPI, UNRATE, ICSA) | **FULL-REFETCH-BY-DESIGN** | Complete vintage set required for PIT | Keep full refetch |
| Fed FOMC HTML | **FULL-REFETCH-BY-DESIGN** | Pages editable; ~65 snapshots dedupe | Keep full page fetch |
| Elections | **DETERMINISTIC-REBUILD** | Statute algorithm; no network | Full regen in range (cheap) |
| NYSE `trading_days` | **DETERMINISTIC-REBUILD** | `pandas_market_calendars` pin | Full spine recompute to `run_as_of` |
| `derive_daily_market_data` | **DERIVED-RECOMPUTE** | From observed | Full symbol recompute (see §13) |
| `market_outcomes` | **DERIVED-RECOMPUTE** | Forward horizons | Full symbol recompute |
| `asset_regimes` | **DERIVED-RECOMPUTE** | Expanding vol regime | Full symbol recompute |
| `calendar_context` | **DERIVED-RECOMPUTE** | Spine replace | Full table replace |

**INCREMENTAL-SAFE (future-only):** Elections only (immutable past). **No mutable HTTP source is INCREMENTAL-SAFE** without revision risk.

---

## 5. Incrementality decisions

### 5.1 Principle

Phase 10 is **not** an incremental-ingestion project by default. For each source:

| Question | Tiingo | FRED/ALFRED | FOMC | WTI |
| --- | --- | --- | --- | --- |
| SAFE? | **No** (adj revisions) | **No** | **No** (HTML edits) | **No** |
| USEFUL? | Marginal | Marginal | Low (snapshots dedupe) | Marginal |
| NECESSARY? | **No** at current scale | **No** | **No** | **No** |

**Locked:** All mutable external sources remain **FULL-REFETCH-BY-DESIGN** in Phase 10B.

### 5.2 Tiingo incrementality audit

- Default fetch: `start_date=1957-01-01`, `end_date=today` (or `run_as_of`) — full history per symbol.
- Tiingo returns `divCash`, `splitFactor`, `adjOpen/High/Low/Close/Volume` — **historical adjusted values can change** when corporate actions are applied retroactively.
- Upsert does **not** delete removed rows — but full refetch + upsert overwrites revised values.
- **Incremental-only fetch would miss revisions** on prior dates.
- **10B contract:** Full refetch per symbol each update. Optional future: rolling overlap window — **DEFER** until cost proves prohibitive.

### 5.3 FRED / ALFRED incrementality audit

- FRED current: paginated full history (`full_concat_v1`); revisions change past values.
- ALFRED: `realtime_start=1776-07-04`, `realtime_end=9999-12-31` — entire vintage dump required for PIT macro and event first-print dates.
- **Do not weaken Phase 4 PIT semantics** for operational efficiency.
- **10B contract:** Full refetch unchanged.

### 5.4 FOMC audit

- Historical: one HTML page per year (1957–2020) + single calendar page (2021+).
- Pages can change; full refetch is inexpensive relative to Tiingo; Phase 9 snapshots **deduplicate unchanged payloads**.
- **10B contract:** Continue full-page acquisition.

### 5.5 Deterministic sources

| Source | Regeneration | Provenance (no payload snapshot) |
| --- | --- | --- |
| NYSE calendar | `build_trading_days_frame(start=1957-01-01, end=run_as_of)` | Git commit, `calendar_pin`, code |
| Elections | Statute loop in `[COVERAGE_START, run_as_of]` | Git + 2 U.S.C. §7 + code |

---

## 6. Derived recompute audit

| Derived layer | Tail-only safe? | Reason | 10B decision |
| --- | --- | --- | --- |
| `derive_daily_market_data` | **No** (drawdown) | `drawdown_from_high` uses cummax from inception | Full symbol recompute |
| `market_outcomes` | **No** | Forward horizons 1/3/5/10/20d: new tail fills NULLs on **prior** dates | Full symbol recompute |
| `asset_regimes` | **No** | `volatility_regime` uses expanding empirical CDF; SMA200 needs 199 prior rows | Full symbol recompute |
| `calendar_context` | N/A (full replace) | Cheap DELETE+INSERT entire spine | Full spine replace |
| `macro_conditions` | N/A (full replace) | DELETE+INSERT all trading days | Full replace |

### 6.1 Forward-outcome tail semantics (locked)

Adding new market days makes forward outcomes on **earlier** dates computable (up to 20 sessions forward). Operational update **must** recompute full per-symbol series, not append-only today's row.

### 6.2 Rolling-regime semantics (locked)

`asset_regimes` requires up to **252** prior `volatility_20d` observations for regime label; SMA windows up to **200** sessions. Full-series recompute is required for correctness.

---

## 7. Run boundary contract

### 7.1 Single run boundary (locked)

> One operational run gets one deterministic temporal boundary.

```text
run_as_of : date   # calendar date, America/New_York semantics for "today"
run_id    : str    # reuse build_id format from manifest (§12)
```

All stages derive horizons from `run_as_of`:

| Stage | Current wall-clock coupling | 10B requirement |
| --- | --- | --- |
| `trading_days` | `end = today_ny()` if unset | `end = run_as_of` |
| `scheduled_events` | `min(max(trading_days), today ET)` | `end = run_as_of` (after trading_days) |
| Tiingo / FRED | Provider returns through latest available | Filter/normalize to `trading_days` spine ≤ `run_as_of` |
| Derived layers | Load all rows from DB | Recompute full symbol/spine (unchanged logic) |

**Default:** `run_as_of = today_ny()` when `--as-of` omitted.

**Time-of-day:** A **date** is sufficient. Session boundaries are already encoded in `trading_days` and provider publication lag handling (Phase 8). No sub-day `run_as_of` in 10B.

### 7.2 Provider publication lag (locked)

Distinguish:

- **Update boundary** (`run_as_of`) — how far the database spine extends
- **Provider latest observation** — may legitimately lag (WTI INFO, ETF CURRENT)

A successful update **must not fail** solely because WTI has not published through the latest ETF session. Phase 8 freshness semantics remain authoritative:

- `EXPECTED_LAG` / `NOT_YET_PUBLISHED` → INFO, success allowed
- Provider HTTP failure → run failure
- `ERROR`/`FATAL` health findings → run failure (see §10)

---

## 8. Preflight contract (10B design)

Cheap checks **before** expensive provider acquisition:

| Check | Fail update? | Notes |
| --- | --- | --- |
| `DATABASE_URL` configured | Yes | |
| Database reachable (`check_connection`) | Yes | |
| Primary DB identity guard (≠ rebuild cert DB) | Yes | See §14 |
| Alembic revision == `V1_ALEMBIC_HEAD` | Yes | **Do not auto-migrate** during update |
| Required credentials present (Tiingo, FRED) | Yes | Structural only; no full fetch |
| Snapshot root writable | Yes | |
| `build_reports/` writable | Yes | |
| Git metadata readable | No (warn) | For provenance |
| Concurrent update lock available | Yes | See §9 |
| Provider network probes | **Optional** | `build_v1` preflight probes 3 endpoints; update may **skip** duplicate probes and fail on first acquisition (simpler) |

**Recommendation:** Lightweight preflight without redundant provider probes; first live `acquire_bytes` failure fails the run.

---

## 9. Git cleanliness

| Mode | Clean tree required? | Rationale |
| --- | --- | --- |
| **REBUILD EXACT** | **Yes** (mandatory) | Exact rebuild reproduces manifest commit |
| **UPDATE LATEST** | **No** | Dirty allowed; manifest records `git.dirty=true` |

Phase 9 behavior: `rebuild_exact` refuses dirty working tree. Successful BUILD LATEST records actual git state including dirty flag.

**10B lock:** Operational update does **not** require clean tree.

---

## 10. Alembic contract

**Current behavior:** `build_v1` stage 0 runs `alembic upgrade head` — migrations can run silently during build.

**10B lock (strong preference):**

- Preflight: `alembic_version == V1_ALEMBIC_HEAD`
- Mismatch → **FAIL before any canonical write**
- Operator runs migrations explicitly (`alembic upgrade head`) outside update

**Gap for 10B:** Remove or gate `stage_migrate` inside update; document in operator guide.

---

## 11. Concurrency

**Requirement:** Second simultaneous update must exit safely.

**10B mechanism (locked):** PostgreSQL **advisory lock** keyed to StockBallDB namespace (single integer agreed in 10B implementation).

```text
second update → lock not acquired → exit non-zero (CONCURRENT_UPDATE)
```

No Redis, filesystem locks, or distributed services.

---

## 12. Failure model

### 12.1 Per-stage failure semantics

| Failure point | DB state after failure | Success claimable? |
| --- | --- | --- |
| Preflight | Unchanged | No |
| During provider fetch (before snapshot) | Unchanged | No |
| After snapshot, before DB write | Snapshots on disk; DB unchanged | No |
| During DB write (upsert/delete+insert) | **Prior txn rolled back** for that sync call | No |
| After DB write, before stage validation | **Partial stage committed** | No |
| Mid-pipeline (earlier stages committed) | **Partially updated** | No |
| After all writes, validate_v1 fails | Partially updated | No |
| After validate_v1, health ERROR/FATAL | Data written; invalid for ops success | No |
| Fingerprint/manifest | N/A | No unless all gates pass |

### 12.2 Transaction audit

| Operation | Atomicity |
| --- | --- |
| Upsert batches (`daily_market_data`, outcomes, regimes) | One `engine.begin()` per sync |
| `calendar_context`, `macro_conditions`, `scheduled_events` | DELETE+INSERT in one transaction |
| `trading_days` | **Two transactions** (DELETE OOR, then upsert) — partial failure can leave damaged spine |
| Full update workflow | **Not** one giant transaction |

**10B model:** Stage-level atomicity + idempotent rerun + validation gate + recovery by rerun (§13).

### 12.3 Recovery contract (locked)

```text
failed run → marked FAILED → operator fixes cause → rerun update → idempotent stages converge
```

**No `--resume` in 10B** (default **NO**). Snapshots dedupe; canonical syncs idempotent; full rerun safer than partial resume.

**Failed-run DB state:** **Option B** — leave committed stage state, mark FAILED, rerun converges. No shadow DB, no automatic rollback.

**Disaster recovery:** `REBUILD EXACT` from last successful Manifest 1.1 — separate from operational recovery.

**Last known good:** Latest successful Manifest 1.1 in `build_reports/`.

---

## 13. Validation and health gates

### 13.1 validate_v1 (locked)

```text
validate_v1 PASS → required for SUCCESS
validate_v1 FAIL → RUN = FAILED (even if data exists)
```

### 13.2 health (locked — Phase 8 semantics unchanged)

| Health status | Update exit |
| --- | --- |
| `HEALTHY` | Success (0) |
| `HEALTHY WITH WARNINGS` | Success (0); optional `--strict` → 1 for automation |
| `UNHEALTHY` (ERROR/FATAL findings) | **Failure (1)** |

**INFO findings** (e.g. WTI_EXPECTED_LAG) do **not** fail update.

**10B gap:** `build_v1` today prints health but always exits 0 on V1 READY. **`update` must fail exit code on UNHEALTHY.**

---

## 14. Primary database safety

**Risk:** `DATABASE_URL` accidentally points at `STOCKBALLDB_REBUILD_DATABASE_URL` or test DB.

**10B guard (MUST):** Preflight compares normalized database name (or host+dbname tuple) against:

- Explicit rebuild URL from env (if set) — **must differ**
- Optional: `STOCKBALLDB_PRIMARY_DATABASE_NAME` allowlist env — **SHOULD** if operators use multiple local DBs

No hardcoded environment-specific names in code.

---

## 15. Snapshots and provenance

### 15.1 Snapshot contract (non-negotiable)

All mutable external acquisition in update:

```text
fetch → immutable snapshot → read snapshot → parse → normalize
```

No live bypass in operational update. Reuse `live_build_context()` + `acquire_bytes()`.

### 15.2 Snapshot reuse on rerun

**10B default:** Always reacquire from providers on each update attempt (simplest). Same-run snapshot reuse after mid-pipeline failure — **DEFER** unless rate limits demand it.

### 15.3 Manifest vs operational run report

| Artifact | When | Purpose |
| --- | --- | --- |
| **Manifest 1.1** | Successful update only | Exact-rebuild-capable provenance; fingerprints; snapshots |
| **Operational run report** | Every run (success or failure) | Stage log, timing, outcome, git/alembic, errors |

**Do not** write `exact_rebuild_capable: true` on failed runs.

Failed report minimum fields:

```text
run_id, started_at, finished_at, run_as_of, status (FAILED),
stages[], failure_stage, error, snapshots_captured_count,
git, alembic_head, fingerprint_before, fingerprint_after (if computed)
```

### 15.4 run_id

Reuse existing **`build_id`** format: `%Y%m%dT%H%M%S-<8hex>` from `health/provenance.py`. No parallel ID system.

---

## 16. Change detection

### 16.1 Mechanism (locked)

```text
fingerprint_before  (after preflight, before acquisition)
fingerprint_after   (after all gates pass)
```

| Comparison | Run outcome label |
| --- | --- |
| `fingerprint_before == fingerprint_after` | `SUCCESS_NO_CHANGE` |
| `fingerprint_before != fingerprint_after` | `SUCCESS_UPDATED` |

Covers historical revisions without row diff machinery.

### 16.2 Revision-only runs

Legitimate update: no new dates but provider revision changes canonical data → fingerprint changes → `SUCCESS_UPDATED`.

Reporting SHOULD note `canonical_change: true/false` and MAY include per-table fingerprint deltas from manifest fields.

---

## 17. Logging, exit codes, CLI surface

### 17.1 Logging (10B)

```text
console (structured stages)
+ build_reports/run_<run_id>.log
+ build_reports/run_<run_id>.json   # machine-readable operational report
+ build_reports/manifest_<run_id>.json  # success only
```

Reuse `v1/report.py` patterns. **No credentials** in logs (reuse `scan_secrets()` patterns from Phase 8/9).

### 17.2 Exit codes (10B minimum)

| Code | Meaning |
| --- | --- |
| `0` | SUCCESS_UPDATED or SUCCESS_NO_CHANGE |
| `1` | Generic failure |
| `2` | Preflight failure (optional) |
| `3` | Concurrent update rejected (optional) |

Keep simple; distinguish preflight/concurrency only if automation benefit confirmed in 10B.

### 17.3 Command surface (locked)

```text
python -m stockballdb.update              # default run_as_of=today_ny
python -m stockballdb.update --as-of YYYY-MM-DD
python -m stockballdb.update --json         # machine-readable summary on stdout
```

**No** `--dry-run` in 10B (cannot know changes without acquisition).  
**No** `--status` — use `python -m stockballdb.health`.  
**No** per-stage CLI switches in 10B.  
Specialized build CLIs remain for development.

### 17.4 `--as-of` semantics

Sets `run_as_of` for spine and event collection bounds. **Does not** imply point-in-time provider APIs — live providers return full history; normalization filters to spine. Useful for testing and controlled cutoffs.

---

## 18. Performance baseline (informational)

From Phase 9 certification (local, approximate):

| Operation | Duration |
| --- | --- |
| Full `build_v1` | ~12–13 min |
| `rebuild_exact` (offline) | ~7.5 min |
| `validate_v1` | ~1–2 s |
| `health` | ~2 s |
| `fingerprint` | ~30–40 s |
| Snapshot verify (91 refs) | ~0.6 s |

Bottleneck: Tiingo ×14 full history + FRED/ALFRED pagination + Fed HTML pages.

---

## 19. Rate limits and retries (audit)

| Provider | Timeout | Retries | Backoff | 429 handling |
| --- | --- | --- | --- | --- |
| Tiingo | 120s | **0** | — | None |
| FRED/ALFRED | 120s | 4 | `2×(attempt+1)` s | Retry on 5xx/connection |
| Fed HTML | 90s | 5 | `2×(attempt+1)` s | 404 not retried |

**10B SHOULD:** Add minimal Tiingo retry for transient errors. **Do not** retry validation failures.

---

## 20. Provider failure semantics

| Provider | Required for successful update? |
| --- | --- |
| Tiingo (14 ETFs) | **Yes** |
| FRED current + ALFRED | **Yes** |
| Fed FOMC HTML | **Yes** |
| WTI (FRED DCOILWTICO) | **Yes** (part of `wti_context` stage) |
| Elections / NYSE | **Yes** (deterministic; failure = code error) |

Skipping a required source → **FAILED run**, not SUCCESS.

---

## 21. Phase 10B implementation backlog

### MUST

| Item | Description |
| --- | --- |
| `stockballdb.update` module | Orchestrator calling existing `stage_*` functions |
| `run_as_of` propagation | Refactor `today_ny()` call sites in update path to accept boundary |
| Preflight package | DB, Alembic, credentials, paths, advisory lock, primary DB guard |
| Alembic gate | Fail if revision ≠ head; **no** silent migrate during update |
| Advisory lock | Prevent concurrent updates |
| `live_build_context` | Snapshot capture unchanged |
| validate_v1 + health gates | Fail exit on validate_v1 or UNHEALTHY |
| fingerprint before/after | Change detection |
| Operational run report | Success and failure JSON + log |
| Manifest 1.1 on success only | Reuse `manifest_from_health_report` |
| Exit codes | 0 success / non-zero failure |
| Tests per §22 | See certification matrix |

### SHOULD

| Item | Description |
| --- | --- |
| Tiingo transient retry | Match FRED reliability |
| `--strict` health passthrough | For automation |
| `STOCKBALLDB_PRIMARY_DATABASE_NAME` | Optional DB identity guard |
| Post-success snapshot verify | Quick integrity check |

### DEFER

| Item | Reason |
| --- | --- |
| Incremental Tiingo/FRED fetch | Revision risk; full refetch certified |
| `--resume` / checkpoint | Rerun sufficient |
| `--dry-run` | No operational value |
| Same-run snapshot reuse | Simplicity |
| trading_days two-txn merge | Low frequency failure; document rerun |
| Shadow/staging DB promote | Unnecessary complexity |
| Scheduler configuration | Phase 10 boundary |

---

## 22. Phase 10C certification matrix (plan)

| Test | Expected |
| --- | --- |
| **A. Fresh update** | PASS; snapshots; validate_v1; health; fingerprint; manifest |
| **B. Immediate no-change rerun** | PASS; `SUCCESS_NO_CHANGE`; same DB fingerprint |
| **C. Controlled failure** | FAILED; no success manifest; failure report exists |
| **D. Recovery rerun** | Converges; validate_v1 PASS; health acceptable |
| **E. Concurrency** | Second update rejected safely |
| **F. Reproducibility** | Successful update manifest usable by REBUILD EXACT (spot-check, not full 30-min cert unless required) |

Additional: preflight failure, provider failure, validation failure, health ERROR, secret sanitization in reports, single `run_as_of` propagation.

---

## 23. Explicit exclusions (confirmed)

Phase 10A introduced **no** excluded infrastructure, datasets, or research scope. Audit confirms no creep into Airflow, Redis, new financial series, Explorer UI, or scheduling platforms.

---

## 24. Phase 10A verification (2026-08-29)

Phase 10A changed **documentation only**. Baseline verification required:

```text
pytest       = 120/120 PASS
validate_v1  = PASS
health       = HEALTHY
```

Canonical data unchanged. Database fingerprint should match Phase 9 certification unless primary DB legitimately changed since certified BUILD.

---

## 25. Document history

| Version | Date | Change |
| --- | --- | --- |
| 1.0 | 2026-08-29 | Phase 10A audit + contract lock |
| 1.1 | 2026-08-29 | Phase 10B implementation record (§26) |

---

## 26. Phase 10B implementation record (2026-08-29)

Phase 10B delivered `python -m stockballdb.update` orchestrating existing `UPDATE_STAGES`, preflight, PostgreSQL advisory lock, fingerprint before/after change detection, validate_v1 + health gates (UNHEALTHY fails), Manifest 1.1 on success only, and per-run JSON reports under `build_reports/run_<run_id>.json`.

Operator guide: [`StockBallDB_operational_update.md`](StockBallDB_operational_update.md).

Verification (no live update performed):

```text
pytest       = 142/142 PASS (21 new update tests)
validate_v1  = PASS
health       = HEALTHY
fingerprint  = sha256:9e474ed3105b9fbdd43b213ce36f415d3f11e804f01aa20716b3629ae7a65138 (unchanged)
```

**NEXT:** Phase 10C — operational certification (live update matrix per §22).
