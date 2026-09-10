# StockBallDB — Phase 11D: Explorer Desktop UI Refresh Contract

**Version:** 1.0  
**Date:** 2026-09-10  
**Status:** Authoritative contract for Phase 11D implementation  
**Prerequisite:** Phase 11C CERTIFIED; Phase 11 functionally COMPLETE

---

## 1. Purpose and historical truth

Phase 11D is a **post-certification presentation/UI refinement** of the certified StockBallDB Explorer.

| Phase | Meaning |
| --- | --- |
| **11A** | Explorer contract lock |
| **11B** | Functional Streamlit Explorer implementation |
| **11C** | Manual functional + read-only certification |
| **11D** | Desktop-first visual/layout refresh — **same data, same functionality** |

**Historical truth must be preserved:** Phase 11C certified functional/read-only behavior. Phase 11D improves the human-facing desktop interface. Do not rewrite 11A/B/C records as if 11D were the original delivery.

---

## 2. Desktop-first requirement

| Requirement | Value |
| --- | --- |
| Primary design target | **1920×1080** desktop |
| Secondary | ~1280+ laptop widths remain usable |
| Mobile responsiveness | **Not a Phase 11D requirement** |

Do not sacrifice desktop information density for phone-sized layouts.

Mandatory: `st.set_page_config(layout="wide", …)` as the first Streamlit configuration call.

---

## 3. Scope — presentation only

### In scope

- Application shell (compact header / navigation presentation)
- Shared presentation helpers
- Layout recomposition of the **six existing** Explorer surfaces
- Dense tables, compact toolbars, restrained professional styling
- Narrow, documented custom CSS
- Display-only financial coloring where Streamlit safely supports it

### Framework

**Streamlit remains the UI framework.** No React, FastAPI UI, or frontend migration in 11D.

### Six surfaces (unchanged inventory)

1. Control Center  
2. Data Explorer  
3. Day Inspector  
4. Coverage Explorer  
5. Provenance Explorer  
6. Validation Center  

Keep `st.navigation` + explicit `url_path` values (Phase 11C navigation fix).

---

## 4. Read-only invariants

Explorer remains strictly read-only:

- `readonly_connection()` / `SET TRANSACTION READ ONLY`
- SELECT-only query architecture
- No INSERT / UPDATE / DELETE / TRUNCATE / DDL
- No update / rebuild / build actions
- No raw SQL console

**Fingerprint before/after Explorer use must MATCH.** Canonical data must not change.

---

## 5. Backend / service reuse rule

Prefer changing the **presentation layer only**.

Reuse existing Explorer services, queries, registry, health, provenance, validation, pagination, and filters.

**If a UI need appears to require certified backend/semantic changes: STOP and report — do not silently change Phase 8/10/11C behavior.**

Protected unless absolutely necessary (and approved):

- `explorer/db.py`
- `health/*`
- `queries.py` semantics
- registry allowlists
- Coverage adapter (`collect_freshness(conn)` / `gap_findings(symbols)`)
- date bound semantics (Phase 11C ±10y fix)
- validate_v1 / fingerprint / snapshot verify
- schema, update, rebuild pipelines

---

## 6. Allowed presentation changes

- Wide layout and compact horizontal toolbars
- Header status (health / last update) via existing read-only APIs
- Key/value tables instead of raw `st.json` where display-only
- Dense dataframes with height/`column_config`
- Compact pagination chrome (same page semantics)
- Status badges, metric rows, section headers
- CSS for density, header, badges, spacing, optional Streamlit chrome reduction

---

## 7. Prohibited functional additions

Do **not** implement:

- Query Explorer / arbitrary query builder / Add Filter builder
- Saved presets / column visibility system
- Split ticker comparison / research metrics
- New SQL aggregations merely to mimic mockup statistics
- Update/universe/write controls
- Phase 12 functionality

Mockups are **visual direction only**.

---

## 8. CSS policy

Custom CSS is approved when:

- Narrowly scoped and documented
- Used for density/chrome/visual hierarchy — not functional correctness
- Avoiding brittle deep generated-DOM / nth-child widget hacks where avoidable

---

## 9. Testing requirements

- Full pytest suite after implementation
- Preserve Phase 11C regression coverage:
  - historical date_input explicit bounds
  - Coverage freshness/gap API arity
  - navigation `url_path` uniqueness / no `pages/` auto-discovery
  - Control Center live status + Latest Attempt vs Latest Successful Run
- Presentation helper unit tests as appropriate

---

## 10. Manual certification requirements

After implementation:

1. Record primary fingerprint (baseline expected: Phase 11C value)
2. Manually exercise all six surfaces on desktop (~1920×1080)
3. Recompute fingerprint — **must match**
4. validate_v1 PASS; health acceptable

**Implementation complete ≠ Phase 11D CERTIFIED.**  
Certification requires a separate manual UX pass.

Target status after this implementation wave:

```text
PHASE 11D = IMPLEMENTED — MANUAL CERTIFICATION PENDING
```

---

## 11. Document history

| Version | Date | Change |
| --- | --- | --- |
| 1.0 | 2026-09-10 | Phase 11D contract lock |
