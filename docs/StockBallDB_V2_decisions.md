# StockBallDB — V2 Decisions

**Purpose:** Decision log for StockBallDB V2 planning and implementation.  
**Companion docs:** [index](StockBallDB_index.md) · [V2 scope](StockBallDB_V2_scope.md) · [V2 architecture](StockBallDB_V2_architecture.md) · [V2 progress](StockBallDB_V2_progress.md) · [future / deferred](StockBallDB_future.md)

Record:

* what was decided;
* why;
* alternatives considered where relevant;
* consequences;
* whether the decision is **Proposed** or **Locked**.

Do not add undecided architecture or technology choices (for example UI framework or desktop packaging) until they are actually made.

---

## Decision entry template

```markdown
### Decision: <short title>

| Field | Value |
| ----- | ----- |
| Status | Proposed \| Locked |
| Date | YYYY-MM-DD |
| Owner doc | link if applicable |

**Decision:** One-paragraph statement of what was decided.

**Why:** Short rationale.

**Alternatives considered:** Optional. List only when useful.

**Consequences:** What this commits the project to, and what it excludes.
```

---

## Locked decisions

### Decision: V2 is an evolution of V1

| Field | Value |
| ----- | ----- |
| Status | Locked |
| Date | 2026-09-17 |
| Owner doc | [StockBallDB_V2_scope.md](StockBallDB_V2_scope.md) |

**Decision:** StockBallDB V2 extends the certified V1 foundation. It does not rebuild StockBallDB from scratch.

**Why:** V1 is complete and certified. The database foundation, pipelines, validation, health checks, fingerprints, snapshots, exact rebuild, update orchestration, provenance, schema, and tests are already trustworthy. Rewriting them would discard proven work without necessity.

**Alternatives considered:**

* Full rewrite of storage / pipelines / schema — rejected for V2.
* Treat V2 as an unrelated greenfield application — rejected; V2 builds on V1.

**Consequences:** Preserve existing PostgreSQL, schema, Python acquisition/normalization/derivation, SQLAlchemy, Alembic, validation, health, fingerprints, provenance, snapshots, exact rebuild, update orchestration, and tests where practical. The primary V2 work is the application/UI layer and clean interfaces to existing capabilities. Material foundation changes require an explicit later decision.

---

### Decision: V2 scope boundary

| Field | Value |
| ----- | ----- |
| Status | Locked |
| Date | 2026-09-17 |
| Owner doc | [StockBallDB_V2_scope.md](StockBallDB_V2_scope.md) |

**Decision:** V2 is limited to helping the user view, filter, explore, inspect, understand, validate, maintain, update, and reproduce what StockBallDB already contains. Research, experiment, prediction, backtesting, strategy, portfolio, and trading functionality are outside V2.

**Why:** StockBallDB’s responsibility is a trustworthy historical foundation. Mixing inspection/management with predictive discovery would blur the certified V1 boundary and invite experiment logic into the database product.

**Alternatives considered:**

* Include lightweight “what happens next” analytics in V2 — rejected; that is research/experiment work.
* Keep V2 strictly read-only forever — rejected as a permanent rule; V2 may surface existing update/snapshot/rebuild maintenance paths, subject to safe UX later.

**Consequences:** Filtering and inspecting canonical fields (including retrospective `market_outcomes` labels) is allowed. Turning those fields into outcome studies, signal tools, or strategy engines is not. Deferred ideas belong in [StockBallDB_future.md](StockBallDB_future.md).

---

### Decision: Documentation model

| Field | Value |
| ----- | ----- |
| Status | Locked |
| Date | 2026-09-17 |
| Owner doc | [StockBallDB_index.md](StockBallDB_index.md) |

**Decision:** StockBallDB uses a **Canonical + historical + V2 working** documentation model.

| Layer | Role |
| ----- | ---- |
| Canonical documents | Describe the current StockBallDB system as it exists. Change only when the system they describe changes. |
| Historical / version documents | Preserve certified baselines (e.g. [StockBallDB_V1_status.md](StockBallDB_V1_status.md)). Do not rewrite history. A future `StockBallDB_V2_status.md` is created only when V2 reaches certification. |
| V2 working / governance documents | Capture scope, decisions, progress, and deferred ideas during V2 development. |

**Why:** Rewriting canonical docs into “V2 docs” would mix current-system truth with planning intent. Separating certified history from working V2 material keeps authorities clear for developers and AI sessions.

**Alternatives considered:**

* Replace canonical docs with V2-branded equivalents now — rejected.
* Keep all V2 planning only in chat / informal notes — rejected; durable working docs are required.

**Consequences:** V2 planning lives in `StockBallDB_V2_scope.md`, this decision log, `StockBallDB_V2_progress.md`, and `StockBallDB_future.md`. Canonical docs remain authoritative for V1/current-system facts until the implemented system changes.

---

## Locked architecture decisions

Foundation, portability, and universe-distribution decisions for V2. These do **not** lock UI framework, desktop packaging, backend service shape, universe file format, GitHub sync mechanism, backup format, or Fresh Build implementation details.

### Decision: PostgreSQL remains the canonical database

| Field | Value |
| ----- | ----- |
| Status | Locked |
| Date | 2026-09-20 |
| Owner doc | this file; current stack: [StockBallDB_Tech_stack.md](StockBallDB_Tech_stack.md) |

**Decision:** StockBallDB V2 continues using PostgreSQL as the canonical database. V2 will not migrate the canonical database to SQLite, DuckDB, or another engine solely for portability.

**Why:** V1 is certified on PostgreSQL. The schema, migrations, constraints, pipelines, validation, fingerprints, and exact-rebuild semantics assume PostgreSQL. Changing engines for packaging convenience would discard certified foundation work.

**Alternatives considered:**

* SQLite or DuckDB as the canonical store for “single-file portability” — rejected for V2.
* Dual-write / dual-engine canonical stores — rejected; one canonical database architecture.

**Consequences:** Portability must be achieved without abandoning PostgreSQL (see portability decision). Existing PostgreSQL-centered V1 capabilities remain the foundation.

---

### Decision: V2 is local-first

| Field | Value |
| ----- | ----- |
| Status | Locked |
| Date | 2026-09-20 |
| Owner doc | this file; aligns with [StockBallDB_V2_scope.md](StockBallDB_V2_scope.md) |

**Decision:** StockBallDB V2 is primarily a personal desktop / local application. The operational StockBallDB database remains local.

**Why:** V2’s purpose is coherent local inspection and maintenance of the historical database. SaaS, cloud-hosted operational databases, real-time multi-device sync, and multi-user production infrastructure are out of scope for V2 requirements.

**Alternatives considered:**

* Cloud-hosted operational PostgreSQL / Supabase as a V2 requirement — deferred; not required for V2.
* Real-time multi-device database synchronization — deferred.

**Consequences:** Design for local operation first. Cloud hosting may be reconsidered in a later version if requirements change; park such ideas in [StockBallDB_future.md](StockBallDB_future.md) rather than stretching V2.

---

### Decision: Portability means reconstructability and transferability

| Field | Value |
| ----- | ----- |
| Status | Locked |
| Date | 2026-09-20 |
| Owner doc | this file |

**Decision:** V2 does **not** require the live PostgreSQL database to exist as a single portable file. Portability should eventually be supported through complementary mechanisms: **Fresh Build**, **Normal Update**, **Backup / Restore**, and preserved **Exact Rebuild**.

**Why:** A single-file database goal would pressure engine migration and weaken certified PostgreSQL semantics. Reconstructability and transferability preserve V1 strengths while enabling multi-machine use.

#### Fresh Build

A new installation should eventually be able to construct a complete usable database from an empty PostgreSQL database using the StockBallDB application/code, canonical universe definition, configured authoritative sources, required API credentials, schema/migrations, existing derivation logic, and validation:

```text
Fresh installation → configure → Build Database → fetch sources → derive → validate → usable StockBallDB
```

A fresh build is **not** necessarily an exact historical reproduction, because external providers may revise or correct historical source data.

#### Normal Update

Existing installations continue to use established StockBallDB update mechanisms. A desired architectural property is:

```text
Fresh Build to target date X ≈ Existing Database + Update to target date X
```

when both installations use the same StockBallDB version, universe definition, source configuration, and available source data. Operational metadata (timestamps, run IDs) need not be identical. No required percentage match is defined at this stage.

#### Backup / Restore

V2 should eventually provide a convenient way to back up the current local PostgreSQL StockBallDB and restore it on another computer. This is distinct from Fresh Build and Exact Rebuild. **Backup format and implementation are not decided in this step.**

#### Exact Rebuild

Preserve the existing V1 snapshot / manifest / exact-rebuild architecture. Exact historical reproducibility remains the stronger mechanism when StockBallDB must reproduce preserved historical source inputs rather than refetching current provider versions. **Fresh Build must not replace or weaken Exact Rebuild.**

**Alternatives considered:**

* Single-file portable live database — rejected as a V2 requirement.
* Replace Exact Rebuild with Fresh Build alone — rejected.

**Consequences:** Later V2 work may implement Fresh Build UX, backup/restore convenience, and setup/portability workflows without changing the certified Exact Rebuild contract. Implementation details remain open.

---

### Decision: Preserve StockBallDB point-in-time principles

| Field | Value |
| ----- | ----- |
| Status | Locked |
| Date | 2026-09-20 |
| Owner doc | this file; principles: [StockBallDB_manifesto.md](StockBallDB_manifesto.md) |

**Decision:** Point-in-time refers to the **historical date being represented or inspected**, not merely the calendar date on which a particular database installation was built. Where StockBallDB has PIT safeguards, a Fresh Build must continue to respect those rules.

**Why:** PIT discipline is core to certified V1 historical integrity. A portable rebuild that silently substitutes today’s revised history would undermine StockBallDB’s purpose.

**Alternatives considered:**

* Redesign PIT handling as part of V2 architecture lock — rejected; out of scope for this step.

**Consequences:** Fresh Build / Update / portability work must preserve existing PIT behavior. No PIT redesign is authorized by this decision.

---

### Decision: Universe definition is portable and version-controlled

| Field | Value |
| ----- | ----- |
| Status | Locked |
| Date | 2026-09-20 |
| Owner doc | this file; current V1 universe authority: [StockBallDB_universe.md](StockBallDB_universe.md) |

**Decision:** V2 separates **StockBallDB definition** (what StockBallDB is supposed to contain) from **local database state** (what a particular installation has currently built). The StockBallDB universe must not depend solely on the contents of one local PostgreSQL database. The working V2 direction is a small canonical, version-controlled universe definition that installations can obtain independently.

**Why:** Multi-machine reconstructability requires a shared intended universe. Basing “what should exist” only on one local DB prevents separate installations from converging deliberately.

**Alternatives considered:**

* Treat local DB contents as the sole universe authority — rejected for V2 portability goals.

**Consequences:** Later work may introduce or refine a machine-usable universe definition. **Exact file format is not decided yet** and requires inspection of the existing V1 universe implementation first. [StockBallDB_universe.md](StockBallDB_universe.md) remains the current human-readable V1 universe authority until an implemented format change is recorded.

---

### Decision: GitHub is the planned shared source of truth for the universe

| Field | Value |
| ----- | ----- |
| Status | Locked |
| Date | 2026-09-20 |
| Owner doc | this file |

**Decision:** GitHub is the current V2 choice for distributing and versioning the canonical StockBallDB universe definition. GitHub will **not** host the operational PostgreSQL database.

**Conceptual flow:**

```text
GitHub universe definition → local StockBallDB installation → source fetching / build / update → local PostgreSQL
```

**Example:** Computer A adds NVDA and MSFT to the canonical universe; the change is version-controlled/shared through GitHub; Computer B obtains the updated definition; its build/update process detects those securities as required and builds the necessary local data.

**Why:** The project already uses GitHub as the remote repository. Reusing it for universe definition distribution avoids inventing a separate distribution service while keeping the operational database local.

**Alternatives considered:**

* Host operational database on GitHub or similar — rejected.
* Separate proprietary universe-distribution service in V2 — not chosen; GitHub is the planned path.

**Consequences:** Universe file format, GitHub API mechanism, authentication, and synchronization implementation are **deliberately not decided yet**. Those require prior inspection of the existing V1 universe implementation.

---

### Decision: Universe synchronization and database updating are conceptually separate

| Field | Value |
| ----- | ----- |
| Status | Locked |
| Date | 2026-09-20 |
| Owner doc | this file |

**Decision:** Preserve the architectural distinction between:

* **What should StockBallDB contain?** (universe definition / Update Universe)
* **Is my local database current for that definition?** (database build/update / Update Database)

V2 may eventually expose both kinds of operations. The normal Update Database workflow **may** automatically check or synchronize the canonical universe first. **No UI decision is locked here.**

**Why:** Collapsing definition sync into opaque database mutation makes multi-installation behavior harder to reason about and debug.

**Alternatives considered:**

* Only a single undifferentiated “Update” with no conceptual separation — rejected as the architectural model (UI may still combine steps later).

**Consequences:** Implementation and UX may combine the steps for convenience, but documentation and architecture must keep the two concerns distinguishable.

---

### Decision: Preserve V1 rather than rewrite it

| Field | Value |
| ----- | ----- |
| Status | Locked |
| Date | 2026-09-20 |
| Owner doc | this file; reinforces [V2 is an evolution of V1](#decision-v2-is-an-evolution-of-v1) |

**Decision:** All V2 architecture work continues from the certified V1 foundation. Existing working V1 capabilities—including pipelines, validation, health checks, snapshots, exact rebuild, schema/migrations, database logic, tests, and Explorer capabilities—should be reused or extended wherever practical. V2 must not become a from-scratch rewrite merely for architectural neatness.

**Why:** Reinforces the earlier evolution decision specifically for architecture and portability work now being planned.

**Alternatives considered:**

* Greenfield rewrite of pipelines/schema to “simplify” portability — rejected.

**Consequences:** New V2 surfaces should call into or extend existing StockBallDB capabilities. Material replacement of certified subsystems requires an explicit later decision.

---

## Locked application / backend architecture decisions

Detailed rationale and diagrams: [StockBallDB_V2_architecture.md](StockBallDB_V2_architecture.md).

### Decision: Thin in-process application façade

| Field | Value |
| ----- | ----- |
| Status | Locked |
| Date | 2026-09-20 |
| Owner doc | [StockBallDB_V2_architecture.md](StockBallDB_V2_architecture.md) |

**Decision:** V2 introduces a thin in-process Python application façade (`stockballdb.app` as the planned package) between any UI and existing StockBallDB capabilities. The UI requests use-cases; it does not own PostgreSQL schema, provider clients, stage DAGs, snapshot internals, or env-var layout. The façade itself remains in-process and transport-agnostic.

**Why:** V1 already exposes callable domain APIs and Streamlit-independent explorer services. A façade gives UI independence and maintenance safety without rewriting certified pipelines.

**Alternatives considered:**

* UI calls V1 modules directly forever — rejected; couples presentation to internals and weakens read/mutate boundaries.
* Rewrite domain into a new service framework — rejected; violates evolution rule.

**Consequences:** Implement façade modules later; keep V1 packages in place. When the UI is out-of-process (React), a thin transport may sit **above** the façade — see locked React/HTTP decisions. Earlier wording that deferred HTTP applied while UI technology was still open.

---

### Decision: Layer A / B / C responsibility model

| Field | Value |
| ----- | ----- |
| Status | Locked |
| Date | 2026-09-20 |
| Owner doc | [StockBallDB_V2_architecture.md](StockBallDB_V2_architecture.md) |

**Decision:** V2 uses a modular three-responsibility model: **A** application/use-case façade; **B** existing StockBallDB domain/data services; **C** infrastructure/persistence. Layer B is the certified V1 capability surface, not a greenfield rewrite. Finer V1 packages remain inside B/C.

**Why:** Matches the desired modular philosophy without forcing artificial relocation of working V1 code.

**Consequences:** New V2 code primarily adds Layer A and selective B extensions; mass package renames are out of scope.

---

### Decision: Read vs maintenance safety boundary

| Field | Value |
| ----- | ----- |
| Status | Locked |
| Date | 2026-09-20 |
| Owner doc | [StockBallDB_V2_architecture.md](StockBallDB_V2_architecture.md) |

**Decision:** Ordinary exploration (browse/filter/inspect/status viewing) uses read-only database access only. Mutating operations (Fresh Build, Update, Exact Rebuild, Backup/Restore, and universe **definition** sync) go only through explicit maintenance/universe façade entry points with the write/maintenance engine as appropriate. Health/validate/fingerprint remain read-safe inspection operations.

**Why:** Preserves V1 Explorer’s read-only safety model while allowing deliberate maintenance in V2.

**Consequences:** Fix dual write-engine usage for pure inspection as architecture is implemented; no multi-user auth system required for this personal local app.

---

### Decision: Reuse Explorer query stack as V2 read foundation

| Field | Value |
| ----- | ----- |
| Status | Locked |
| Date | 2026-09-20 |
| Owner doc | [StockBallDB_V2_architecture.md](StockBallDB_V2_architecture.md) |

**Decision:** V2 read/query builds on existing `explorer/queries.py`, `explorer/registry.py`, `explorer/db.py`, and Streamlit-independent `explorer/services/*`. Future UI should consume Catalog/Explore/Day/Status façade APIs rather than importing registry/universe constants or models directly. Multi-symbol/compare needs may extend allowlisted queries later.

**Why:** Inspection showed these modules are already the real read path and are not Streamlit-bound.

**Consequences:** V1 `explorer/views` remain presentation only; query allowlisting is preserved.

---

### Decision: Maintenance via adapters over existing orchestrators

| Field | Value |
| ----- | ----- |
| Status | Locked |
| Date | 2026-09-20 |
| Owner doc | [StockBallDB_V2_architecture.md](StockBallDB_V2_architecture.md) |

**Decision:** Fresh Build, Update, and Exact Rebuild are exposed to V2 through thin application adapters over `run_build_v1`, `run_update`, and `run_rebuild_exact`. Do not rewrite stage DAGs or domain pipelines for UI friendliness. Adapters should evolve toward structured results suitable for a desktop UI.

**Why:** Those orchestrators are already callable and certified; CLI shaping is an adapter concern.

**Consequences:** Progress/cancellation mechanisms remain open; Exact Rebuild stays semantically isolated; Backup/Restore is a separate new maintenance capability (format open).

---

### Decision: Narrow universe service in the application layer

| Field | Value |
| ----- | ----- |
| Status | Locked |
| Date | 2026-09-20 |
| Owner doc | [StockBallDB_V2_architecture.md](StockBallDB_V2_architecture.md) |

**Decision:** V2 includes a Universe application service responsible for loading/validating/exposing the portable instrument definition, comparing/synchronizing definition (not DB rows), and reporting definition-vs-DB gaps. “Universe” remains **narrowly about market instruments**, including non-ETF kinds (e.g. WTI). Macro/event definition maps stay separate unless a later decision widens “StockBallDB definition.”

**Why:** Aligns with locked portable-universe + GitHub SoT decisions and with V1’s real instrument diversity.

**Consequences:** File format and GitHub transport remain open; `market_data/universe.py` is wrapped/adapted until replaced by a portable definition source.

---

### Decision: Façade service module boundaries

| Field | Value |
| ----- | ----- |
| Status | Locked |
| Date | 2026-09-20 |
| Owner doc | [StockBallDB_V2_architecture.md](StockBallDB_V2_architecture.md) |

**Decision:** The application façade is split into Catalog, Explore, Day, Status, Universe, and Maintenance (build/update/rebuild/backup) rather than a single mega-service. Planned package root: `src/stockballdb/app/` (not created yet).

**Why:** Matches distinct use-cases and keeps read vs mutate separable.

**Consequences:** Implementation may adjust file names slightly, but the responsibility split is locked.

---

## Locked frontend / communication architecture decisions

Detailed rationale: [StockBallDB_V2_architecture.md](StockBallDB_V2_architecture.md) §§17–18.

### Decision: React is the V2 forward-facing UI

| Field | Value |
| ----- | ----- |
| Status | Locked |
| Date | 2026-09-20 |
| Owner doc | [StockBallDB_V2_architecture.md](StockBallDB_V2_architecture.md) |

**Decision:** StockBallDB V2 uses React for its new application UI. The certified V1 Streamlit Explorer remains available as a legacy/reference/diagnostic interface and must not be removed or rewritten merely because V2 adopts React.

**Why:** React supports the richer Explorer/maintenance UX planned for V2 and provides a durable path into V3/StockBallAPP without treating the V2 UI as disposable.

**Alternatives considered:**

* Continue Streamlit as the only V2 UI — rejected as the forward-facing direction.
* Replace/delete Streamlit immediately — rejected; V1 Explorer remains certified.

**Consequences:** New V2 UI work targets React. Streamlit stays in the V1 tree until an explicit later retirement decision.

---

### Decision: V2 React architecture continues into V3 / StockBallAPP

| Field | Value |
| ----- | ----- |
| Status | Locked |
| Date | 2026-09-20 |
| Owner doc | [StockBallDB_V2_architecture.md](StockBallDB_V2_architecture.md) |

**Decision:** The V2 React frontend and its communication boundary are intended to extend into V3/StockBallAPP rather than be replaced. V3 is expected to remain React-based. V2 must not implement research/experiment features, but must not choose a throwaway UI architecture.

**Why:** Establishing the long-lived frontend/backend boundary now avoids a second rewrite when StockBallAPP grows.

**Consequences:** Prefer clean feature/client separation and stable contracts; avoid prototype-only shortcuts that force a V3 redesign.

---

### Decision: React communicates only through the application/transport boundary

| Field | Value |
| ----- | ----- |
| Status | Locked |
| Date | 2026-09-20 |
| Owner doc | [StockBallDB_V2_architecture.md](StockBallDB_V2_architecture.md) |

**Decision:** React must not access PostgreSQL, SQLAlchemy models, V1 pipeline internals, providers, snapshots, environment variables, or orchestrators directly. It communicates via the frontend application client → transport → `stockballdb.app` only.

**Why:** Preserves read/maintenance safety and keeps the certified core independent of UI technology.

**Consequences:** No raw SQL console in React; no shelling out to arbitrary Python from the UI.

---

### Decision: Localhost-only HTTP JSON transport over the façade

| Field | Value |
| ----- | ----- |
| Status | Locked |
| Date | 2026-09-20 |
| Owner doc | [StockBallDB_V2_architecture.md](StockBallDB_V2_architecture.md) |

**Decision:** React ↔ Python communication uses a **localhost-only HTTP JSON API** that thinly wraps `stockballdb.app`. The API binds to `127.0.0.1` by default and is not a public/SaaS service. Domain logic remains in the façade, not in HTTP handlers. Optional SSE (or similar) may later carry maintenance progress; request/response JSON remains the primary read model.

**Why:** React is a separate process/language. Local HTTP gives structured contracts, testability, Windows desktop suitability, packaging flexibility, and V3 longevity without enterprise complexity. Subprocess pipes and packaging-only IPC were rejected as the primary protocol.

**Alternatives considered:** See architecture §17.2.

**Consequences:** Implement a thin `stockballdb.transport` (name flexible) later using **FastAPI** (now locked). Ports, endpoints, and progress channel remain open. No cloud deployment or user-account auth required for V2 local use.

---

### Decision: React frontend tier / dependency direction

| Field | Value |
| ----- | ----- |
| Status | Locked |
| Date | 2026-09-20 |
| Owner doc | [StockBallDB_V2_architecture.md](StockBallDB_V2_architecture.md) |

**Decision:** Organize the React app as feature pages → reusable components → application client (HTTP/state boundary). Dependency direction: presentation depends on the client; the client depends on localhost contracts; nothing in the frontend depends on Python internals.

**Why:** Matches modular UI practice and keeps Explorer/maintenance features extensible for V3.

**Consequences:** Feature-based folders; shared selectors/grids; state libraries remain an open implementation choice.

---

## Locked desktop runtime / packaging decisions

Detailed rationale: [StockBallDB_V2_architecture.md](StockBallDB_V2_architecture.md) §19.

### Decision: Electron is the V2 desktop shell

| Field | Value |
| ----- | ----- |
| Status | Locked |
| Date | 2026-09-20 |
| Owner doc | [StockBallDB_V2_architecture.md](StockBallDB_V2_architecture.md) |

**Decision:** StockBallDB V2 uses **Electron** as the forward-facing desktop shell. It loads the production React build and manages the local Python backend process so the user can launch StockBallDB like a normal desktop application.

**Why:** Best fit for React + spawning/managing a Python localhost service on Windows with mature tooling and acceptable complexity for a personal project. Shell size is secondary to Python/PostgreSQL weight.

**Alternatives considered:**

* **Tauri** — rejected as primary; size wins do not outweigh Rust toolchain cost and weaker Python-orchestration fit for this stack.
* **Browser-only local app as sole production UX** — rejected for target “normal desktop app” launch; retained as development/fallback mode.

**Consequences:** Electron project comes later. Installer/code-signing tools remain open. Dev may run without Electron.

---

### Decision: FastAPI is the localhost HTTP framework

| Field | Value |
| ----- | ----- |
| Status | Locked |
| Date | 2026-09-20 |
| Owner doc | [StockBallDB_V2_architecture.md](StockBallDB_V2_architecture.md) |

**Decision:** The thin localhost transport layer is implemented with **FastAPI** (ASGI server such as uvicorn). Handlers wrap `stockballdb.app` only.

**Why:** JSON/validation/typed contracts, React-friendly, SSE-capable later, low boilerplate, testable, sufficient for V3 longevity without enterprise frameworks.

**Consequences:** Transport implementation targets FastAPI; endpoint schemas still open.

---

### Decision: Electron owns the Python backend child process

| Field | Value |
| ----- | ----- |
| Status | Locked |
| Date | 2026-09-20 |
| Owner doc | [StockBallDB_V2_architecture.md](StockBallDB_V2_architecture.md) |

**Decision:** In production desktop mode, Electron starts the Python FastAPI backend as a child process, waits for readiness, monitors health/crashes, and shuts it down when safe. React talks only to localhost HTTP.

**Why:** Delivers one-click launch without manual terminals while preserving the locked HTTP boundary.

**Consequences:** Readiness handshake and port strategy are implementation details. Development may start Python independently.

---

### Decision: PostgreSQL remains an independent local service

| Field | Value |
| ----- | ----- |
| Status | Locked |
| Date | 2026-09-20 |
| Owner doc | [StockBallDB_V2_architecture.md](StockBallDB_V2_architecture.md) |

**Decision:** V2 does not embed PostgreSQL inside Electron. PostgreSQL remains a separately installed local database. The app detects/connects and guides first-run/Fresh Build/restore; it does not redefine portability as copying live data directories. Application packaging and database installation are distinct.

**Why:** Preserves certified canonical architecture; avoids disproportionate installer complexity in V2.

**Consequences:** First-run must handle missing/unavailable DB clearly; automated PG install inside the app is out of V2 scope unless later reconsidered.

---

### Decision: Maintenance integrity over casual window-close termination

| Field | Value |
| ----- | ----- |
| Status | Locked |
| Date | 2026-09-20 |
| Owner doc | [StockBallDB_V2_architecture.md](StockBallDB_V2_architecture.md) |

**Decision:** Closing the desktop UI must not silently kill an active Update, Fresh Build, Exact Rebuild, Backup, Restore, or universe sync in a way that risks database integrity. Exact UX (block quit vs warn vs allow background completion) remains open; unsafe cancellation is not authorized by this decision.

**Why:** V1 orchestrators are not designed as casually interruptible UI toys.

**Consequences:** Shutdown design must check maintenance state before stopping the Python child.

---

### Decision: Application update ≠ database update

| Field | Value |
| ----- | ----- |
| Status | Locked |
| Date | 2026-09-20 |
| Owner doc | [StockBallDB_V2_architecture.md](StockBallDB_V2_architecture.md) |

**Decision:** Installing a newer StockBallDB application (Electron/React/Python code) is conceptually separate from **Update Database** (data maintenance). Terminology and product actions must not blur them. No auto-update system is locked for V2.

**Why:** Prevents operator confusion and accidental conflation of code deploys with data pipelines.

---

### Decision: V2 desktop runtime continues into V3 / StockBallAPP

| Field | Value |
| ----- | ----- |
| Status | Locked |
| Date | 2026-09-20 |
| Owner doc | [StockBallDB_V2_architecture.md](StockBallDB_V2_architecture.md) |

**Decision:** Electron + FastAPI + `stockballdb.app` + React is the intended runtime architecture to extend into V3/StockBallAPP. V3 should add façade/UI capabilities, not replace the desktop/runtime stack again.

**Why:** Avoid a third architecture rewrite when research features arrive.

**Consequences:** Prefer durable process/lifecycle choices; do not treat Electron as disposable scaffolding.

---

## Locked implementation-roadmap decisions

Detailed plan: [StockBallDB_V2_roadmap.md](StockBallDB_V2_roadmap.md).

### Decision: Early vertical slice before full Explorer

| Field | Value |
| ----- | ----- |
| Status | Locked |
| Date | 2026-09-20 |
| Owner doc | [StockBallDB_V2_roadmap.md](StockBallDB_V2_roadmap.md) |

**Decision:** Before building Explorer V2, deliver a thin end-to-end slice: React → FastAPI → `stockballdb.app` → read-only V1 path → PostgreSQL (readiness + catalog/status at minimum).

**Why:** Proves the new V2 boundary early and reduces integration risk.

**Consequences:** Phases P1–P3 precede deep Explorer UI work.

---

### Decision: Electron after proven React + FastAPI

| Field | Value |
| ----- | ----- |
| Status | Locked |
| Date | 2026-09-20 |
| Owner doc | [StockBallDB_V2_roadmap.md](StockBallDB_V2_roadmap.md) |

**Decision:** Implement and stabilize React + FastAPI + PostgreSQL in development before investing in Electron packaging. Electron wraps a working system (roadmap Phase 13).

**Why:** Avoid debugging every early issue inside the desktop shell.

---

### Decision: Prototype reconciliation before deep Explorer rebuild

| Field | Value |
| ----- | ----- |
| Status | Locked |
| Date | 2026-09-20 |
| Owner doc | [StockBallDB_V2_roadmap.md](StockBallDB_V2_roadmap.md) |

**Decision:** When the Google AI Studio prototype is available in GitHub, run a keep/modify/discard audit before finishing Explorer V2 UI. The prototype is design/interaction reference only; locked StockBallDB architecture remains authoritative.

**Why:** Preserve intended UX without copying generated architecture.

---

### Decision: Multi-symbol Explore façade before full Explorer UI

| Field | Value |
| ----- | ----- |
| Status | Locked |
| Date | 2026-09-20 |
| Owner doc | [StockBallDB_V2_roadmap.md](StockBallDB_V2_roadmap.md) |

**Decision:** Implement allowlisted multi-symbol Explore façade/API contracts (with pagination) before or as a hard prerequisite to full Explorer V2 UI.

**Why:** Prevents UI-driven unbounded queries and keeps allowlisting intact.
