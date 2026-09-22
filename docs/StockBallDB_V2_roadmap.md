# StockBallDB — V2 Implementation Roadmap

**Status:** Authoritative ordered implementation plan  
**Authority:** How to build V2 sequentially without rewriting certified V1  
**Companion docs:** [architecture](StockBallDB_V2_architecture.md) · [decisions](StockBallDB_V2_decisions.md) · [progress](StockBallDB_V2_progress.md) · [scope](StockBallDB_V2_scope.md) · [index](StockBallDB_index.md)

This is an **implementation sequence**, not another abstract architecture essay. Architecture locks remain in the architecture/decision docs.

**Do not begin a phase until its prerequisites and the prior phase completion gate are met.**  
Focused Cursor implementation prompts should target **one phase (or named sub-phase) at a time**.

---

## 1. Guiding principles

* Evolve V1; wrap and extend; no mass refactor.
* Prove boundaries early with a small end-to-end vertical slice.
* Prefer useful, testable milestones over giant backend- or frontend-only silos.
* Introduce Electron only after React + FastAPI + PostgreSQL work independently.
* Keep Fresh Build, Update, Backup/Restore, and Exact Rebuild conceptually distinct.
* Preserve database integrity for long-running maintenance (no unsafe cancellation assumptions).
* Primary production DB is never a casual mutating test target (`STOCKBALLDB_TEST_DATABASE_URL`).
* V3 research features are out of scope for every phase below.

---

## 2. Critical path

```text
P1 app façade (Catalog/Status)
  → P2 FastAPI read transport
    → P3 React foundation + vertical slice
      → P4 Prototype reconciliation (when prototype is in GitHub)
        → P5 Explore façade (multi-symbol queries)
          → P6 Explorer V2 UI
            → P7 Day Inspector
              → P8 Status/Dashboard + short maintenance ops
                → P9 Update Database (long-running)
                  → P10 Universe portable definition (+ sync)
                    → P11 Fresh Build
                      → P12 Backup / Restore
                        → P13 Electron desktop shell
                          → P14 V2 certification
```

**Critical path (shortest path to a credible V2 product core):**  
P1 → P2 → P3 → P5 → P6 → P7 → P9 → P13 → P14  

P4 should run **before P6 advances far** if the AI Studio prototype is available (do not block P1–P3 on it).  
P8 can overlap late P6/P7.  
P10 should precede P11 where practical.  
P12 can follow P11 (or run after P9 if needed sooner for portability trials — prefer after Fresh Build exists).

---

## 3. Early vertical slice (required)

**Yes — build a thin end-to-end slice before full Explorer.**

Minimum proof:

```text
React → FastAPI → stockballdb.app → read-only V1 path → PostgreSQL
```

Suggested tiny surface:

* backend readiness;
* list instruments (Catalog);
* one Status call (e.g. live health or validate summary);
* optional: one tiny paginated table page.

**Why:** Catches contract, CORS/localhost, error envelope, and connection-policy bugs before Explorer complexity.  
Delivered across **P1–P3**, not as a separate mega-phase.

---

## 4. Façade / FastAPI / React order (summary)

| Layer | First | Then | Later |
| ----- | ----- | ---- | ----- |
| `stockballdb.app` | Catalog + Status + connections/results | Explore + Day | Maintenance + Universe |
| FastAPI | readiness + Catalog + Status + error envelope | Explore/Day routes | Maintenance/Universe routes |
| React | shell + client + tiny Catalog/Status pages | Explorer + Day | Maintenance/Universe/Electron |

Do **not** create empty stubs for every architecture box on day one.

---

## 5. Implementation phases

### Phase 1 — `stockballdb.app` foundation (Catalog + Status)

| Item | Content |
| ---- | ------- |
| **Goal** | Create Layer A package skeleton: connection policy helpers, result/error types, **Catalog** (instruments/fields metadata from existing V1 universe/registry), **Status** wrappers for health/validate/fingerprint (read-safe). |
| **Why now** | All later transport/UI depends on a transport-agnostic façade. |
| **Expected code areas** | New `src/stockballdb/app/` (`connections`, `results`, `read/catalog`, `read/status`); wrap `market_data/universe.py`, `explorer/registry`, `health`, `validate_v1`, `fingerprint`. |
| **Reuse V1** | Universe constants, registry, health/validate/fingerprint APIs, explorer read-only DB patterns. |
| **New V2** | `stockballdb.app` package and façade APIs. |
| **Tests** | Unit/façade tests; use test DB rules; no primary mutation. |
| **Completion gate** | Catalog lists V1 instruments; Status can run health and/or validate_v1 via façade; tests green; Streamlit Explorer still launches; spot V1 CLI health/validate still work. |
| **Non-goals** | FastAPI, React, Explore multi-symbol, mutations, universe file format. |
| **Risk** | **Low** — additive package. |

---

### Phase 2 — FastAPI localhost transport (read slice)

| Item | Content |
| ---- | ------- |
| **Goal** | Thin FastAPI app on `127.0.0.1` wrapping P1 façade: readiness, catalog, status, structured success/error JSON. |
| **Why now** | Prove React-compatible contracts before UI work. |
| **Expected code areas** | `src/stockballdb/api/` (FastAPI factory, routes, schemas, settings); ASGI entry via `python -m stockballdb.api`. |
| **Reuse V1** | Nothing rewritten — only call `app.*`. |
| **New V2** | Transport adapters + API tests. |
| **Tests** | Transport/contract tests (TestClient); error-envelope cases. |
| **Completion gate** | Local curl/TestClient proves readiness + catalog + status; binds localhost only; façade remains HTTP-agnostic. |
| **Non-goals** | Full endpoint catalog, SSE, auth system, Electron, React. |
| **Risk** | **Low**. |
| **Status** | **Complete** — endpoints `/ready`, `/api/catalog/*`, `/api/status`; pytest 241 passed / 3 skipped. |

---

### Phase 3 — React foundation + vertical slice

| Item | Content |
| ---- | ------- |
| **Goal** | Scaffold React app (feature folders, Tier 1–3), TypeScript client to FastAPI, minimal pages: readiness + instrument list + status view. |
| **Why now** | Complete the early E2E boundary proof. |
| **Expected code areas** | New `frontend/` (name flexible); `client/`, `features/`, `app/` shell/routing. |
| **Reuse V1** | Data via API only. |
| **New V2** | React foundation + client. |
| **Tests** | Client contract tests and/or minimal component tests where valuable; manual E2E checklist. |
| **Completion gate** | Dev mode works: React dev server + FastAPI + PostgreSQL show live instruments/status; no Electron required. |
| **Non-goals** | Full Explorer, Day Inspector, styling finalization, Electron, copying AI Studio wholesale. |
| **Risk** | **Medium** — toolchain/bootstrap, keep dependencies minimal. |
| **Status** | **Complete** — `frontend/` Vite+React+TS; Status+Catalog vertical slice; vitest 9 passed; Python 241/3; production build OK. |

**Decisions required before P3 starts (minimal):** React+TS bundler baseline (e.g. Vite), router approach, how client points at localhost API. **Do not** lock data-grid/styling/state libraries yet unless blocking.

---

### Phase 4 — Google AI Studio prototype reconciliation

| Item | Content |
| ---- | ------- |
| **Goal** | When the prototype is in GitHub, audit it and map: prototype feature → keep/modify/discard → production React feature → backend requirement → gaps. |
| **Why now** | Preserve preferred UI direction without inheriting generated architecture. Must inform Explorer implementation (**before P6 goes deep**). |
| **Expected code areas** | Docs artifact (mapping note in progress/roadmap appendix or short audit doc); no blind code import. |
| **Reuse V1** | N/A. |
| **New V2** | Reconciliation map only. |
| **Tests** | Review checklist complete. |
| **Completion gate** | Written keep/modify/discard map approved as the UI reference for P6+. |
| **Non-goals** | Rebuilding the entire prototype; adopting its API/state assumptions. |
| **Risk** | **Low** (process); **High** if skipped and prototype is copied blindly. |

**Checkpoint:** User pushes prototype to GitHub → Cursor inspects → mapping produced → then continue P5/P6 with eyes open.  
If prototype is delayed, P5 may proceed; **do not finish P6 without the audit** once the prototype exists.

---

### Phase 5 — Explore façade (multi-symbol read queries)

| Item | Content |
| ---- | ------- |
| **Goal** | `app.read.explore` (and FastAPI routes) for allowlisted browse/filter/sort/paginate with **multi-symbol** support and field selection contracts suitable for Explorer V2. |
| **Why now** | Explorer UI must not invent unbounded SQL; backend must exist first (or immediately alongside first Explorer spike — prefer backend contracts first). |
| **Expected code areas** | `app/read/explore.py`; extend `explorer/queries` / registry usage; transport routes. |
| **Reuse V1** | `explorer/queries.py`, `registry.py`, `explorer/db` read-only path. |
| **New V2** | Multi-symbol/compare-oriented query operations; DTOs. |
| **Tests** | Façade + API tests for filters/pagination caps; deny non-allowlisted columns. |
| **Completion gate** | API returns paginated multi-symbol pages without huge unbounded dumps; V1 Explorer unaffected. |
| **Non-goals** | Full React Explorer, research analytics, Arrow protocols. |
| **Risk** | **Medium** — query shape design; keep pagination mandatory. |

**Strategy:** Implement multi-symbol backend **before** (or as hard prerequisite to) full Explorer UI. Incremental UI can follow immediately in P6.

---

### Phase 6 — Explorer V2 UI

| Item | Content |
| ---- | ------- |
| **Goal** | Production Explorer: repeatable instrument groups, add/remove, no hard 3-symbol cap, per-instrument fields, shared dates, ordering, filter/sort/pagination, navigation toward Day Inspector. |
| **Why now** | Core V2 product surface after contracts + prototype map exist. |
| **Expected code areas** | `features/explorer/`, shared selectors/grid components; client methods from P5. |
| **Reuse V1** | Semantics/definitions via Catalog; not Streamlit views. |
| **New V2** | Explorer feature UI aligned to reconciliation map. |
| **Tests** | Component tests for critical selectors; manual Explorer checklist; contract tests against API. |
| **Completion gate** | Checklist in §6 requirements met against live DB via FastAPI; no direct DB access from React. |
| **Non-goals** | Maintenance mutations, Electron, universe GitHub sync, V3 charts/experiments. |
| **Risk** | **Medium–High** — UX complexity; mitigate with P4 map + P5 contracts. |

---

### Phase 7 — Day Inspector

| Item | Content |
| ---- | ------- |
| **Goal** | Dedicated Day façade operation (wrapping V1 day inspect logic) + React Day Inspector with drilldown from Explorer. |
| **Why now** | Natural next inspection workflow; shares Catalog/Explore date/symbol context. |
| **Expected code areas** | `app/read/day.py`; transport; `features/day-inspector/`; reuse `explorer/services/day` + queries. |
| **Reuse V1** | Day inspector service/query helpers. |
| **New V2** | Façade + React feature. |
| **Tests** | Façade tests for trading/non-trading dates; UI checklist. |
| **Completion gate** | Inspect date/symbol from Explorer navigation; read-only path only. |
| **Non-goals** | Predictive “what happens next” panels. |
| **Risk** | **Low–Medium**. |

**Strategy:** Combination — dedicated `app.read.day` façade **over** existing V1 day helpers (not a fork of business rules).

---

### Phase 8 — Dashboard / Status enrichment + short maintenance ops

| Item | Content |
| ---- | ------- |
| **Goal** | Dashboard/Status UI: coverage, provenance, manifests/run reports, fingerprint display; on-demand validate/health/verify (synchronous or short). |
| **Why now** | Operators need trust/visibility before long mutating workflows. |
| **Expected code areas** | Expand `app.read.status`; transport; `features/dashboard`, `features/status`. |
| **Reuse V1** | health coverage/provenance, artifacts discovery, snapshot verify. |
| **New V2** | Status/Dashboard features. |
| **Tests** | API tests; manual status checklist; fingerprint match expectations for read-only ops. |
| **Completion gate** | Status surfaces match V1 Explorer Validation/Control intent without mutations. |
| **Non-goals** | Update/Fresh Build/Rebuild execution (P9/P11). |
| **Risk** | **Low**. |

---

### Phase 9 — Maintenance: Update Database (long-running)

| Item | Content |
| ---- | ------- |
| **Goal** | UI-safe **Update Database** via `app.maintenance.update` adapter over `run_update`; start + status polling (SSE optional later); respect advisory lock; no unsafe cancel. |
| **Why now** | First real mutating maintenance after read stack is trusted. |
| **Expected code areas** | `app/maintenance/update.py`; transport maintenance routes; `features/maintenance/`; minimal operation-status tracking (not a generic job platform). |
| **Reuse V1** | `update.orchestrator.run_update`, locks, validate/health gates. |
| **New V2** | Adapter + UI + status model. |
| **Tests** | Adapter tests with test DB where safe; conflict-when-locked cases; **V1 CLI update regression** on disposable/test practices; never casual primary pytest mutation. |
| **Completion gate** | Update can be started/monitored from UI; structured completion/failure; closing UI does not silently corrupt (integrity principle). |
| **Non-goals** | Fresh Build, Exact Rebuild, Backup, universe GitHub sync, cancellation. |
| **Risk** | **High** — mutating; keep adapters thin; heavy V1 regression. |

Introduce **operation-status infrastructure here** (only as needed for update), not earlier.

---

### Phase 10 — Universe portable definition (+ synchronization)

| Item | Content |
| ---- | ------- |
| **Goal** | Evolve from `market_data/universe.py` constants toward portable version-controlled instrument definition; façade Universe service; later GitHub sync. Preserve WTI/non-ETF kinds; fix brittle assumptions (e.g. hard-coded ETF counts) carefully. |
| **Why now** | Needed before polished Fresh Build/multi-machine workflows; Catalog already abstracts consumers. |
| **Expected code areas** | `app/universe/`; definition file (format chosen in this phase); adapters so Catalog/Explore read façade universe; optional GitHub transport. |
| **Reuse V1** | Existing symbol routing/pipelines; do not flag-day rewrite all call sites at once. |
| **New V2** | Portable definition + sync workflows. |
| **Tests** | Definition validation; equivalence vs current V1 constants; pipeline still builds expected symbols; non-ETF path intact. |
| **Completion gate** | Façade serves universe from portable definition; sync (local and/or GitHub) documented and tested; Update remains distinct from universe sync. |
| **Non-goals** | Mega “StockBallDB definition” including macro/events; inventing ETF-only model. |
| **Risk** | **High** — touches many consumers; migrate in steps (façade first → file → adapt call sites → sync). |

**Transition sequence (within phase):**  
1) façade reads V1 constants → 2) introduce portable file → 3) validate equivalence → 4) adapt consumers → 5) GitHub sync → 6) add-instrument application workflow.

---

### Phase 11 — Fresh Build

| Item | Content |
| ---- | ------- |
| **Goal** | Expose Fresh Build for empty PostgreSQL: configure → `run_build_v1` adapter → validate/health/fingerprint → usable DB. |
| **Why now** | Requires Maintenance patterns (P9) and preferably Universe (P10). |
| **Expected code areas** | `app/maintenance/build.py`; maintenance UI; first-run guidance hooks. |
| **Reuse V1** | `build_v1.run_build_v1` / BUILD_STAGES — wrap, don’t replace. |
| **New V2** | Adapter + UI/first-run wiring. |
| **Tests** | Disposable empty DB Fresh Build where feasible; V1 build regression awareness; distinct from Exact Rebuild. |
| **Completion gate** | New machine path documented and proven: empty PG → usable StockBallDB via UI/API. |
| **Non-goals** | Replacing Exact Rebuild; claiming bit-identity with live provider refetch. |
| **Risk** | **High**. |

---

### Phase 12 — Backup / Restore

| Item | Content |
| ---- | ------- |
| **Goal** | Distinct operational Backup/Restore of local PostgreSQL StockBallDB (format chosen here or narrowly earlier if blocked). Include validation/version metadata; no live data-directory copy as official method. |
| **Why now** | Portability complement after Fresh Build exists. |
| **Expected code areas** | `app/maintenance/backup.py`; infrastructure helper; maintenance UI. |
| **Reuse V1** | None required as core pipeline; may verify with validate/health after restore. |
| **New V2** | Backup/Restore capability. |
| **Tests** | Backup → restore onto disposable DB → validate; refusal of dangerous overwrite without confirm. |
| **Completion gate** | Backup and restore proven; distinct from Fresh Build/Update/Exact Rebuild. |
| **Non-goals** | Cloud backup SaaS; Exact Rebuild replacement. |
| **Risk** | **High**. |

---

### Phase 13 — Electron desktop shell

| Item | Content |
| ---- | ------- |
| **Goal** | Electron loads production React build, spawns FastAPI child, readiness, localhost only, safe shutdown respecting maintenance integrity. |
| **Why now** | Wrap a **proven** React+FastAPI+PostgreSQL system — not the early debug environment. |
| **Expected code areas** | New `desktop/` (name flexible); packaging scripts (installer tool still open). |
| **Reuse V1** | Backend unchanged. |
| **New V2** | Electron shell + lifecycle. |
| **Tests** | Smoke: launch → UI loads → catalog works → quit clean when idle; maintenance-active quit behavior per locked safety. |
| **Completion gate** | Double-click/desktop launch works without manual terminals; Python child managed; PG still external. |
| **Non-goals** | Auto-update system; embedding PostgreSQL; rewriting API. |
| **Risk** | **Medium**. |

---

### Phase 14 — V2 certification / closeout

| Item | Content |
| ---- | ------- |
| **Goal** | Declare V2 complete against §8 definition; create `StockBallDB_V2_status.md` when certified; reconcile docs. |
| **Why now** | Final gate. |
| **Expected code areas** | Docs/status; fix only certification defects. |
| **Reuse V1** | Full V1 regression suite + operational gates. |
| **New V2** | V2 status baseline record. |
| **Tests** | Full V1 + V2 suites; health/validate; Explorer/Day/Maintenance/Universe/Fresh Build/Backup/Electron smoke. |
| **Completion gate** | See §8. |
| **Non-goals** | V3 features. |
| **Risk** | **Medium** — process discipline. |

---

## 6. Explorer requirements (P6 checklist)

Must support:

* repeatable instrument groups;
* no arbitrary three-symbol comparison limit;
* grouped instrument headers;
* add/remove instruments;
* per-instrument field selection;
* shared date context;
* column/instrument ordering;
* filtering, sorting, pagination;
* Day Inspector drilldown entry.

Backend must paginate; do not return entire history because the UI can scroll.

---

## 7. Testing strategy (integrated)

| Kind | Where it matters most |
| ---- | --------------------- |
| Unit | Pure façade helpers, DTO mapping |
| Façade/application | Catalog/Explore/Day/Status/Maintenance adapters |
| FastAPI transport | Contract + error envelope + localhost assumptions |
| React | Critical selectors/client mapping; not every pixel |
| Contract | TS client ↔ OpenAPI/DTO alignment on vertical slice + Explorer |
| Integration | Test DB only for mutating paths |
| Maintenance safety | Lock conflict; no silent kill assumptions |
| V1 regression | Recurring after P1+, mandatory after P5/P6/P9/P10/P11/P13 |
| Electron smoke | P13+ |

**V1 regression recurring gate (minimum):** `validate_v1` / health (as appropriate), relevant pytest subset, Streamlit Explorer still importable/launchable, update/build/rebuild not casually broken.

---

## 8. V2 completion / certification definition

StockBallDB V2 may be declared complete when **all** are true:

1. React app usable for View → Filter → Explore → Inspect → Maintain (in scope).
2. Explorer V2 checklist (§6) met.
3. Day Inspector operational.
4. Status/validation/health/fingerprint/snapshot verify accessible.
5. Update Database operational via UI/API safely.
6. Universe portable definition operational; sync available per locked direction.
7. Fresh Build proven on empty PostgreSQL.
8. Backup/Restore proven and distinct.
9. Exact Rebuild still available (CLI and/or UI) and not weakened.
10. Electron launch/runtime proven (Python child managed).
11. V1 regression suite passes; V2 tests pass.
12. Health/validate acceptable on certified DB practices.
13. Documentation reconciled (`V2_status` created; progress/architecture/decisions current).
14. No V3 research features required.

---

## 9. Documentation strategy during implementation

| Doc | Role during build |
| --- | ----------------- |
| `StockBallDB_V2_progress.md` | Living status — update each phase |
| `StockBallDB_V2_roadmap.md` | This plan — mark phase status lightly |
| `StockBallDB_V2_decisions.md` | Only when a real decision locks |
| `StockBallDB_V2_architecture.md` | Update when architecture actually changes |
| `StockBallDB_V2_scope.md` | Rarely — scope changes only |
| Canonical V1 docs | Untouched unless implemented system behavior changes |
| `project_steps.md` / `phase_history.md` | Per existing process rules |
| Manual doc audits | At major checkpoints (after P3, P6, P9, P13, P14) rather than every tiny edit |

---

## 10. Git strategy

* Meaningful commits per phase or coherent sub-phase — not per bullet.
* Do not push automatically.
* Do not include unrelated dirty files (e.g. accidental rule deletions).
* Prefer local commits at phase gates; push when the user requests.
* Keep V1-safe: avoid mixing large refactors with feature phases.

---

## 11. Open items (not blockers for P1)

* Universe file format / GitHub auth details (P10).
* Backup format (P12).
* Python bundler / installer tooling (P13).
* Exact port/session-token mechanics.
* SSE vs poll for progress (start with poll in P9).
* React data-grid/styling/state libraries (choose when P3/P6 needs them).
* Exact quit-during-maintenance UX (integrity principle already locked).

---

## 12. Phase status tracker

| Phase | Status |
| ----- | ------ |
| P1 `stockballdb.app` foundation | **Complete** |
| P2 FastAPI read transport | **Complete** |
| P3 React foundation + vertical slice | **Complete** |
| P4 Prototype reconciliation | Not started (blocked on prototype in GitHub until inspected) |
| P5 Explore façade | Not started |
| P6 Explorer V2 UI | Not started |
| P7 Day Inspector | Not started |
| P8 Dashboard/Status + short ops | Not started |
| P9 Update Database | Not started |
| P10 Universe portable + sync | Not started |
| P11 Fresh Build | Not started |
| P12 Backup / Restore | Not started |
| P13 Electron shell | Not started |
| P14 V2 certification | Not started |

**Next to execute:** **Phase 4** (prototype reconciliation).
