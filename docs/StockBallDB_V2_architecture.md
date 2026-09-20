# StockBallDB — V2 Architecture

**Status:** Working architecture baseline (backend / application layer)  
**Authority:** Detailed V2 application architecture; lockable decisions also recorded in [StockBallDB_V2_decisions.md](StockBallDB_V2_decisions.md)  
**Companion docs:** [index](StockBallDB_index.md) · [V2 scope](StockBallDB_V2_scope.md) · [V2 progress](StockBallDB_V2_progress.md) · [V1 status](StockBallDB_V1_status.md) · [explorer](StockBallDB_explorer.md) · [workflow](StockBallDB_workflow.md)

This document designs the **V2 backend / application architecture** around the certified V1 system. It is not an implementation plan for UI technology, universe file format, GitHub auth, backup format, or packaging.

**No V2 application packages are created yet.** Package paths below are proposed targets.

---

## 1. Design verdict

V2 should introduce a **thin in-process application façade** between any future UI and existing StockBallDB capabilities.

```text
V2 UI (technology undecided)
  → stockballdb.app  (NEW: use-case façade; read vs maintenance)
    → existing V1 domain / explorer / orchestration capabilities
      → PostgreSQL / providers / snapshots / filesystem / (later) GitHub universe transport
```

This matches V1 reality:

* Explorer already has Streamlit-independent `explorer/services`, allowlisted `queries` + `registry`, and dedicated read-only DB access.
* Build/update/rebuild/validate/health/fingerprint already expose callable Python APIs.
* The main gaps for V2 are: a coherent **application boundary**, **read vs mutate safety**, a **portable universe service**, and **maintenance adapters** suitable for a desktop UI — not a rewrite of pipelines or schema.

Do **not** introduce an HTTP API or local server merely because a non-Streamlit UI might be chosen later. Transport is a later decision; the logical boundary is an in-process Python application layer.

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

## 11. UI independence

* Backend boundary = **in-process Python application façade**.
* UI technology (Streamlit / React / Electron / Tauri / etc.) remains **open**.
* Do not add HTTP/RPC now.
* If a future UI needs out-of-process access, add transport **on top of** the same façade — do not fork business logic into the UI.

---

## 12. Proposed package / module structure

Minimal evolutionary layout (proposed — **do not create yet**):

```text
src/stockballdb/app/                 # NEW — Layer A
  read/
    catalog.py                       # symbols/fields/metadata
    explore.py                       # browse/filter/compare
    day.py                           # day inspect
    status.py                        # health/validate/fingerprint/coverage/provenance (read)
  maintenance/
    build.py                         # Fresh Build adapter
    update.py                        # Update adapter
    rebuild.py                       # Exact Rebuild adapter
    backup.py                        # Backup/Restore boundary (later impl)
  universe/
    service.py                       # definition load/compare/sync façade
  connections.py                     # read vs write policy helpers
  results.py                         # shared result/error types
```

| Item | Classification |
| ---- | -------------- |
| `models/*`, domain pipelines, providers, `v1/stages`, `validate_v1`, `health`, `fingerprint`, `snapshots`, `rebuild_exact`, `update/orchestrator` | **Keep unchanged** (extend only when required) |
| `explorer/queries`, `registry`, `explorer/db`, `explorer/services/*` | **Wrap/adapt** as read foundation; extend queries for multi-symbol as needed |
| `market_data/universe.py` | **Wrap/adapt** → eventually fed by portable definition |
| `explorer/views`, `explorer/ui`, `explorer/app` | V1 presentation; **not** the long-term façade (may remain until UI replacement) |
| `stockballdb/app/*` | **New V2 capability** (façade) |
| Portable universe file + GitHub transport | **New V2 capability** (format/transport open) |
| Backup/Restore implementation | **New V2 capability** (format open) |
| Moving domain code into new packages / renaming V1 | **Possible later refactor** — not required to start V2 |

---

## 13. Dependency direction

Desired:

```text
UI → app (Layer A) → domain/data services (Layer B) → infrastructure (Layer C)
```

Rules:

* Infrastructure never imports UI or `app`.
* Domain/data packages should not import Streamlit or `app`.
* `app` may import existing V1 modules.
* Existing V1 is not perfectly layered today (orchestrators talk to infrastructure directly). **Do not mass-refactor** for purity; new code should follow the direction above.
* Avoid unnecessary ports/adapters/interfaces for a personal local app — thin functions/modules are enough.

Useful inversion: UI depends on façade abstractions, not on PostgreSQL or Tiingo. Unnecessary inversion: abstracting every domain function behind interfaces with no second implementation.

---

## 14. Architecture diagrams

### A. V2 Read path

```text
User
  → UI (undecided)
    → app.read (Catalog / Explore / Day / Status)
      → explorer services + queries + registry  (or evolved equivalents)
        → read-only PostgreSQL connection
      → (Status also) validate_v1 / health / fingerprint / artifacts filesystem
```

### B. V2 Update path

```text
User
  → UI
    → app.maintenance.update
      → optional app.universe status/sync check  (definition only)
      → update.orchestrator.run_update  (adapter)
        → v1 UPDATE_STAGES → providers / snapshots / domain pipelines
          → PostgreSQL (write engine)
        → validate_v1 → health → fingerprint → manifest / run report
```

### C. V2 Fresh Build path

```text
Fresh installation
  → configure machine settings + obtain universe definition
    → app.maintenance.build  (Fresh Build adapter)
      → build_v1.run_build_v1 / BUILD_STAGES
        → migrate → acquire → derive → persist
          → PostgreSQL
        → validate / health / fingerprint / manifest
```

### D. Exact Rebuild path (preserved)

```text
User / operator
  → app.maintenance.rebuild
    → rebuild_exact.run_rebuild_exact
      → verify manifest snapshots → offline replay
        → migrate → truncate → BUILD_STAGES from snapshots
          → validate / health / fingerprint match
```

Isolated from Fresh Build and Backup/Restore.

### E. Backup / Restore path (boundary only)

```text
User
  → app.maintenance.backup | restore
    → (future) infrastructure backup helper
      → local PostgreSQL data directory / dump / archive  [format TBD]
```

Distinct from Fresh Build, Update, and Exact Rebuild.

---

## 15. Evaluation against V2 requirements

| Requirement | Satisfied? |
| ----------- | ---------- |
| Evolution not rewrite | Yes — façade + adapters |
| PostgreSQL retained | Yes |
| Local-first / personal desktop | Yes — in-process; no SaaS |
| Portability / reconstructability | Yes — Fresh Build + Update + Backup + Exact Rebuild boundaries |
| GitHub-distributed universe | Yes at architecture level; format/transport open |
| Fresh Build / Update / Backup / Exact Rebuild | Yes as distinct Maintenance operations |
| Read-only exploration safety | Yes — explicit read vs maintenance connection policy |
| Multi-symbol Explorer / Day Inspector | Yes as Explore/Day façade contracts; query extensions later |
| Maintenance UI | Yes — Maintenance façade |
| Future UI independence | Yes — no Streamlit in `app`; no premature HTTP |
| Modularity | Yes — small façade services over existing V1 |

**Not satisfied by architecture alone (needs later work):** portable universe file + sync implementation; Fresh Build UX; Backup format; multi-symbol query extensions; UI/packaging choice.

---

## 16. Architecture decisions vs open items

See [StockBallDB_V2_decisions.md](StockBallDB_V2_decisions.md) for locked entries corresponding to this document.

**Ready to lock (structural):** application façade; Layer A/B/C mapping; read vs maintenance safety; Explore query foundation reuse; Maintenance adapters over existing orchestrators; narrow universe service; in-process boundary (no HTTP required now); package sketch as evolutionary target.

**Remain open:** UI framework; desktop packaging; universe file format; GitHub auth/API; backup format; progress/cancellation mechanism; exact Explore query shapes for multi-symbol compare; whether V1 Streamlit Explorer is extended or replaced; transport if ever out-of-process.
