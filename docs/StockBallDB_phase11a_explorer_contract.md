# StockBallDB — Phase 11A: Explorer Audit & Contract

**Version:** 1.0 (Phase 11A lock)  
**Date:** 2026-08-30  
**Status:** Authoritative contract for Phase 11B implementation  
**Prerequisite:** Phase 10 COMPLETE (certified operational update, Manifest 1.1, REBUILD EXACT)

---

## 1. Purpose and architectural boundary

### 1.1 Purpose

Phase 11 delivers **StockBallDB Explorer** — a **local, read-only inspection interface** that makes the certified historical database understandable, verifiable, and auditable by a human operator.

The Explorer answers factual inspection questions:

```text
What data exists?
What does this row/date/symbol contain?
Where did this value come from (dataset/build level)?
How much history do we have?
Where are the gaps?
What is database health?
What happened on this particular date?
Which manifest/snapshot/build produced the current state?
```

It does **not** answer research or trading questions:

```text
Should I buy this?
Which ETF is strongest?
What predicts tomorrow?
Which strategy works best?
What happens if I backtest this rule?
```

### 1.2 Locked boundary

> **StockBallDB Explorer is a read-only inspection interface for understanding, verifying, tracing, and auditing data already contained in or produced by StockBallDB.**

It is **NOT**:

```text
research workbench
experiment runner
backtesting platform
signal generator
screening engine
prediction system
strategy builder
portfolio manager
trading dashboard
order-entry interface
database editor
manual data-correction UI
```

The Explorer **must not** change StockBallDB's architectural boundary. Canonical schema, provider pipelines, validation rules, and operational update remain in the existing package. Explorer **displays** canonical facts; it does not **create** new financial definitions.

### 1.3 Phase structure

| Sub-phase | Scope | Status after 11A |
| --- | --- | --- |
| **11A** | Audit + Explorer contract (this document) | **COMPLETE** |
| **11B** | Explorer implementation | **NOT STARTED** |
| **11C** | Explorer verification & closeout | **NOT STARTED** |

### 1.4 Non-goals (Phase 11 overall)

See §23. No database mutation, no operational update/rebuild triggers, no new canonical tables/metrics, no research/trading scope, no cloud deployment or authentication in Phase 11.

---

## 2. Existing repository capability audit

### 2.1 Reusable structured Python APIs

The Explorer **must** call shared package functions — **not** shell out to CLI commands and parse text.

| Capability | Primary module | Key callables | Structured return |
| --- | --- | --- | --- |
| Database engine/session | `stockballdb.db` | `get_engine()`, `session_scope()` | SQLAlchemy `Engine` / `Session` |
| Settings | `stockballdb.config` | `load_settings()` | `Settings` dataclass |
| Health | `stockballdb.health.engine` | `run_health(engine)` | `HealthReport` |
| Health JSON | `stockballdb.health.render` | `report_to_dict(report)` | `dict` |
| Coverage | `stockballdb.health.coverage` | `collect_table_coverage()`, `collect_symbol_coverage()` | dataclass lists |
| Freshness / gaps | `stockballdb.health.freshness`, `gaps` | `collect_freshness()`, `gap_findings()` | dataclass lists |
| Limitations registry | `stockballdb.health.limitations` | `MACRO_FIELD_FLOORS`, `EXPECTED_LIMITATIONS`, etc. | constants |
| validate_v1 | `stockballdb.validate_v1` | `validate_v1_database(engine)` | `list[str]` diagnostics; raises `ValidateV1Error` |
| Diagnostics snapshot | `stockballdb.v1.stages` | `collect_diagnostics(engine)` | `dict` (counts + min/max) |
| Fingerprint | `stockballdb.fingerprint.compute` | `compute_database_fingerprint(engine)` | `DatabaseFingerprint` |
| Manifest / provenance | `stockballdb.health.provenance` | `reports_dir()`, `git_provenance()`, `classify_manifest()` | `dict` / `Path` |
| Snapshots | `stockballdb.snapshots.store`, `verify` | `SnapshotStore`, `verify_manifest()`, `load_manifest()` | dataclasses / reports |
| Operational runs | `stockballdb.update.report` | read `run_*.json` from `build_reports/` | JSON on disk |
| Symbol registry | `stockballdb.market_data.universe` | `V1_MARKET_SYMBOLS`, `asset_type_for_symbol()` | constants + helpers |
| Event types | `stockballdb.events.types` | `EVENT_TYPES` | enum/tuple |
| Macro series | `stockballdb.macro.series` | `MACRO_SERIES` | series metadata |

### 2.2 CLI-only or text-primary today

| Component | Gap for Explorer | 11B approach |
| --- | --- | --- |
| `validate_v1` CLI | No typed report object | Call `validate_v1_database()` directly; wrap diagnostics in Explorer service layer |
| `build_v1` stage output | Console text | Not used by Explorer |
| `check_db` | CLI-only | Explorer uses `check_connection()` or health DB section |
| Per-table `build_*` CLIs | Console only | Not used by Explorer |

**No 11A refactors required.** Optional 11B SHOULD: thin `ValidateV1Result` dataclass wrapping diagnostics + pass/fail — not mandatory.

### 2.3 Authoritative documentation sources

| Need | Document |
| --- | --- |
| Table layout | `docs/StockBallDB_schema.md` |
| Field definitions | `docs/StockBallDB_definitions.md` |
| Asset scope | `docs/StockBallDB_universe.md` |
| Providers | `docs/StockBallDB_sources.md` |
| PIT / macro semantics | `docs/StockBallDB_phase4a_macro_contract.md` |
| Events semantics | `docs/StockBallDB_phase6a_scheduled_events_contract.md` |
| Calendar context | `docs/StockBallDB_phase7a_calendar_context_contract.md` |
| Health / coverage | `docs/StockBallDB_phase8a_validation_provenance_contract.md` |
| Snapshots / rebuild | `docs/StockBallDB_phase9a_snapshot_rebuild_contract.md` |
| Operational update | `docs/StockBallDB_operational_update.md` |

Explorer definitions UI **must reuse** these sources — no contradictory UI-only definitions.

### 2.4 Filesystem artifacts (read-only)

| Path | Content | Discovery |
| --- | --- | --- |
| `build_reports/manifest_*.json` | Manifest 1.0 / 1.1 | Glob + sort by `build_started_at` desc |
| `build_reports/run_*.json` | Operational run reports | Glob + sort by `started_at` desc |
| `build_reports/v1_*.txt` | Legacy text build reports | Optional display; lower priority |
| `snapshots/` (content-addressed) | Immutable provider payloads | Via `SnapshotStore.resolve_payload_path()` only |
| `docs/StockBallDB_definitions.md` | Field help text | Static read for tooltips |

All under gitignore except docs. Explorer reads from configured repo paths via existing helpers (`reports_dir()`, `SnapshotStore`).

---

## 3. Seven canonical tables — inspection inventory

Live baseline (Phase 10C certified primary DB, 2026-08-30):

| Table | Rows | First date | Last date | PK | Secondary index |
| --- | ---: | --- | --- | --- | --- |
| `trading_days` | 17,532 | 1957-01-02 | 2026-08-28 | `date` | — |
| `daily_market_data` | 99,633 | 1986-01-02 | 2026-08-28 | `(date, symbol)` | `ix_daily_market_data_symbol_date (symbol, date)` |
| `market_outcomes` | 99,633 | 1986-01-02 | 2026-08-28 | `(date, symbol)` | `ix_market_outcomes_symbol_date` |
| `asset_regimes` | 99,633 | 1986-01-02 | 2026-08-28 | `(date, symbol)` | `ix_asset_regimes_symbol_date` |
| `macro_conditions` | 17,532 | 1957-01-02 | 2026-08-28 | `date` | — |
| `scheduled_events` | 2,641 | 1957-01-08 | 2026-08-12 | `event_id` | `ix_scheduled_events_type_date (event_type, event_date)` |
| `calendar_context` | 17,532 | 1957-01-02 | 2026-08-28 | `date` | — |

**Symbols:** 15 market symbols (14 ETFs + WTI close-only). **Manifests:** variable count in `build_reports/`. **Snapshots:** 91 in latest certified manifest.

### 3.1 Per-table Explorer contract

#### `trading_days`

- **Grain:** one row per NYSE trading session  
- **Filters:** date from/to, weekday, month, year, `is_month_end`, `is_quarter_end`  
- **Display columns:** all 15 canonical fields  
- **NULL patterns:** `prev_trading_date` NULL at spine start; `next_trading_date` NULL at spine end  
- **Relationships:** parent of all date-keyed tables except `scheduled_events`  
- **Confusing fields:** ISO week vs calendar week — tooltip from definitions  
- **Views:** Data Explorer table; Day Inspector header; Coverage spine reference  

#### `daily_market_data`

- **Grain:** `(date, symbol)`  
- **Filters:** symbol (required or optional multi), date from/to, asset_type  
- **Sort:** date, symbol (default: date ASC, symbol ASC)  
- **Display:** OHLC/adj OHLC, corp actions, derived fields — with definitions for raw vs adjusted  
- **NULL patterns:** pre-inception symbols absent (not NULL rows); WTI close-only row shape (NULL OHLC except close); derived NULL during warm-up  
- **Confusing fields:** `return_1d` basis (adj close); WTI has no OHLC  
- **Views:** Data Explorer; Day Inspector symbol section; Coverage by symbol  

#### `market_outcomes`

- **Grain:** `(date, symbol)`  
- **Filters:** symbol, date from/to  
- **NULL patterns:** forward horizons NULL near series tail (not yet computable) — **must not** display as error  
- **Confusing fields:** forward return windows vs calendar days  
- **Views:** Data Explorer; Day Inspector symbol section  

#### `asset_regimes`

- **Grain:** `(date, symbol)`  
- **Filters:** symbol, date from/to, optional regime label filters (browse stored values only)  
- **NULL patterns:** rolling window warm-up; vol regime NULL until sufficient history  
- **Views:** Data Explorer; Day Inspector symbol section  

#### `macro_conditions`

- **Grain:** one row per trading day  
- **Filters:** date from/to  
- **Display:** all macro fields with units (% vs pp per definitions)  
- **NULL patterns:** historical floors per `MACRO_FIELD_FLOORS`; pre-floor = expected unavailable  
- **PIT labels:** derive from Phase 4A contract + field metadata where documented  
- **Views:** Data Explorer; Day Inspector market-wide section  

#### `scheduled_events`

- **Grain:** one row per event instance  
- **Filters:** `event_type`, date from/to, symbol (for applicable types)  
- **Important:** `event_date` may be **non-trading** — no FK to `trading_days`  
- **Views:** Data Explorer; Day Inspector events section; non-trading date lookup  

#### `calendar_context`

- **Grain:** one row per trading day (1:1 with `trading_days`)  
- **Filters:** date from/to, boolean flags (holiday, FOMC week, CPI week, etc.)  
- **Views:** Data Explorer; Day Inspector calendar section  

---

## 4. Technology comparison and locked recommendation

### 4.1 Requirements summary

```text
Local Python + PostgreSQL inspection app
Interactive tables, filters, pagination
Reuse SQLAlchemy + existing health/validation APIs
Desktop-first, single developer maintainability
Minimal new dependencies
Testable service layer separate from UI
No consumer SaaS polish required
```

### 4.2 Comparison

| Criterion | Streamlit | Dash (Plotly) | FastAPI + React | Flask + Jinja templates |
| --- | --- | --- | --- | --- |
| Python-native integration | Excellent | Good | Split stack | Good |
| SQLAlchemy reuse | Direct | Direct | Via API layer | Direct |
| Interactive tables/filters | Built-in `st.dataframe`, widgets | DataTable callbacks | Build in React | Manual HTML/JS |
| Local dev complexity | Low | Medium | High (2 projects) | Medium |
| Pagination UX | Straightforward | Callback-heavy | Flexible | Manual |
| Testing | Service layer unit tests; limited UI tests | Similar | API tests + frontend tests | Template tests |
| Dependency weight | Moderate (+ streamlit) | Moderate (+ dash, plotly) | Heavy (npm ecosystem) | Light |
| Charts for inspection | `st.line_chart` / Altair optional | Native Plotly | Chart library choice | Manual |
| Maintainability (solo) | High | Medium | Lower | Medium |
| Future portability | Local app; not locked to cloud | Same | Over-engineered for scope | Same |

### 4.3 Locked recommendation: **Streamlit**

**Phase 11B will implement Explorer as a Streamlit application** launched via:

```text
python -m stockballdb.explorer
```

**Reasoning:**

1. Smallest path to useful interactive tables and filters for seven known tables.  
2. Keeps all logic in Python — aligns with existing stack (`pyproject.toml`).  
3. Service/query layer remains framework-agnostic and unit-testable.  
4. No separate frontend build, npm, or API contract maintenance.  
5. Local `localhost` execution matches Phase 11 local-first scope.  
6. Descriptive charts (coverage timeline, single-series inspection) available without Dash/React overhead.

**Rejected for V1:**

- **Dash** — callback complexity disproportionate to scope.  
- **FastAPI + React** — two-layer architecture unjustified for internal read-only tool.  
- **Flask templates** — more manual work for interactive filtering/pagination.

### 4.4 New dependencies (11B only — not installed in 11A)

| Package | Purpose |
| --- | --- |
| `streamlit` | UI framework |

Optional SHOULD: `altair` or use Streamlit native charts only for V1.

**Do not add** React, npm, Redis, or Celery.

---

## 5. Read-only enforcement architecture

### 5.1 Principle

Read-only is enforced at **multiple layers** — not merely by omitting edit buttons.

### 5.2 MUST (11B)

| Layer | Mechanism |
| --- | --- |
| **Application code** | Explorer package contains **zero** INSERT/UPDATE/DELETE/TRUNCATE/DDL. Code review + tests assert no DML SQL strings. |
| **Query layer** | Parameterized SQLAlchemy queries / Core `select()` only. **No raw SQL console.** No string-concatenated user SQL. |
| **Session guard** | Explorer DB access module documents read-only intent; use read-only transactions where supported (`connection.execution_options(postgresql_readonly=True)` or `SET TRANSACTION READ ONLY`). |
| **Operational actions** | **No** update button. **No** rebuild button. **No** manual correction UI. |
| **Filesystem** | Read-only opens of manifests/snapshots; path resolution only through `SnapshotStore` / `reports_dir()` — no arbitrary path picker. |

### 5.3 SHOULD (operator hardening)

| Layer | Mechanism |
| --- | --- |
| **PostgreSQL role** | Dedicated read-only DB user (`stockballdb_explorer`) with `SELECT` on canonical tables only. Optional env: `STOCKBALLDB_EXPLORER_DATABASE_URL`. Document in operator guide. |
| **Fallback** | If read-only URL not set, use `DATABASE_URL` with application safeguards above. |

### 5.4 MUST NOT

```text
Raw SQL console
Ad-hoc query textarea
Database editing
Trigger update/rebuild from UI
```

DBeaver remains the tool for unrestricted SQL inspection by advanced operators.

---

## 6. Information architecture and navigation

### 6.1 Six conceptual areas → Streamlit pages

Use Streamlit **multipage app** (`pages/` or `st.navigation`):

| # | Area | Page | Purpose |
| --- | --- | --- | --- |
| 1 | **Control Center** | Home / `1_Control_Center.py` | At-a-glance health, fingerprint, latest run, table summary |
| 2 | **Data Explorer** | `2_Data_Explorer.py` | Browse any canonical table with filters |
| 3 | **Day Inspector** | `3_Day_Inspector.py` | Cross-table view for one date (+ optional symbol) |
| 4 | **Coverage Explorer** | `4_Coverage_Explorer.py` | Coverage, gaps, missingness classification |
| 5 | **Provenance Explorer** | `5_Provenance_Explorer.py` | Manifests, run reports, snapshots, fingerprints |
| 6 | **Validation Center** | `6_Validation_Center.py` | validate_v1, health findings, snapshot verify |

**Sidebar:** page selector + global **Refresh** button (manual reload — no WebSockets/polling daemon).

### 6.2 Global chrome

- App title: **StockBallDB Explorer**  
- Subtle status strip: DB connected / health status / last refreshed timestamp  
- No market ticker widgets, heatmaps, or signal scores  

---

## 7. Control Center contract

**Purpose:** At a glance — is StockBallDB healthy, current, reproducible, and ready to inspect?

### 7.1 Data sources (reuse)

| Display | Source |
| --- | --- |
| Health status | `run_health()` → `HealthReport.status` |
| validate_v1 | `HealthReport.validate_v1_pass` or on-demand `validate_v1_database()` |
| Table row counts / date ranges | `collect_table_coverage()` or `collect_diagnostics()` |
| Symbol coverage summary | `collect_symbol_coverage()` or health JSON |
| Database fingerprint | `compute_database_fingerprint()` |
| Alembic revision | health report / DB query |
| Git provenance | `git_provenance()` |
| Latest operational run | newest `build_reports/run_*.json` by timestamp |
| Latest Manifest 1.1 | newest successful `build_reports/manifest_*.json` |
| Last update result | run report `status` / `change_classification` |
| Provider freshness | health `freshness` section |
| Snapshot verify status | on-demand `verify_manifest()` for latest manifest (cached until Refresh) |
| Unresolved datasets | `limitations.UNRESOLVED_SYMBOLS`, docs reference — **documentation only**, not fake tables |

### 7.2 Status language (locked)

Reuse existing terminology — do not invent alternatives:

```text
HEALTHY / HEALTHY WITH WARNINGS / UNHEALTHY
PASS / FAIL
SUCCESS_UPDATED / SUCCESS_NO_CHANGE / FAILED (+ failure_kind)
```

### 7.3 Excluded from Control Center

```text
SPY price widget (unless linked to Data Explorer as navigation — not a dashboard tile)
Market heatmap
Bull/bear score
Trading signals
Buy/sell indicators
```

---

## 8. Data Explorer contract

### 8.1 Scope

All seven canonical tables browsable with server-side filtering, deterministic sorting, and pagination.

### 8.2 Filters per table (locked)

| Table | Filters |
| --- | --- |
| `trading_days` | date from/to |
| `daily_market_data` | symbol, date from/to |
| `market_outcomes` | symbol, date from/to |
| `asset_regimes` | symbol, date from/to |
| `macro_conditions` | date from/to |
| `scheduled_events` | event_type, date from/to |
| `calendar_context` | date from/to; optional boolean flag filters (stored fields only) |

No filters named or implying recommendations (`best momentum`, `buy candidates`, etc.).

### 8.3 Query safety (locked)

```text
Server/database-side filtering (WHERE in SQL — not load-all-filter-in-Python)
ORDER BY deterministic PK or (date, symbol)
Pagination required — no unbounded full-table fetch
Default page size: 100 rows
Maximum page size: 500 rows
Hard cap on total export if CSV export enabled (see §12)
```

### 8.4 Sorting

- **V1:** single-column sort on explicit allowlist per table (date, symbol, event_type, event_date, event_id).  
- Default: PK order (date ASC, symbol ASC where applicable).  
- **No** arbitrary multi-column user sort builder in V1.

### 8.5 Raw SQL console

**Locked: NO.**

---

## 9. Day Inspector contract

### 9.1 Purpose

Given one calendar/trading context date, show canonical information associated with that date across the database — **factual cross-table inspection**, not market analysis.

### 9.2 Input model

```text
Primary input: date (ISO YYYY-MM-DD)
Optional: symbol (focus market tables)
Default symbol view: all symbols (paginated table sections)
```

Selecting a symbol focuses `daily_market_data`, `market_outcomes`, `asset_regimes` to that symbol; macro, calendar, and events remain market-wide.

### 9.3 Query pattern (locked)

**Separate bounded queries** — not one giant join:

```text
1. Resolve date context (trading day? event-only? weekend/holiday?)
2. trading_days row (if exists)
3. calendar_context row (if trading day)
4. macro_conditions row (if trading day)
5. scheduled_events for event_date (may exist without trading day)
6. daily_market_data rows (all symbols or filtered — paginated)
7. market_outcomes rows
8. asset_regimes rows
```

### 9.4 Date semantics (locked)

| Input date type | Behavior |
| --- | --- |
| **Trading day** (in `trading_days`) | Full inspector: all sections populated per data availability |
| **Scheduled event on non-trading day** (e.g. 1958-11-04 Election) | Show: "Trading session: none"; display matching `scheduled_events`; show next/previous trading session from spine; **do not fabricate** trading_day row |
| **Weekend/holiday with no event** | Show: "Trading session: none"; no events unless present; link to nearest trading sessions |
| **Date outside StockBallDB history** | Clear "outside coverage" message with spine bounds |

**Example (Election 1958-11-04):**

```text
Calendar date: 1958-11-04
Trading session: none
Scheduled event: Election Day
Effective next StockBallDB session: 1958-11-05
```

Reuse `scheduled_events` + `trading_days` lookup — no fabricated rows.

### 9.5 Excluded

```text
Comparative scoring across symbols
Signal interpretation
"Market summary" narrative generation
```

---

## 10. Coverage Explorer contract

### 10.1 Purpose

Show what StockBallDB contains and where data is missing — reusing Phase 8 health/coverage logic.

### 10.2 Data sources (reuse — do not reinvent)

| Display | Source |
| --- | --- |
| Per-table first/last/count | `collect_table_coverage()` |
| Per-symbol coverage %, gaps | `collect_symbol_coverage()` |
| Freshness / lag | `collect_freshness()` |
| Gap findings | `gap_findings()` |
| Historical floors | `MACRO_FIELD_FLOORS`, `EVENT_FAMILY_FLOORS`, `WTI_INCEPTION` |
| Unresolved datasets | `UNRESOLVED_SYMBOLS`, `UNRESOLVED_MACRO`, `EXPECTED_LIMITATIONS` |

### 10.3 Missingness classification (locked)

UI must distinguish (reuse health `MissingnessClass` / finding codes where available):

```text
expected historical floor
asset not yet in existence (pre-inception)
provider publication lag (INFO)
known provider gap (WTI)
warm-up NULL (rolling windows)
forward-outcome tail NULL (not yet computable)
unresolved dataset (documented)
actual integrity problem (ERROR/FATAL findings)
```

**Do not paint every NULL red.**

### 10.4 Charts (acceptable)

```text
Coverage timeline (sessions present vs eligible)
Missing-date sample visualization
Row counts by symbol (bar chart)
Freshness lag indicator
```

---

## 11. Provenance Explorer contract

### 11.1 Purpose

Explain where StockBallDB build state came from — **dataset/build level**, not row-level lineage unless explicitly stored.

### 11.2 What CAN be proven

| Provenance type | Source |
| --- | --- |
| Latest / historical Manifest 1.1 | `build_reports/manifest_*.json` |
| Operational run reports | `build_reports/run_*.json` |
| Snapshot references | manifest `snapshots[]` |
| Snapshot metadata | `SnapshotReference` fields + sidecar JSON (sanitized) |
| Snapshot verification | `verify_manifest()` |
| Git commit, dirty flag | manifest / `git_provenance()` |
| Alembic revision | manifest / health |
| Database + table fingerprints | manifest / live `compute_database_fingerprint()` |
| `exact_rebuild_capable` | `classify_manifest()` |
| Provider / series identity | manifest providers + docs |

### 11.3 What CANNOT be proven (must disclose)

```text
Per-row "this exact cell came from snapshot X byte offset Y"
Historical provider state at past calendar dates (without REBUILD EXACT context)
```

Navigate: Control Center → latest manifest → snapshot list → snapshot metadata.

### 11.4 Snapshot display (locked)

**Show:**

```text
snapshot_id, provider, source_identifier, source_type
retrieved_at, sha256, payload_path (relative), byte sizes
verification state
sanitized request_identity (no secrets)
```

**Do NOT** render multi-MB raw JSON/HTML payloads inline by default. Optional SHOULD: "view truncated preview (first N KB)" with warning.

### 11.5 Manifest / run report discovery

- Glob `reports_dir()` for `manifest_*.json` and `run_*.json`  
- Sort: **newest first** by embedded timestamp / `started_at`  
- Malformed JSON: skip with warning in UI — do not crash app  

### 11.6 Secret safety (locked)

**Never display:** API keys, auth headers, database URLs, passwords, tokens, unsanitized provider credentials. Reuse `scan_secrets()` patterns from provenance module.

---

## 12. Validation Center contract

### 12.1 Purpose

Make existing validation and health systems understandable — **no second validation engine**.

### 12.2 Sections

```text
validate_v1 (PASS/FAIL + diagnostic lines)
health findings (severity, code, dataset, message)
coverage findings
freshness
gap detection
snapshot verification (selected manifest)
database fingerprint
table fingerprints (7 tables)
```

### 12.3 Execution model (locked)

**Both:**

| Mode | Behavior |
| --- | --- |
| **Display latest** | Show results from most recent on-demand run in session (or cached at page load) |
| **Run on demand** | Buttons: "Run health", "Run validate_v1", "Verify latest manifest" — read-only, may take ~1–15s |

No database mutation. Runtime acceptable for local operator use.

### 12.4 Refresh

Manual **Refresh** / rerun buttons only — no background polling daemon.

---

## 13. Definitions, NULL, and units presentation

### 13.1 Definitions UX

Source: `docs/StockBallDB_definitions.md` (+ phase contracts for PIT notes).

**V1 approach:** parse or embed definition snippets for tooltips / expanders per table column. No full documentation CMS.

**Per field where available:**

```text
field name
plain-English definition
units
source
PIT / ex-post classification (where documented)
NULL semantics
```

### 13.2 NULL presentation (locked)

| Semantic | Display |
| --- | --- |
| Database NULL | `—` or `NULL` (consistent app-wide) |
| Not applicable | label when field N/A for row type (e.g. WTI OHLC) |
| Not yet computable | tooltip for forward-outcome tail |
| Outside history | "Pre-series" with floor date |
| Provider gap | link to Coverage Explorer finding |

**Never** render NULL as `0`. **Never** fabricate display values.

### 13.3 Units / formatting (display-only)

| Type | Rule |
| --- | --- |
| Prices | decimal as stored |
| Returns | decimal; optional % display with label |
| Macro rates | respect pp vs % per definitions — **no global % conversion** |
| Dates | ISO 8601 |
| Hashes | truncated with copy-full option |
| Booleans | Yes/No |

Stored canonical values remain authoritative; formatting is presentation layer only in `explorer/formatting.py`.

---

## 14. Charts, export, search, and UX constraints

### 14.1 Charts (descriptive only)

**Acceptable:** coverage timeline, missing-data timeline, row counts by symbol, single canonical series over time (e.g. SPY adj close, WTI close, macro field), freshness lag visual.

**Not acceptable:** technical indicators not in DB, signals, strategy equity curves, forecasts, correlation research, backtests.

### 14.2 Derived calculations in UI

**Allowed:** row counts, coverage %, missing counts, pagination metadata, display formatting.

**Forbidden:** new financial metrics not in canonical schema (momentum scores, custom signals, etc.).

### 14.3 CSV export

**SHOULD (11B):** export **current filtered page or bounded result set** (max 10,000 rows per export) with canonical values. Not MUST for first useful Explorer.

### 14.4 Global search

**Locked: NO.** Structured navigation and per-table filters sufficient for seven known tables.

### 14.5 Responsive / visual design

```text
Desktop-first
Basic responsive layout (Streamlit default)
Engineering/data inspection aesthetic — clarity, density, legibility
No marketing animations or decorative dashboards
```

---

## 15. Caching, connections, configuration

### 15.1 Caching

| Safe to cache (session-scoped) | Careful / refresh on demand |
| --- | --- |
| Parsed definitions snippets | Health report |
| Table metadata / column lists | Latest fingerprint |
| Manifest list (until Refresh) | Latest run report |
| Slow aggregate summaries | validate_v1 result |

**Prefer correctness over clever caching.** External `python -m stockballdb.update` may change DB while Explorer is open — manual Refresh clears session cache.

### 15.2 Database connections

Reuse `get_engine()` / `session_scope()` from `stockballdb.db`. Same `.env` / `Settings` as rest of project. No separate secrets file.

| Concern | Approach |
| --- | --- |
| Pooling | SQLAlchemy default engine pool |
| Lifetime | Per-request/session scope in Streamlit callbacks |
| Errors | User-safe messages; no connection strings in UI |

### 15.3 Entry point (locked)

```text
python -m stockballdb.explorer
```

Streamlit invoked programmatically or via `[project.scripts]` equivalent. Local browser at `localhost` default port.

---

## 16. Performance expectations

### 16.1 Dataset scale (current)

~100k rows per symbol-grain table; ~17k spine rows — **well within indexed pagination**. No billion-row optimization required.

### 16.2 Index adequacy

Existing PK + `(symbol, date)` indexes support expected Explorer filters. **No new indexes in 11B** unless profiling proves otherwise (would require separate justification — not expected).

### 16.3 Expensive views

| View | Risk | Mitigation |
| --- | --- | --- |
| Data Explorer full scan | High | Pagination + required date bounds for wide queries |
| Day Inspector all symbols | Medium | Paginate symbol tables; default 15 symbols manageable |
| Coverage | Low | Reuse health aggregates |
| Health on demand | Medium | ~1–2s; show spinner |
| Fingerprint | Medium | ~9s; run on demand only, cache in session |

### 16.4 Day Inspector — no mega-join

Locked in §9.3 — preserves NULL semantics and performance.

---

## 17. Security

| Risk | Mitigation |
| --- | --- |
| SQL injection | SQLAlchemy parameterized queries; table/column allowlists; no raw SQL console |
| Path traversal | Manifest/snapshot paths resolved only via `reports_dir()` / `SnapshotStore.resolve_payload_path()` |
| Secret exposure | `scan_secrets()` on displayed JSON; strip credentials from request_identity |
| HTML injection | Escape provider metadata in UI components |
| Arbitrary filesystem read | No open file picker; glob only known artifact patterns |
| Local-only scope | No auth system required; bind localhost by default |

Even local-only, follow safe patterns above.

---

## 18. Proposed package structure (11B — not created in 11A)

```text
src/stockballdb/explorer/
    __init__.py
    __main__.py          # python -m stockballdb.explorer
    app.py               # Streamlit entry / navigation
    config.py            # Explorer-specific settings (page sizes, cache TTL)
    db.py                # read-only engine/session helpers
    services/
        control.py       # Control Center data assembly
        tables.py        # Data Explorer queries
        day.py           # Day Inspector queries
        coverage.py      # Coverage wrappers around health modules
        provenance.py    # Manifest/run/snapshot discovery
        validation.py    # validate_v1 + health + verify wrappers
    formatting.py        # NULL, units, hash display
    definitions.py       # Load tooltips from docs/definitions
    artifacts.py         # Safe manifest/run report loading
    pages/               # Streamlit multipage (or st.navigation modules)
        1_Control_Center.py
        2_Data_Explorer.py
        3_Day_Inspector.py
        4_Coverage_Explorer.py
        5_Provenance_Explorer.py
        6_Validation_Center.py
tests/
    test_explorer_*.py   # Service-layer tests (no brittle screenshot tests)
```

**Service boundary (locked):**

```text
Streamlit UI → explorer.services.* → existing stockballdb APIs / SQLAlchemy → PostgreSQL + build_reports/
```

UI components **must not** contain large raw SQL strings.

### 18.1 Small refactors acceptable in 11B (not 11A)

| Refactor | Priority |
| --- | --- |
| Optional `ValidateV1Result` dataclass | SHOULD |
| Extract manifest listing helper to `health/provenance.py` | SHOULD |
| Read-only engine factory accepting explorer URL | SHOULD |

---

## 19. Phase 11B backlog

### 19.1 MUST

| Item | Description |
| --- | --- |
| Entry point | `python -m stockballdb.explorer` (Streamlit) |
| Read-only DB access | Parameterized queries; no DML; session read-only intent |
| Control Center | Health, fingerprint, latest run/manifest, table summary |
| Data Explorer | All 7 tables; filters; pagination; allowlisted sort |
| Day Inspector | Trading + non-trading event dates; optional symbol focus |
| Coverage Explorer | Reuse health coverage/gap/missingness logic |
| Provenance Explorer | Manifest/run history; snapshot metadata; no secrets |
| Validation Center | On-demand health + validate_v1 + snapshot verify display |
| Definitions tooltips | From authoritative docs |
| Safe artifact access | `reports_dir()` + `SnapshotStore` only |
| Tests | Service layer per §20 |
| No mutation actions | No update/rebuild/edit/SQL console |

### 19.2 SHOULD

| Item | Description |
| --- | --- |
| CSV export | Bounded filtered export |
| Simple descriptive charts | Coverage timeline, single-series inspection |
| PostgreSQL read-only role | `STOCKBALLDB_EXPLORER_DATABASE_URL` + operator doc |
| `ValidateV1Result` wrapper | Cleaner Validation Center |
| Truncated snapshot preview | First N KB with warning |

### 19.3 DEFER

| Item | Reason |
| --- | --- |
| Update / rebuild buttons | Violates read-only boundary; process management scope |
| Authentication / multi-user | Out of Phase 11 scope |
| Cloud deployment / HTTPS | Local-first |
| Advanced charting | Not required for inspection V1 |
| Global search | Low value for 7 tables |
| Raw SQL console | Safety + scope |
| Mobile app | Desktop-first |
| Row-level lineage | Not stored in canonical schema |
| Real-time streaming / WebSockets | Manual refresh sufficient |

---

## 20. Phase 11B test plan

Unit/integration tests on **service layer** (no Streamlit screenshot tests required):

| Area | Tests |
| --- | --- |
| Read-only queries | No DML in query modules; grep/static check |
| Pagination | Offset/limit math; max page size enforced |
| Filters | symbol/date/event_type validation; reject invalid inputs |
| Sort allowlist | Unknown column rejected |
| Day Inspector | Trading date; non-trading event date (1958-11-04); outside range |
| Coverage | Delegates to health; missingness labels present |
| Manifest discovery | Newest-first sort; malformed JSON skipped gracefully |
| Snapshot metadata | Secret sanitization; path traversal blocked |
| Health/validation integration | Mock engine; run_health / validate_v1 wrappers |
| NULL formatting | NULL not rendered as zero |
| SQL injection | Parameter binding for user filters |

Optional: Streamlit smoke test that app module imports without launching server.

---

## 21. Phase 11C certification matrix

### 21.1 Read-only certification (critical)

```text
fingerprint_before = compute_database_fingerprint(primary)
exercise every Explorer page and on-demand validation action
fingerprint_after  = compute_database_fingerprint(primary)

Expected: MATCH
```

Also: code audit confirms zero DML paths; optional test with read-only PG role rejects writes.

### 21.2 Functional certification

| Area | Checks |
| --- | --- |
| **Control Center** | Health visible; latest run; fingerprint; table coverage; Alembic |
| **Data Explorer** | All 7 tables browsable; filter works; pagination works; sort works |
| **Day Inspector** | Normal trading date; non-trading event date; symbol focus; macro/events/calendar |
| **Coverage Explorer** | ETF inception; WTI provider gaps; macro floors; forward-outcome tail NULLs labeled |
| **Provenance Explorer** | Manifest 1.1 fields; snapshot list; hashes; exact_rebuild_capable; no secrets |
| **Validation Center** | validate_v1 PASS; health findings; snapshot verify; fingerprints |

### 21.3 Regression (must not change canonical DB)

```text
pytest       = all PASS
validate_v1  = PASS
health       = acceptable
fingerprint  = unchanged after Explorer certification session
```

---

## 22. Explicit exclusions (confirmed)

Phase 11A introduces **no** excluded scope. Locked OUT for Phase 11 overall:

```text
research experiments, backtesting, strategy testing, signals, predictions
recommendations, screeners, portfolio tools, trading, broker integration
alerts, live streaming quotes, database editing, raw SQL console
manual corrections, update button, rebuild button
new data sources, new canonical metrics
Gold, DXY, PMI, GDP implementation
new event families
cloud deployment, authentication, multi-user permissions, mobile app
Airflow, Celery, Kafka, Redis, Docker/Kubernetes orchestration
```

Unresolved symbols (XAU/USD, DXY, PMI) may appear as **documentation/status only** in Control Center — not as fake canonical data.

---

## 23. Phase 11A verification (2026-08-30)

Phase 11A changed **documentation only**.

```text
pytest       = 142/142 PASS
validate_v1  = PASS
health       = HEALTHY
fingerprint  = sha256:9e474ed3105b9fbdd43b213ce36f415d3f11e804f01aa20716b3629ae7a65138
```

Canonical data unchanged. Matches Phase 10C certified primary fingerprint.

---

## 24. Document history

| Version | Date | Change |
| --- | --- | --- |
| 1.0 | 2026-08-30 | Phase 11A audit + contract lock |

**NEXT:** Phase 11B — StockBallDB Explorer Implementation
