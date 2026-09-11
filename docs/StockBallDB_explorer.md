# StockBallDB Explorer

**Status:** Phase 11C COMPLETED (functional + read-only certification). Phase 11D desktop presentation refresh **implemented**; Phase 11D manual UX certification **pending**.

Local, read-only inspection interface for the certified StockBallDB database.

---

## Purpose

StockBallDB Explorer is a **local read-only inspection** tool. It helps an operator understand, verify, trace, and audit data already contained in or produced by StockBallDB.

It answers factual questions such as:

```text
What data exists?
What does this row / date / symbol contain?
Where did this value come from (dataset / build level)?
How much history do we have?
Where are the gaps?
What is database health?
What happened on this particular date?
Which manifest / snapshot / build produced the current state?
```

It is **not** a research, trading, signals, or strategy tool. It does **not** answer:

```text
Should I buy this?
Which ETF is strongest?
What predicts tomorrow?
Which strategy works best?
What happens if I backtest this rule?
```

Explorer displays canonical facts. It does not create new financial definitions, metrics, or recommendations.

---

## Strict read-only boundary

Read-only is enforced at multiple layers — not merely by omitting edit buttons.

| Layer | Rule |
| --- | --- |
| Application code | Zero INSERT / UPDATE / DELETE / TRUNCATE / DDL in the Explorer package |
| Query layer | Parameterized SQLAlchemy `select()` only; table and column names from explicit allowlists |
| Session | `SET TRANSACTION READ ONLY` (via Explorer read-only connection helpers) |
| Operations | No update, rebuild, build, or manual-correction triggers in the UI |
| Console | No raw SQL console, ad-hoc query textarea, or string-concatenated user SQL |
| Filesystem | Manifests / snapshots opened read-only through `reports_dir()` and `SnapshotStore` only |

**MUST NOT:** mutate the database, invent display values for NULL, or shell-parse CLI text output.

DBeaver (or equivalent) remains the tool for unrestricted SQL inspection by advanced operators.

---

## Architecture

```text
Streamlit UI
  → explorer service layer
    → shared Python APIs (health / validate / fingerprint / provenance / queries)
      → PostgreSQL + build_reports/ + snapshots/
```

Explorer **must** call structured package APIs. It must **not** shell out to CLIs and parse console text.

Primary reusable surfaces include health (`run_health`, coverage, freshness, gaps), `validate_v1_database`, `compute_database_fingerprint`, provenance/manifest helpers, snapshot verify, and Explorer registry/query modules.

**Service boundary:** UI components must not embed large raw SQL strings. Query semantics live in the Explorer query/service layer with allowlisted tables and sort columns.

---

## Launch

From the project root (Streamlit required; included in project dependencies):

```bash
pip install -e .
# or: pip install -r requirements.txt

python -m stockballdb.explorer
```

Streamlit binds to **localhost** only. Use **Refresh** to invalidate session-cached data after an external operational update.

---

## Six pages

| Page | Responsibility |
| --- | --- |
| **Control Center** | At-a-glance health, fingerprint (on demand), Alembic/git provenance, latest operational run and Manifest 1.1, table/symbol coverage summary, provider freshness, snapshot verify status for latest manifest. Status language reused from the package: `HEALTHY` / `HEALTHY WITH WARNINGS` / `UNHEALTHY`; `PASS` / `FAIL`; `SUCCESS_UPDATED` / `SUCCESS_NO_CHANGE` / `FAILED`. No tickers, heatmaps, or signal scores. |
| **Data Explorer** | Browse all seven canonical tables with server-side filters, allowlisted sort, pagination, definitions tooltips, and optional bounded CSV export. |
| **Day Inspector** | Cross-table factual view for one calendar date (+ optional symbol focus). Separate bounded queries — not one mega-join. Supports trading days and non-trading event dates without fabricating `trading_days` rows. |
| **Coverage Explorer** | Table/symbol coverage, freshness/lag, gap findings, and missingness classification reused from health tooling. |
| **Provenance Explorer** | Dataset/build-level provenance: manifests, run reports, snapshot metadata and verification, fingerprints, `exact_rebuild_capable`. No secrets, credentials, or database/provider URLs. |
| **Validation Center** | On-demand display of validate_v1, health findings, coverage/freshness/gaps, snapshot verify, and database/table fingerprints. No second validation engine. Manual run buttons only — no background polling daemon. |

Sidebar / shell: page navigation plus global **Refresh**.

---

## Filtering, pagination, and sort

| Constant | Value |
| --- | --- |
| `DEFAULT_PAGE_SIZE` | 100 |
| `MAX_PAGE_SIZE` | 500 |
| CSV export cap | 10_000 rows |

Rules:

- Server/database-side filtering (`WHERE` in SQL) — not load-all-then-filter in Python
- Deterministic `ORDER BY` on an explicit **sort allowlist** (e.g. date, symbol, event_type, event_date, event_id)
- Default sort: primary key order (date ASC, symbol ASC where applicable)
- No arbitrary multi-column sort builder
- **No raw SQL**
- **No global search** — structured navigation and per-table filters only

Typical filters: date from/to; symbol where applicable; `event_type` for `scheduled_events`; optional stored boolean flags for `calendar_context`. No recommendation-style filters.

Constants live in `stockballdb.explorer.config`.

---

## Day Inspector — non-trading dates

Primary input: ISO date. Optional: symbol (focuses market tables; macro, calendar, and events stay market-wide).

| Input date type | Behavior |
| --- | --- |
| Trading day (in `trading_days`) | Full inspector sections per data availability |
| Scheduled event on non-trading day (e.g. Election 1958-11-04) | Show “Trading session: none”; display matching `scheduled_events`; show nearest spine sessions; **do not fabricate** a `trading_days` row |
| Weekend/holiday with no event | “Trading session: none”; nearest trading sessions |
| Outside StockBallDB history | Clear outside-coverage message with spine bounds |

Example:

```text
Calendar date: 1958-11-04
Trading session: none
Scheduled event: Election Day
Effective next StockBallDB session: 1958-11-05
```

---

## Missingness and NULL display

**Never display NULL as 0.** Never fabricate display values.

UI must distinguish expected vs integrity problems, including:

```text
expected historical floor
asset not yet in existence (pre-inception)
provider publication lag
known provider gap (e.g. WTI)
warm-up NULL (rolling windows)
forward-outcome tail NULL (not yet computable)
unresolved dataset (documented)
actual integrity problem (ERROR / FATAL findings)
```

Consistent NULL rendering (`—` or `NULL` app-wide). Do not paint every NULL as an error.

---

## Macro and units display

Formatting is presentation-only. Stored canonical values remain authoritative.

| Type | Rule |
| --- | --- |
| Prices | Decimal as stored (display rounding may apply, e.g. adj OHLC to 2 d.p. on screen) |
| Returns / decimal ratios | Respect definitions; percentage display is labeling only |
| Macro rates | **Percentage points vs decimal returns** — respect field definitions; no global “convert everything to %” |
| Dates | ISO 8601 |
| Hashes | Truncated with copy-full option |
| Booleans | Yes / No |

Field meaning, units, and PIT notes: [StockBallDB_definitions.md](StockBallDB_definitions.md).

---

## Provenance

Provenance is **dataset/build level**, not per-cell lineage (unless explicitly stored).

**Can show:** Manifest 1.1 fields, operational run reports, snapshot references/metadata/verification, git commit/dirty flag, Alembic revision, database and table fingerprints, `exact_rebuild_capable`, sanitized request identity.

**Cannot prove:** per-row “this cell came from snapshot X byte offset Y”; historical provider state at past calendar dates without REBUILD EXACT context.

**Never display:** API keys, auth headers, database URLs, passwords, tokens, unsanitized provider credentials. Reuse provenance secret-scanning patterns.

Do not render multi-MB raw snapshot payloads inline by default.

---

## Charts and derived UI math

Charts are **descriptive only** (coverage timeline, missing-date samples, row counts by symbol, single canonical series, freshness lag).

**Allowed:** row counts, coverage %, missing counts, pagination metadata, display formatting.

**Forbidden:** inventing new financial metrics in the UI (momentum scores, custom signals, strategy equity curves, forecasts, correlation research, backtests, technical indicators not stored in the DB).

---

## Configuration

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | Primary PostgreSQL URL (used when Explorer URL unset) |
| `STOCKBALLDB_EXPLORER_DATABASE_URL` | Optional dedicated read-only connection URL |

Explorer uses a separate SQLAlchemy engine from build/update workflows. Connection strings are never shown in the UI.

Optional operator hardening (not auto-created by StockBallDB): a PostgreSQL role with `SELECT` only on canonical tables, then point `STOCKBALLDB_EXPLORER_DATABASE_URL` at that role.

---

## Desktop UI (Phase 11D)

Phase 11D is a **presentation-only** refresh after Phase 11C functional certification. Same data, same six surfaces, same read-only semantics.

| Requirement | Value |
| --- | --- |
| Layout | `st.set_page_config(layout="wide", …)` |
| Primary target | Desktop **1920×1080** |
| Secondary | ~1280+ laptop widths usable |
| Mobile | Not a Phase 11D requirement |
| CSS | Narrow, documented, presentation-only (density / chrome / hierarchy) |
| Navigation | Preserve `st.navigation` + explicit `url_path` values (Phase 11C nav fix) |
| Framework | Streamlit only — no React / FastAPI UI migration |

Six surfaces remain functionally unchanged. Prefer presentation-layer changes; do not silently alter certified health/query/validation semantics.

Mockups are **visual direction only**, not functional requirements.

**Prohibited additions** (presentation refresh must not introduce):

- Query Explorer / arbitrary filter builders / raw SQL
- Saved presets or column-visibility product systems
- Split-ticker research layouts or new research metrics
- New SQL aggregations invented only to mimic mockup stats
- Write controls, update/rebuild triggers, or strategy/backtest UI

**Phase 11D status:** presentation refresh **implemented**. Functional certification remains **Phase 11C**. Phase 11D **manual UX certification is pending** (implementation complete ≠ 11D certified).

---

## Certification (Phase 11C)

**Phase 11C = COMPLETED.** Explorer did **not** mutate the database.

```text
fingerprint_before = compute_database_fingerprint(primary)
exercise every Explorer page and on-demand validation action
fingerprint_after  = compute_database_fingerprint(primary)

Expected: MATCH
```

**Current certified primary fingerprint:**

```text
sha256:5055ae10f216ff33141eb137fc396ce29481e896c3ea828983e4ca8b12291aca
```

Fingerprint before/after Explorer certification **MATCH**.

Formal closeout gates (2026-09-10) included validate_v1 PASS, health HEALTHY (INFO-only expected lag/gap findings), snapshot verify PASS (91 snapshots), `exact_rebuild_capable = True`, and read-only audit PASS (`SET TRANSACTION READ ONLY`; no DML/DDL; no update/rebuild triggers; no raw SQL console).

**Explorer tests:** 70 passed (Explorer suite). Full project pytest suite also green at closeout / subsequent presentation waves.

Six surfaces manually certified at 11C: Control Center, Data Explorer, Day Inspector (incl. 1958-11-04), Coverage Explorer, Provenance Explorer, Validation Center.

---

## Related documents

| Topic | Document |
| --- | --- |
| Principles / boundary | [StockBallDB_manifesto.md](StockBallDB_manifesto.md) |
| Field definitions / units | [StockBallDB_definitions.md](StockBallDB_definitions.md) |
| Providers | [StockBallDB_sources.md](StockBallDB_sources.md) |
| Validation, health & provenance | [StockBallDB_validation.md](StockBallDB_validation.md) |
| Snapshots & rebuilds | [StockBallDB_snapshots_and_rebuilds.md](StockBallDB_snapshots_and_rebuilds.md) |
| Operational update | [StockBallDB_operational_update.md](StockBallDB_operational_update.md) |
| Schema | [StockBallDB_schema.md](StockBallDB_schema.md) |
