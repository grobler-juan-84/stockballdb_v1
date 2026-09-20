# StockBallDB — V2 Architecture

**Status:** Working architecture baseline (backend / application / React communication)  
**Authority:** Detailed V2 application + frontend communication architecture; lockable decisions also recorded in [StockBallDB_V2_decisions.md](StockBallDB_V2_decisions.md)  
**Companion docs:** [index](StockBallDB_index.md) · [V2 scope](StockBallDB_V2_scope.md) · [V2 progress](StockBallDB_V2_progress.md) · [V1 status](StockBallDB_V1_status.md) · [explorer](StockBallDB_explorer.md) · [workflow](StockBallDB_workflow.md)

This document designs the **V2 backend / application architecture** and the **React ↔ Python communication architecture** around the certified V1 system. It is not an implementation plan for universe file format, GitHub auth, backup format, desktop packaging (Electron vs Tauri), endpoint schemas, or UI styling.

**No V2 application packages, React app, or transport server are created yet.** Paths below are proposed targets.

---

## 1. Design verdict

V2 adds a **thin in-process Python application façade** and, for the React UI, a **thin localhost-only HTTP transport** on top of that façade.

```text
V1 (preserved):
  Streamlit Explorer → existing V1 services/core → PostgreSQL

V2:
  React UI
    → frontend application client
      → localhost-only HTTP JSON transport  (NEW: thin; not the business layer)
        → stockballdb.app façade  (NEW: use-case layer; read vs maintenance)
          → existing V1 domain / data / orchestration
            → PostgreSQL / providers / snapshots / filesystem / (later) GitHub universe transport

V3 / StockBallAPP (future):
  React UI (same boundary)
    → same transport + expanded application façade
      → StockBallDB core + future research capabilities
```

Principles:

* Evolve V1; do not rewrite core pipelines/schema.
* React is the forward-facing V2/V3 UI; Streamlit remains the certified V1 Explorer (legacy/reference/diagnostic).
* Business logic lives in `stockballdb.app`, not in React and not in HTTP handlers.
* Transport exists because React is a separate language/process — not because StockBallDB is becoming SaaS.
* Do not build enterprise job platforms, auth systems, or cloud APIs for V2.

Earlier planning deferred HTTP while the UI technology was open. **React creates a real process boundary**; the cleanest fit is now a **local HTTP JSON API wrapping the façade**, bound to localhost only.

---

## 2. Layer model

A modular three-layer philosophy fits StockBallDB **if** Layer B is understood as “existing StockBallDB capabilities,” not a greenfield domain rewrite.

| Layer | Name | Responsibility |
| ----- | ---- | -------------- |
| **A** | Application / use-case | What the product can do: browse, inspect, status, update, fresh build, universe sync, backup/restore, exact rebuild. Returns structured results. No UI widgets. No provider HTTP details. |
| **B** | Domain / data services | Existing StockBallDB capabilities: explorer query services, domain pipelines, derivations, validation, health, fingerprints, build/update/rebuild orchestration, universe access (today: constants). |
| **C** | Infrastructure / persistence | PostgreSQL, SQLAlchemy engines/sessions, external providers, snapshot store, manifests/build reports, env/private config, future GitHub universe transport, future backup transport. |

### Why not force a different count?

V1 already has finer internal packages (`providers`, `snapshots`, `health`, `v1/stages`, etc.). Those remain **inside** Layers B/C. V2’s architectural addition is primarily **Layer A**. Collapsing V1 into three new packages would be a rewrite.

### Mapping to existing code

| Layer | Existing today | V2 addition |
| ----- | -------------- | ----------- |
| A | Partially foreshadowed by `explorer/services/*` (read-only, Streamlit-free) | New `stockballdb.app.*` façade covering read **and** maintenance use-cases |
| B | `explorer/queries`, `registry`, domain `*/`, `v1/stages`, `update/orchestrator`, `validate_v1`, `health`, `fingerprint`, `rebuild_exact`, `market_data/universe.py` | Prefer wrap/adapt; extend query capabilities as needed |
| C | `db.py`, `explorer/db.py`, `config.py`, `providers/*`, `snapshots/*`, `build_reports/`, `alembic` | Later: GitHub universe transport; backup/restore backend |

---

## 3. Application façade

### Responsibilities

The façade:

* exposes **use-case operations** to any UI;
* resolves **read vs write** connection policy;
* translates UI intents into calls on existing V1 APIs;
* returns **structured results** (status, diagnostics, warnings, paths) rather than CLI stdout contracts;
* hides schema internals, provider details, stage DAG, env-var layout, and snapshot storage layout from the UI;
* enforces StockBallDB scope (inspection/maintenance only — no research engines).

The façade does **not**:

* reimplement derivation, validation rules, or provider clients;
* own PostgreSQL schema;
* replace Exact Rebuild semantics;
* become a SaaS multi-tenant service layer.

### Recommended service boundaries

Prefer a small set of façade modules rather than one mega-service.

| Façade service | Operations (conceptual) | Wraps (primarily) |
| -------------- | ----------------------- | ----------------- |
| **Catalog** | list symbols; list tables/fields; field metadata/definitions pointers; date bounds | `universe` (evolving), `explorer/registry`, definitions access |
| **Explore** | browse/filter/sort/paginate; multi-symbol compare queries; bounded export | `explorer/queries`, `explorer/services/tables` |
| **Day** | inspect calendar/trading date; optional symbol filter; nearest sessions | `explorer/services/day`, `explorer/queries` |
| **Status** | health; validate_v1; fingerprint; coverage; provenance/manifests/run reports (read) | `health`, `validate_v1`, `fingerprint`, `explorer/services/{coverage,validation,control,provenance}`, artifacts |
| **Universe** | load local definition; validate definition; compare to remote; sync definition; report DB coverage gaps vs definition | new capability over portable definition; initially may adapt `market_data/universe.py` |
| **Maintenance** | fresh build; update database; exact rebuild; backup; restore; concurrency/status of maintenance runs | adapters over `build_v1.run_build_v1`, `update.run_update`, `rebuild_exact.run_rebuild_exact`; new backup/restore |

UI may call these services directly (in-process). No requirement that they share one class.

---

## 4. Read vs maintenance safety

V1 Explorer is deliberately read-only. V2 adds maintenance **without** collapsing that boundary.

| Path | Allowed | Connection policy |
| ---- | ------- | ----------------- |
| **Read / query** | browse, filter, compare, day inspect, coverage, provenance view, health/validate/fingerprint **viewing** | **Read-only** engine/connection only (`SET TRANSACTION READ ONLY` or equivalent). No INSERT/UPDATE/DELETE/DDL. |
| **Maintenance / mutate** | Fresh Build, Update, Exact Rebuild, universe definition sync (filesystem/git), Backup/Restore | Explicit **write** / maintenance engine and APIs. Must go through Maintenance (or Universe sync) façade — never through Explore/Day query helpers. |

### Architectural rules

1. Ordinary exploration code paths must not obtain a writable session.
2. Status operations that only read DB/filesystem use the read path (fix Control Center’s occasional use of shared `db.get_engine()` for inspection).
3. Mutating operations are deliberate façade entry points with structured results and existing concurrency controls where present (e.g. update advisory lock).
4. No authentication system is required for this personal local app; safety is **API boundary + connection policy + UX confirmation** (UX later), not multi-user IAM.

Health/validate/fingerprint are **read-safe** capabilities: they inspect state; they must not be bundled into Explore mutation risks, and they must not silently open write sessions.

---

## 5. Universe architecture

### Current V1

* Runtime universe = Python constants in `market_data/universe.py`.
* `StockBallDB_universe.md` = documentation only.
* Explorer symbol lists come from those constants, not `SELECT DISTINCT` from PostgreSQL.
* WTI is a distinct asset type / provider / stage (close-only), proving “all symbols are Tiingo ETFs” is false.
* Macro series (`macro/series.py`) and event types (`events/types.py`) are separate hard-coded definition maps.

### V2 Universe service (conceptual)

Owns:

* load local canonical **instrument** universe definition;
* validate definition structure and supported asset kinds;
* expose instruments to Catalog/Explore/Maintenance;
* compare local definition vs remote/canonical (GitHub);
* synchronize **definition only** (not database rows);
* report which instruments are required by definition but absent/incomplete in local DB;
* supply the active instrument set to build/update orchestration.

Does **not** (in this architecture step):

* choose file format;
* choose GitHub API/auth;
* fetch market prices;
* mutate PostgreSQL by itself.

### Instrument diversity

Universe entries must be able to express differences such as:

* asset type (e.g. etf vs commodity);
* provider / acquisition route;
* data shape (full OHLCV vs close-only);
* which pipeline stages apply.

Build/update continue to route instruments through the correct existing pipelines (ETF path vs WTI path, etc.). The façade must not flatten everything into one ETF assumption.

### Narrow “universe” vs broader “StockBallDB definition”

| Term | V2 stance |
| ---- | --------- |
| **Universe** | Narrow: **market instruments** intended for `daily_market_data` / outcomes / regimes (and related symbol-scoped data). |
| **Broader application/data definition** | Macro series maps, event definitions, calendar rules, etc. already exist as separate code. A single mega-definition document is **not** required for V2 start. Revisit later if portability demands it. |

Universe sync and database update remain **conceptually separate** (locked foundation decision). Update workflows may optionally check universe sync status first; that is orchestration convenience, not merging the two concepts.

---

## 6. Maintenance orchestration

| Capability | Existing API | V2 approach |
| ---------- | ------------ | ----------- |
| Fresh Build | `build_v1.run_build_v1` | **Wrap/adapt** — application Maintenance service |
| Update | `update.orchestrator.run_update` | **Wrap/adapt** |
| Exact Rebuild | `rebuild_exact.run_rebuild_exact` | **Wrap/adapt**; keep isolated semantics |
| validate / health / fingerprint / snapshot verify | existing callables | Prefer **Status** (read) or Maintenance post-gates; already reusable |

### Adapter principles

* Prefer **thin adapters** over rewriting stage DAGs or domain pipelines.
* Normalize CLI-oriented behavior (stdout progress, exit codes) into structured result objects for UI consumption.
* Preserve advisory locking / fail-fast stage behavior.
* Progress reporting, cancellation, and rich UX status are **open implementation details**; adapters should eventually allow progress callbacks if safe, but cancellation must not corrupt mid-transaction state — design later, do not invent unsafe cancel now.

---

## 7. Read / query architecture

### Foundation

Keep and evolve:

* `explorer/queries.py` — allowlisted parameterized SELECTs  
* `explorer/registry.py` — table specs  
* `explorer/db.py` — read-only engine/connection  
* `explorer/services/{tables,day,coverage,validation,control,provenance}` — Streamlit-independent today  

### What the UI should stop importing directly

Future V2 UI should call **Catalog / Explore / Day / Status** façade APIs rather than importing:

* `TABLE_REGISTRY` for widget construction;
* `V1_MARKET_SYMBOLS` constants;
* SQLAlchemy models;
* `db.get_engine()` write paths.

Schema/field metadata should be exposed through **Catalog** (derived from registry/definitions), not by leaking registry internals into presentation.

### Multi-symbol Explorer / Day Inspector backend needs

The Explore/Day façade must eventually support (backend contracts, not UI design):

* multiple symbols in one query/compare context;
* per-symbol field selection;
* shared date range / date context;
* filter, sort, pagination;
* navigation from explore results into day inspect.

Existing `query_table_page` / day fetch helpers are the starting point; multi-symbol compare may require **extended query operations** in Layer B without abandoning allowlisting.

V1 Streamlit `explorer/views` and `explorer/ui` remain presentation; they are not the V2 application boundary.

---

## 8. Database connection boundaries

| Use | Engine | Rule |
| --- | ------ | ---- |
| Explore / Day / Coverage / Catalog DB reads | Explorer read-only engine (`explorer/db` or successor under `app` policy) | READ ONLY transactions |
| Status reads (health, validate, fingerprint) | Prefer same read-only engine when the operation is read-only | Do not use write engine “because Control Center did” |
| Maintenance writes | Shared write engine (`db.get_engine` / settings `DATABASE_URL`) | Only via Maintenance façade |
| Exact Rebuild | Explicit rebuild target URL (existing rebuild guards) | Isolated from casual Explorer access |
| Tests | `STOCKBALLDB_TEST_DATABASE_URL` | Unchanged safety model |

Goal: make accidental mutation from ordinary exploration **architecturally difficult**.

---

## 9. Configuration boundary

| Kind | Examples | Where resolved |
| ---- | -------- | -------------- |
| **Version-controlled application definition** | universe definition, schema/migrations, stage definitions, derivation rules, supported provider maps | Repo / portable definition files; loaded by domain + Universe service |
| **Machine / private configuration** | `DATABASE_URL`, API keys, Explorer/rebuild URLs, local paths, future GitHub credentials | `config.py` / settings objects; resolved at process edges and passed inward |

Architectural rule: UI features and most façade methods should receive **Settings** (or narrow config objects), not scatter `os.getenv` calls. Keep evolving existing `config.py` rather than redesigning configuration wholesale.

---

## 10. Fresh Build / Update / Exact Rebuild / Backup-Restore

### Fresh Build

Conceptually:

```text
Empty PostgreSQL → migrations → source acquisition → domain stages
  → validation → health → fingerprint → usable StockBallDB
```

Much of this **already exists** as `run_build_v1` + `BUILD_STAGES`.

| Reuse directly | Adapter needs | Watch-outs for user-facing Fresh Build |
| -------------- | ------------- | -------------------------------------- |
| Stage DAG, domain sync, snapshot capture, validate/health/fingerprint/manifest | Progress/result shaping; preflight messaging; optional pytest default off for UI; setup/config gating | Assumes credentials + network; not Exact Rebuild; provider revisions mean Fresh Build ≠ historical bit-identity |

Fresh Build must not replace or weaken Exact Rebuild.

### Update convergence

Desired property:

```text
Fresh Build to target date X ≈ Existing DB + Update to target date X
```

(same StockBallDB version, universe definition, source configuration, available source data)

**Canonical equality (conceptual):** equality of canonical table contents as measured by existing **database fingerprint** / table fingerprints — not PostgreSQL cluster bytes, not identical run IDs/timestamps/manifest filenames.

**May legitimately differ:** run reports, manifest build IDs, timestamps, snapshot capture identities when live-fetched at different times if providers changed, operational metadata.

Automated convergence testing would be useful later; not implemented in this step.

### Exact Rebuild

Remains the offline, snapshot/manifest-driven reproduction path (`run_rebuild_exact`). Architecturally isolated under Maintenance; semantics unchanged. Fresh Build and Backup/Restore must not subsume it.

### Backup / Restore

| Item | Stance |
| ---- | ------ |
| Layer | Maintenance façade + future infrastructure helper |
| Distinct from | Fresh Build, Update, Exact Rebuild |
| Format | **Not decided** |
| Constraint | PostgreSQL remains canonical; backup restores a usable local DB |

---

## 11. UI and transport relationship

* **Business boundary** = in-process Python `stockballdb.app` façade (unchanged).
* **Forward-facing UI** = React (locked for V2 and intended for V3/StockBallAPP).
* **V1 Streamlit Explorer** remains available; do not delete or rewrite it merely for V2.
* **Transport** = thin **localhost-only HTTP JSON API** that calls the façade. Handlers must not contain domain logic.
* Packaging (Electron vs Tauri vs other) remains open; any shell should start/stop the local Python process and host or load the React UI.

```text
React  →  Application Client (TS)  →  localhost HTTP  →  transport adapters  →  stockballdb.app  →  V1 core
```

---

## 12. Proposed package / module structure

Minimal evolutionary layout (proposed — **do not create yet**):

```text
src/stockballdb/app/                 # NEW — Layer A (use-cases)
  read/
    catalog.py
    explore.py
    day.py
    status.py
  maintenance/
    build.py
    update.py
    rebuild.py
    backup.py
  universe/
    service.py
  connections.py
  results.py                         # structured results / error types (transport-agnostic)

src/stockballdb/transport/           # NEW — thin local HTTP adapters (not business logic)
  http/                              # localhost ASGI app wrapping app.* 
    ...                              # framework choice open (FastAPI likely)

frontend/                            # NEW — React app root name open
  src/
    features/                        # pages/workflows
    components/                      # shared UI
    client/                          # application client → HTTP
    app/                             # shell / routing
```

| Item | Classification |
| ---- | -------------- |
| `models/*`, domain pipelines, providers, `v1/stages`, `validate_v1`, `health`, `fingerprint`, `snapshots`, `rebuild_exact`, `update/orchestrator` | **Keep unchanged** (extend only when required) |
| `explorer/queries`, `registry`, `explorer/db`, `explorer/services/*` | **Wrap/adapt** as read foundation |
| `market_data/universe.py` | **Wrap/adapt** → portable definition later |
| `explorer/views`, `explorer/ui`, `explorer/app` | **Keep** as V1 Streamlit Explorer |
| `stockballdb/app/*` | **New V2 capability** (façade) |
| `stockballdb/transport/*` | **New V2 capability** (thin local HTTP) |
| React `frontend/` | **New V2 capability** |
| Portable universe file + GitHub transport | **New V2 capability** (format/transport open) |
| Backup/Restore implementation | **New V2 capability** (format open) |
| Moving domain code / renaming V1 | **Possible later refactor** |

---

## 13. Dependency direction

Desired:

```text
React (presentation)
  → frontend client (Tier 3)
    → localhost HTTP transport
      → stockballdb.app (Layer A)
        → domain/data (Layer B)
          → infrastructure (Layer C)
```

Rules:

* Infrastructure never imports UI, React, or transport.
* Domain/data packages should not import Streamlit, React, transport, or `app`.
* `app` must not import React or HTTP framework types (keep façade transport-agnostic).
* Transport may import `app` and map HTTP ↔ result DTOs.
* React imports only the frontend client — never Python modules, SQL, or env files directly.
* Avoid unnecessary abstraction for a personal local app.

---

## 14. Architecture diagrams

### A. V2 Read path

```text
User
  → React feature (Explorer / Day / Status / …)
    → frontend application client
      → localhost HTTP (read routes)
        → stockballdb.app.read (Catalog / Explore / Day / Status)
          → explorer services + queries + registry
            → read-only PostgreSQL
          → validate_v1 / health / fingerprint / artifacts (Status)
```

### B. V2 Update path

```text
User
  → React Maintenance feature
    → frontend client
      → localhost HTTP (maintenance start / status)
        → app.maintenance.update
          → optional app.universe check/sync (definition only)
          → update.orchestrator.run_update
            → providers / snapshots / domain pipelines
              → PostgreSQL (write)
            → validate / health / fingerprint / manifest
```

### C. V2 Fresh Build path

```text
Fresh installation
  → configure settings + universe definition
    → React (or first-run flow) → HTTP → app.maintenance.build
      → build_v1 / BUILD_STAGES → PostgreSQL
      → validate / health / fingerprint / manifest
```

### D. Exact Rebuild path (preserved)

```text
User → React → HTTP → app.maintenance.rebuild → rebuild_exact.run_rebuild_exact
  → verify snapshots → offline replay → fingerprint match
```

### E. Backup / Restore path (boundary only)

```text
User → React → HTTP → app.maintenance.backup|restore → (future) backup helper → local PostgreSQL [format TBD]
```

### F. Process model (local)

```text
[Desktop shell — packaging TBD]
   ├── React UI (static build or dev server)
   └── Python local service (transport + app + V1)
          └── PostgreSQL (local)
```

---

## 15. Evaluation against V2 requirements

| Requirement | Satisfied? |
| ----------- | ---------- |
| Evolution not rewrite | Yes — façade + thin transport + React |
| PostgreSQL retained | Yes |
| Local-first / personal desktop | Yes — localhost-only; no SaaS |
| Portability / reconstructability | Yes — Maintenance operations preserved |
| GitHub-distributed universe | Yes at architecture level; format open |
| Fresh Build / Update / Backup / Exact Rebuild | Yes via Maintenance façade + HTTP |
| Read-only exploration safety | Yes — read routes → read façade only |
| Multi-symbol Explorer / Day Inspector | Yes — Explore/Day contracts + React features |
| Maintenance UI | Yes |
| UI independence of core | Yes — React ↔ HTTP ↔ app |
| V3 React longevity | Yes — same boundary; expand façade later |
| Modularity | Yes |

**Still later work:** implement façade/transport/React; universe format; backup format; packaging; progress channel details.

---

## 16. Architecture decisions vs open items

See [StockBallDB_V2_decisions.md](StockBallDB_V2_decisions.md).

**Locked (structural):** façade; layers; read vs maintenance; explorer query foundation; maintenance adapters; narrow universe service; **React as V2/V3 UI**; **localhost HTTP JSON transport over app**; frontend tier direction; Streamlit retained as V1.

**Open:** Electron vs Tauri; exact ASGI framework (FastAPI likely); endpoint names/schemas; DTO field lists; React Query/Zustand/etc.; data-grid library; styling; packaging/install; SSE vs poll for progress; cancellation; performance protocols (Arrow/etc.).

---

## 17. React ↔ Python communication

### 17.1 Recommendation

**Localhost-only HTTP JSON API** as a thin transport over `stockballdb.app`.

| Concern | Choice |
| ------- | ------ |
| Protocol | HTTP/1.1 (+ optional SSE later for progress) |
| Payload | JSON |
| Bind | `127.0.0.1` only by default |
| Auth | None required for V2 personal local use (OS user boundary); do not expose beyond localhost |
| Business logic | Only in `stockballdb.app` |
| Transport role | Map HTTP ↔ façade calls; validate request shapes; return structured errors |

Likely Python implementation: lightweight ASGI stack such as **FastAPI** — preferred but **not locked** as the only allowed framework.

### 17.2 Alternatives evaluated

| Approach | Verdict | Why |
| -------- | ------- | --- |
| **Localhost HTTP JSON over `app`** | **Accepted** | Fits React; structured contracts; testable; Windows-friendly; works with any desktop shell; supports V3 expansion; keeps façade clean |
| Desktop-shell IPC only (Electron/Tauri IPC as primary protocol) | Rejected as primary | Couples app protocol to packaging choice not yet locked; weaker independent frontend/backend dev; still need structured contracts |
| Subprocess stdin/stdout JSON lines | Rejected as primary | Poor fit for concurrent Explorer reads, connection lifecycle, and long maintenance progress |
| WebSocket for all traffic | Rejected as primary | Unnecessary for request/response reads; may supplement progress later |
| gRPC / binary RPC | Rejected | Overengineered for personal local JSON-shaped Explorer |
| In-browser Python (Pyodide) | Rejected | Cannot own local PostgreSQL/providers/snapshots |
| Public/cloud HTTP API | Rejected | Violates local-first; not a V2 requirement |

### 17.3 Local process / runtime model

* Python process hosts transport + `app` + V1 libraries.
* React is a separate UI process (dev server in development; bundled web UI in packaging).
* Desktop shell (TBD) typically **starts the Python local service as a child process** and opens the UI against `http://127.0.0.1:<port>`.
* Separately installed system Python is acceptable in early development; bundling is a packaging decision.
* PostgreSQL remains a local database service as today.

### 17.4 Read-operation flow

```text
React Explore/Day/Status
  → GET/POST localhost read routes (explicit operation contracts)
    → transport → app.read.*
      → read-only DB / filesystem inspection
    ← JSON page/result DTOs
```

Supports (architecturally): list instruments/fields; browse/filter/sort/paginate; multi-symbol queries; shared date ranges; day inspect; coverage; provenance; health/validate/fingerprint viewing.

Exact routes/schemas: **open**.

### 17.5 Maintenance-operation flow

```text
React Maintenance
  → POST start operation (update | fresh build | rebuild | backup | restore | universe sync)
    → transport → app.maintenance.* / app.universe.*
      → existing orchestrators (advisory lock preserved where already present)
  → GET operation status (and optional SSE progress stream later)
    ← structured progress / warnings / completion / failure
```

Architectural expectations:

* Start returns an operation identity (or equivalent status handle).
* Conflicting maintenance operations rely on existing locks + façade refusal — not unrestricted parallel mutators.
* Progress reporting is desirable; **mechanism open** (poll first is acceptable; SSE later).
* Cancellation only if underlying V1 path can be made safe — **not required** initially.
* No arbitrary command execution or raw SQL from React.

### 17.6 Data contracts

* `stockballdb.app.results` (and related façade return types) are the **transport-agnostic** source of truth.
* Transport may expose thin JSON DTOs that serialize those results (1:1 where practical).
* Do not make `app` import HTTP request models or React types.
* Prefer explicit JSON-compatible types: ISO dates, nulls, enums as strings, nested objects/arrays.
* Frontend TypeScript types should mirror contracts — generation optional later, not required to start.

### 17.7 Large / tabular data

* **Start with paginated JSON** for Explorer workloads (multi-symbol, selected columns, filters, sort).
* Reconsider binary/columnar protocols (Arrow/etc.) only if measured payload size or parse cost becomes a real bottleneck.
* Do not introduce Parquet/Arrow in V2 architecture by default.

### 17.8 Error boundary

Transport returns **structured application errors**, not raw Python tracebacks, to React.

Useful categories (conceptual):

| Category | Examples |
| -------- | -------- |
| validation / bad request | invalid filters, unknown symbol, bad date range |
| dependency unavailable | database down, missing credentials when required |
| provider failure | Tiingo/FRED errors during maintenance |
| maintenance conflict | update lock held |
| operation failure | stage/validate/health failure |
| health warnings | non-fatal findings (may appear in Status results, not only errors) |
| internal | unexpected faults (log locally; generic message to UI) |

Detailed logs remain on the local machine for diagnostics.

### 17.9 Development workflow (pre-packaging)

```text
local PostgreSQL
  + Python local service (transport + app) on 127.0.0.1
  + React dev server
```

Frontend development does not wait for Electron/Tauri packaging.

### 17.10 Desktop packaging relationship

Electron or Tauri (or similar) can:

1. spawn/monitor the Python local service;
2. serve or load the React build;
3. keep traffic on localhost.

**Electron vs Tauri remains open** — the HTTP boundary deliberately avoids forcing that choice.

---

## 18. React frontend architecture

### 18.1 Intent

V2 React is the start of the long-term StockBallAPP UI, not disposable prototype chrome. Keep V2 feature scope inside StockBallDB boundaries; keep structure extensible for V3 research features later.

### 18.2 Feature-based layout (conceptual)

```text
features/
  dashboard/          # overview / control-style status
  explorer/           # multi-instrument explore/compare
  day-inspector/      # date drilldown
  maintenance/        # build/update/rebuild/backup
  universe/           # definition status/sync
  status/             # validation/health/provenance
components/           # shared: instrument selector, field selector, grid, dates, progress
client/               # Tier 3 — talks to localhost API
app/                  # shell, routing
```

Shared building blocks (conceptual): instrument/ticker selector (+ add/reorder), field selector, data grid, date controls, status/progress UI. **Styling undecided.**

### 18.3 Three-tier UI philosophy

| Tier | Responsibility |
| ---- | -------------- |
| **1 — Pages / features** | Workflow composition (Explorer page, Maintenance page, …) |
| **2 — Reusable components** | Selectors, grids, dialogs, progress panels |
| **3 — Application client / state boundary** | HTTP calls, query/mutation lifecycle, mapping DTOs → UI state |

Do not put fetch/HTTP details inside presentational grid cells. Do not put PostgreSQL knowledge in Tier 1.

### 18.4 State management (conceptual)

| State kind | Where it should live |
| ---------- | -------------------- |
| Backend/server data (query results, health, manifests) | Fetched via client; cache library optional later |
| Explorer configuration (symbols, fields, dates, sort, filters, column order) | Feature-level state (URL and/or feature store) |
| Selected day / navigation | Feature/router state |
| Maintenance operation status | Client + maintenance feature state |
| Ephemeral UI (open dialog, hover) | Local component state |

**Architecture decision:** separate server state from Explorer configuration from local UI state.  
**Library choice** (TanStack Query, Zustand, Context-only, etc.): **can wait** — likely implementation choice, not locked.

### 18.5 Explorer longevity

Communication + Explore façade must support:

* repeatable instrument groups;
* add instruments without a hard three-symbol cap;
* per-instrument field selection;
* shared date context;
* ordering of instruments/columns;
* filtering, sorting, pagination;
* navigation into Day Inspector.

UI details remain open; backend/client contracts must not assume a fixed three-column compare toy.

### 18.6 V3 / StockBallAPP compatibility

The same pattern scales:

```text
React feature → client → localhost HTTP → expanded app.* use-cases → core
```

Future research/experiment endpoints would be **new façade operations** (and routes), not a new frontend/backend architecture. V2 must not implement those operations.
