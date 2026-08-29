# StockBallDB — Phase 9A Snapshot & Exact-Rebuild Architecture Contract

**Version:** 1.0  
**Status:** LOCKED (audit + architecture)  
**Date:** 2026-08-29  
**Scope:** Immutable source snapshot design, exact-rebuild semantics, manifest evolution, Phase 9B backlog. **No Phase 9B implementation in 9A.**

> Companion: [Phase 8A validation & provenance](StockBallDB_phase8a_validation_provenance_contract.md) · [schema](StockBallDB_schema.md) · [sources](StockBallDB_sources.md) · [workflow](StockBallDB_workflow.md)

---

## 1. Purpose

Phases 0–8 delivered a structurally valid, health-checked StockBallDB with build manifests that record **who, when, and what coverage** — but not **what exact source bytes** produced a historical build.

Phase 9 closes that gap:

```text
BUILD LATEST   → retrieve providers → immutable snapshots → normalize → canonical DB
REBUILD EXACT  → historical manifest → snapshots only (offline) → normalize → verify fingerprint
```

Phase 9A locks architecture before immutable source material begins accumulating.

---

## 2. Current acquisition audit

All live HTTP flows through `src/stockballdb/providers/` (`requests` only). **No raw responses are persisted today** — only normalized PostgreSQL rows and Phase 8 build manifests.

### 2.1 Acquisition inventory

| Source | Provider | Endpoint / identifier | Params | Response | Retrieval code | Normalization | Preserved today? | Can revise historically? | Bytes available at acquire? |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **14 ETFs** | Tiingo | `GET /tiingo/daily/{ticker}/prices` | `startDate=1957-01-01`; optional `endDate` | JSON array | `providers/tiingo.py` → `fetch_daily_prices()` | `market_data/normalize.py` → `normalize_tiingo_bars()` | **No** | **Yes** (adj_* restatements) | Transient `response.content` |
| **WTI** | FRED | `series/observations` `DCOILWTICO` | `api_key`, `file_type=json`, paginated | JSON | `providers/fred.py` → `fetch_current_observations()` | `market_data/normalize.py` → `normalize_fred_close_only_observations()` | **No** | **Yes** | Transient |
| **DFF** | FRED | `series/observations` | same | JSON | `fetch_current_observations()` | `macro/pit.py` → `build_current_series_on_trading_days()` | **No** | **Yes** | Transient |
| **DGS2, DGS10** | FRED | same | same | JSON | same | same | **No** | **Yes** | Transient |
| **WALCL** | FRED | same | same | JSON | same | same | **No** | **Yes** | Transient |
| **BAA10Y** | FRED | same | same | JSON | same | same | **No** | **Yes** | Transient |
| **CPIAUCSL** | ALFRED | `series/observations` + vintage window | `realtime_start=1776-07-04`, `realtime_end=9999-12-31`, paginated | JSON | `fetch_all_vintages()` | `macro/pit.py` → `parse_alfred_rows()` → PIT builders | **No** | **Yes** (new vintages) | Transient |
| **CPILFESL** | ALFRED | same | same | JSON | same | same | **No** | **Yes** | Transient |
| **UNRATE** | ALFRED | same | same | JSON | same | same + `events/releases.py` first-print | **No** | **Yes** | Transient |
| **ICSA** | ALFRED | same | same | JSON | same | same | **No** | **Yes** (sparse pre-~2009) | Transient |
| **FOMC historical** | Federal Reserve | `/monetarypolicy/fomchistorical{YYYY}.htm` (1957–2020) | path only | HTML | `providers/fed.py` → `fetch_text()` | `events/fomc.py` → `parse_historical_html()` | **No** | **Yes** (page edits) | Transient `response.text` |
| **FOMC calendar** | Federal Reserve | `/monetarypolicy/fomccalendars.htm` (2021+) | path only | HTML | same | `events/fomc.py` → `parse_calendars_html()` | **No** | **Yes** | Transient |
| **Election days** | Generated | 2 U.S.C. §7 rule | none | N/A | `events/elections.py` | direct `CanonicalEvent` | N/A | **No** | N/A |
| **NYSE calendar** | `pandas_market_calendars==5.4.0` | library `NYSE` calendar | date range | library dates | `calendar/nyse.py` | `calendar/trading_days_build.py` | N/A (pin only) | Package version dependent | N/A |

### 2.2 Non-acquisition / deferred

| Item | Status |
| --- | --- |
| `derive_*`, `outcomes`, `regimes`, `calendar_context` | Derived from canonical tables — no external fetch |
| `EIA_API_KEY` in config | Loaded but **unused**; no `providers/eia.py` |
| XAU/USD, DXY, PMI | Documented unresolved — **outside V1 universe** |

### 2.3 Orchestration

| Pipeline | Entry | External fetch? |
| --- | --- | --- |
| `build_v1` | `v1/stages.py` (8 stages) | Tiingo, FRED/ALFRED, Fed HTML, elections, NYSE lib |
| `build_wti` | `market_context/wti.py` | FRED DCOILWTICO — **not in `build_v1`** |
| Preflight | `v1/preflight.py` | Partial probes only (SPY 4 days, DFF 4 days, FOMC page) |

### 2.4 Fetch mode (all providers)

**Full-history refetch every build** — no incremental cursors, watermarks, or delta APIs. Idempotent upsert (trading_days deletes out-of-range; others upsert only).

Implication for Phase 9: each build captures **one complete snapshot per request identity** representing provider state at retrieval time. Exact rebuild replays that complete snapshot set — not an ordered chain of incremental deltas.

---

## 3. Source-type classification

| Type | Sources | Snapshot semantics |
| --- | --- | --- |
| **API JSON** | Tiingo, FRED, ALFRED | Preserve raw HTTP response body bytes (paginated pages concatenated deterministically — see §11) |
| **HTML page** | FOMC historical + calendar | Preserve raw HTML bytes (UTF-8 encoded) |
| **Generated deterministic** | Election days | **No payload snapshot** — code + statute provenance |
| **Library-generated calendar** | NYSE via `pandas_market_calendars` | **No payload snapshot** — `calendar_pin` + dependency version |
| **Derived internal** | outcomes, regimes, calendar_context | No snapshot — reproducible from upstream snapshots + code |

---

## 4. Snapshot definition (LOCKED)

> A **StockBallDB source snapshot** is an **immutable, content-addressed representation of the source material actually received or deterministically used by an acquisition/build run, captured before canonical normalization**.

Properties:

- Written once; never edited or overwritten.
- Identified primarily by **SHA-256 of canonical payload bytes** (see §6).
- Normalization **must consume the preserved snapshot** in BUILD LATEST (not a separate in-memory copy discarded after write).
- Snapshots are **not** canonical PostgreSQL rows.
- Snapshots are **not** a substitute for build manifests — manifests reference snapshots; snapshots do not reference builds exclusively (deduplication allows reuse).

---

## 5. Raw bytes vs parsed records (LOCKED: Hybrid C)

| Option | Verdict |
| --- | --- |
| A — Raw bytes only | Strong audit trail but harder inspection |
| B — Parsed records only | Cannot prove exact provider response |
| **C — Hybrid** | **LOCKED** |

**Locked choice:**

```text
PRIMARY   = immutable raw provider payload bytes (or deterministic concatenation thereof)
METADATA  = sidecar JSON (request identity, retrieval event, hash, paths)
OPTIONAL  = deterministic parsed sidecar for human inspection ONLY (never identity source)
```

Rules:

- **Content identity** derives from **raw bytes before compression** (§28).
- Parsed sidecars, if written, are derived artifacts with their own hash recorded separately; they must not replace raw payload as source-of-truth.
- Do **not** make pandas DataFrames the only snapshot format.

---

## 6. Snapshot identity & integrity (LOCKED)

| Decision | Locked choice |
| --- | --- |
| Hash algorithm | **SHA-256** |
| Hashed material | **Original uncompressed source bytes** |
| `snapshot_id` | **`sha256:` + lowercase hex digest** (content-addressed) |
| Metadata in hash? | **No** — retrieval time, build_id, HTTP headers are **not** part of content identity |
| Deduplication | **Yes** — identical bytes → same `snapshot_id`; separate retrieval events |
| Mutation detection | Re-hash on read; mismatch → **corruption error** |
| Provider revision | Same request identity + different content hash → **two immutable snapshots**, both retained |

---

## 7. Immutability contract (LOCKED)

Once written and verified:

1. Payload file cannot be edited.
2. Same `snapshot_id` cannot point to different content.
3. Overwrite attempts must fail (content-addressed paths make accidental overwrite unlikely).
4. Metadata sidecars may be appended in separate files but must not alter payload bytes.

**Same bytes retrieved twice:**

```text
1 snapshot content object
2 retrieval event records (in manifest / retrieval log)
```

---

## 8. Storage architecture (LOCKED)

| Decision | Locked choice |
| --- | --- |
| Payload location | **Local filesystem** (Git-ignored); portable to object storage later |
| PostgreSQL payloads | **No** — canonical tables only |
| Root directory | **`snapshots/`** at repo root (add to `.gitignore`) |
| Layout | **Content-addressed hybrid** |

```text
snapshots/
  sha256/
    ab/
      abcdef...<full64hex>          # raw payload (optionally .gz — see §28)
      abcdef...<full64hex>.meta.json # sidecar metadata
```

Optional provider prefix symlinks or index entries for browseability — not identity-bearing.

| Concern | Approach |
| --- | --- |
| Git | **`snapshots/` gitignored** — never commit payloads |
| Inspectability | Sidecar JSON + optional parsed preview |
| Deduplication | Content-addressed paths |
| Portability | Relative paths in manifest; `sha256/` prefix maps to S3 `{prefix}{hash}` |
| Windows | Two-char shard prefix avoids huge flat directories |

---

## 9. Snapshot metadata (LOCKED minimum)

Sidecar `.meta.json` per snapshot (does not affect content hash):

| Field | Required | Notes |
| --- | --- | --- |
| `snapshot_id` | yes | `sha256:...` |
| `sha256` | yes | hex digest |
| `provider` | yes | e.g. `tiingo`, `fred`, `alfred`, `federal_reserve` |
| `source_identifier` | yes | series_id, symbol, or page path |
| `source_type` | yes | `api_json`, `html_page`, … |
| `retrieved_at` | yes | ISO8601 UTC — **retrieval event time** |
| `content_type` | yes | e.g. `application/json`, `text/html` |
| `byte_size` | yes | uncompressed |
| `encoding` | yes | e.g. `utf-8` |
| `request_identity` | yes | canonical dict — **no secrets** (§30) |
| `payload_path` | yes | relative path from repo root |
| `storage_encoding` | if compressed | e.g. `gzip` |
| `http_status` | recommended | when HTTP-sourced |
| `etag` | optional | if provider returns |
| `last_modified` | optional | if provider returns |
| `provider_url_template` | optional | sanitized template without credentials |

**Never persist:** API keys, Authorization headers, passwords, secret query params, full authenticated URLs, DB credentials.

---

## 10. Request identity (LOCKED)

Canonical, deterministic, credential-free dict. Examples:

```json
{
  "provider": "tiingo",
  "endpoint": "daily_prices",
  "symbol": "SPY",
  "start_date": "1957-01-01",
  "end_date": null
}
```

```json
{
  "provider": "fred",
  "endpoint": "series/observations",
  "series_id": "DCOILWTICO",
  "realtime_start": null,
  "realtime_end": null,
  "observation_start": null,
  "observation_end": null,
  "pagination": "full_concat_v1"
}
```

```json
{
  "provider": "alfred",
  "endpoint": "series/observations",
  "series_id": "CPIAUCSL",
  "realtime_start": "1776-07-04",
  "realtime_end": "9999-12-31",
  "pagination": "full_concat_v1"
}
```

```json
{
  "provider": "federal_reserve",
  "endpoint": "html_page",
  "path": "/monetarypolicy/fomchistorical2019.htm"
}
```

Rules:

- Keys sorted when serialized for determinism.
- `null` explicit for omitted optional params.
- Never include `api_key` or auth tokens.

---

## 11. Retrieval event vs snapshot content (LOCKED)

| Concept | Meaning |
| --- | --- |
| **Snapshot content** | Immutable bytes + content hash |
| **Retrieval event** | A point-in-time fetch that produced or confirmed those bytes |

Build manifest records **retrieval events** referencing **snapshot_id**. Multiple retrieval events may reference one snapshot.

Phase 8 manifest fields `retrieved_at` / `build_started_at` remain build-boundary timestamps. Phase 9 adds per-snapshot `retrieved_at` in sidecars and manifest snapshot entries.

---

## 12. Build manifest evolution (LOCKED)

| Item | Decision |
| --- | --- |
| Current schema | `schema_version: "1.0"` (Phase 8) |
| Phase 9 schema | **`"1.1"`** — backward-compatible minor bump |
| Pre-Phase-9 manifests | Classified **`PROVENANCE-CAPABLE`**, **`NOT EXACT-REBUILD-CAPABLE`** |

New fields in 1.1:

```json
{
  "schema_version": "1.1",
  "snapshot_capture": true,
  "database_fingerprint": "sha256:...",
  "snapshots": [
    {
      "snapshot_id": "sha256:...",
      "provider": "tiingo",
      "source_identifier": "SPY",
      "request_identity": { },
      "retrieved_at": "2026-08-29T...",
      "sha256": "...",
      "payload_path": "snapshots/sha256/ab/abc...",
      "byte_size": 1234567
    }
  ],
  "reproducibility_mode": "snapshot_capable"
}
```

Phase 8 `1.0` manifests remain readable; tooling treats missing `snapshots` as pre-snapshot builds.

**No `snapshot set` abstraction** — ordered snapshot list in manifest is sufficient.

---

## 13. Per-provider snapshot granularity (LOCKED)

| Source | Granularity | Rationale |
| --- | --- | --- |
| **Tiingo** | **One snapshot per symbol request** (14 per ETF build) | Maps 1:1 to API call; enables per-symbol dedup |
| **FRED current** | **One snapshot per series** | One series/observations request chain; paginated pages **concatenated deterministically** into single byte payload per series |
| **ALFRED** | **One snapshot per series** (full vintage window) | PIT reconstruction requires complete vintage dump |
| **FOMC historical** | **One snapshot per HTML page** (~64 year pages) | Page is natural fetch unit; enables partial dedup on unchanged years |
| **FOMC calendar** | **One snapshot** (`fomccalendars.htm`) | Single page |
| **Elections** | **None** | Deterministic generation |
| **NYSE calendar** | **None** | `calendar_pin` + code version |
| **WTI** | **One snapshot** (`DCOILWTICO`) | Same as FRED current |

### FRED/ALFRED pagination concatenation (LOCKED)

For multi-page responses, concatenate **raw response bodies** in ascending offset order with a deterministic separator:

```text
---STOCKBALLDB_PAGE_BOUNDARY---
offset=0
<body bytes>
---STOCKBALLDB_PAGE_BOUNDARY---
offset=100000
<body bytes>
```

Hash the concatenated result. Document separator in sidecar `request_identity.pagination = "full_concat_v1"`.

---

## 14. Full fetch vs incremental (LOCKED semantics)

All current providers use **full fetch**. Phase 9B initial implementation:

- One snapshot per request identity **per build** captures the **complete** provider response at retrieval time.
- Exact rebuild requires **all snapshots listed in that build's manifest** — not a historical chain of deltas.

Future incremental fetch (Phase 10+) must define ordered snapshot sequences; out of 9B scope unless needed.

---

## 15. Provider-specific preservation rules

### 15.1 ALFRED PIT (LOCKED)

Snapshots must preserve **complete ALFRED JSON observation rows** including:

```text
date, value, realtime_start, realtime_end
```

Never collapse to current revised values only. The snapshot is input to:

- `parse_alfred_rows()` → PIT state maps
- `first_print_events()` for CPI / employment events
- YoY computation from index levels

Provider revision example: two builds, same `CPIAUCSL` request identity, different vintage sets → **two snapshots**, both retained.

### 15.2 FRED current series (LOCKED)

Snapshot the **full current-vintage observation history** JSON as returned at retrieval time, including FRED's own `realtime_start`/`realtime_end` fields on each row.

Applies to: `DFF`, `DGS2`, `DGS10`, `WALCL`, `BAA10Y`, `DCOILWTICO`.

Later FRED revisions to historical values require a **new snapshot** — never overwrite.

### 15.3 Tiingo (LOCKED)

Preserve **entire JSON array** returned by Tiingo, including all provider fields (not only fields StockBallDB currently maps). Validated minimum: `TIINGO_PRICE_FIELDS` set in `providers/tiingo.py`.

### 15.4 HTML / FOMC (LOCKED)

Preserve **raw HTML bytes** — not extracted dates alone. Extraction is normalization; snapshot is the page material.

### 15.5 Deterministic sources (LOCKED)

| Source | Snapshot? | Exact-rebuild requires |
| --- | --- | --- |
| Election days | **No** | Git commit + election algorithm code |
| NYSE calendar | **No** | `calendar_pin` (`pandas_market_calendars==5.4.0`) + date range params |
| Derived tables | **No** | Upstream snapshots + code |

Do not manufacture fake snapshot files for deterministic calculations.

### 15.6 Calendar special case (LOCKED)

Exact rebuild of `trading_days` requires:

```text
calendar_pin (package + version)
start/end date parameters
locked calendar generation code at Git commit
```

Not a raw NYSE download. Integrates with existing Phase 8 `calendar_pin` in manifest.

---

## 16. Build modes (LOCKED)

### 16.1 BUILD LATEST

```text
1. retrieve provider material (network allowed)
2. write immutable snapshot (atomic)
3. verify SHA-256
4. register retrieval metadata
5. parse/normalize FROM snapshot bytes (not parallel in-memory-only path)
6. build canonical tables
7. validate_v1
8. health
9. compute database fingerprint
10. write manifest 1.1 referencing all snapshots
```

### 16.2 REBUILD EXACT

```text
1. load historical build manifest (schema 1.1+)
2. resolve every referenced snapshot
3. verify SHA-256 on disk
4. NO provider network calls (LOCKED — offline)
5. parse/normalize snapshots
6. derive canonical tables
7. validate_v1
8. compute fingerprint
9. compare to manifest.database_fingerprint
```

**Failure behavior (LOCKED):**

| Condition | Result |
| --- | --- |
| Missing snapshot | **FAIL** — do not fetch from provider |
| Hash mismatch | **FAIL** — corruption |
| Manifest pre-9 (no snapshots) | **FAIL** with clear `NOT_EXACT_REBUILD_CAPABLE` |
| Silent provider fallback | **FORBIDDEN** |

### 16.3 REPROCESS SNAPSHOTS (conceptual — may defer implementation)

```text
historical snapshots + CURRENT code/schema → canonical DB
```

Different from REBUILD EXACT (historical code/schema). Useful for schema migrations on old source material. Terminology locked; implementation optional in 9B.

---

## 17. Offline requirement (LOCKED)

**REBUILD EXACT must be fully offline with respect to data providers.**

Network isolation approach (9B recommendation — simplest robust):

```text
source_mode: "live" | "snapshot"
```

- Provider clients accept injected transport or raise if called in `snapshot` mode.
- Exact rebuild entrypoint sets `source_mode=snapshot` globally.
- Integration test: mock/spy asserts zero HTTP calls during exact rebuild.

---

## 18. Exact equality target (LOCKED)

**Level 2 — Database logical equivalence** (not PostgreSQL byte identity):

> Deterministic logical equality of all seven canonical tables under the locked schema/build version.

Includes row values, NULLs, and keys. Ignores physical row order and internal PostgreSQL TID/CTID.

**Not required:** byte-identical PostgreSQL cluster files.

---

## 19. Canonical database fingerprint (LOCKED design)

Deterministic fingerprint for proving exact rebuild:

```text
per-table hash  →  database hash
```

### 19.1 Per-table serialization (LOCKED rules)

For each canonical table, in **fixed table order** (alphabetical by table name):

1. **Column order:** alphabetical by column name (excluding no columns — all persisted columns).
2. **Row order:** primary key columns ascending (composite PK: lexicographic by PK column order as defined in schema).
3. **NULL:** literal `\N`
4. **date:** ISO8601 `YYYY-MM-DD`
5. **Numeric:** PostgreSQL `Numeric` → decimal string via `format(d, 'f')` stripped of trailing zeros except preserve at least one decimal place for integers stored as numeric; **use Decimal from DB driver, never float**
6. **String:** UTF-8, no delimiter escaping beyond pipe-separated fields
7. **Row format:** `col1|col2|...|colN\n`
8. **Table hash:** SHA-256 of UTF-8 encoded serialized rows

### 19.2 Database hash

```text
database_fingerprint = SHA-256( table_name + ":" + table_hash + "\n" for each table in order )
```

Prefix: `sha256:` + hex.

Store in manifest 1.1 as `database_fingerprint`.

### 19.3 Floating-point audit notes

Current schema uses SQLAlchemy `Numeric` → Python `Decimal` — **good for determinism**.

Risks to guard in 9B:

- Never fingerprint via `float()` or pandas float intermediates for canonical values.
- NaN must not exist in canonical tables (validators enforce).
- `-0.0` vs `0.0`: normalize Decimal sign on serialization.

---

## 20. Code / schema / dependency pinning (LOCKED classification)

| Pin | REBUILD EXACT | REPROCESS | BUILD LATEST |
| --- | --- | --- | --- |
| `snapshot_id` set from manifest | **REQUIRED** | **REQUIRED** | captured at build |
| Git commit from manifest | **REQUIRED** | RECOMMENDED | recorded |
| Alembic revision from manifest | **REQUIRED** | optional (current HEAD) | recorded |
| `calendar_pin` | **REQUIRED** | **REQUIRED** | recorded |
| Python version | RECOMMENDED | RECOMMENDED | optional record |
| Dependency lock file | RECOMMENDED | RECOMMENDED | optional record |

Exact rebuild with different transformation code is **not exact** — must checkout historical Git commit (or fail loudly).

### Schema evolution (LOCKED terminology)

| Operation | Meaning |
| --- | --- |
| **EXACT HISTORICAL REBUILD** | Historical snapshots + historical Git + historical Alembic |
| **REPROCESS SNAPSHOTS** | Historical snapshots + current code/schema |

These are **different operations** — do not conflate.

---

## 21. Dependency reproducibility audit

Current state:

- `pyproject.toml` pins `pandas_market_calendars==5.4.0` only.
- `pandas`, `requests`, SQLAlchemy, etc. are **unpinned ranges**.

**9B recommendation (SHOULD):** add `requirements.lock` or pin dev/test dependencies used in CI; record lock hash in manifest 1.1 as optional `dependency_fingerprint`.

No Docker requirement.

---

## 22. Retention policy (LOCKED)

| Category | Policy |
| --- | --- |
| Snapshots referenced by successful build manifest | **Retain indefinitely, immutable** |
| Unreferenced failed-retrieval artifacts | Log separately; GC policy **deferred** (prefer retain) |
| Orphan snapshots (no manifest reference) | Audit via verify command; GC **deferred** |

---

## 23. Storage growth estimate (ballpark)

Based on current full-fetch universe:

| Contributor | Initial full snapshot (order of magnitude) | Per BUILD LATEST growth |
| --- | --- | --- |
| Tiingo 14 ETFs | **150–300 MB** JSON (varies by symbol history) | Mostly duplicate content → **dedup shrinks**; new days add ~KB–MB |
| FRED current (6 series) | **5–20 MB** | Small delta if provider revises history |
| ALFRED (4 series, full vintages) | **50–200 MB** (CPI/UNRATE vintages dominate) | New vintages add rows |
| FOMC HTML (~65 pages) | **3–8 MB** | 0–1 pages change per build |
| WTI | included in FRED | same |

**Initial footprint (first BUILD LATEST with capture): ~250–500 MB** uncompressed.

**Annual growth (weekly builds, dedup): ~50–150 MB** mostly from ALFRED vintage expansion and Tiingo new bars — highly dependent on provider revision behavior.

Local filesystem remains practical for V1 scale. Compression (§28) reduces storage ~60–80%.

---

## 24. Compression (LOCKED)

| Decision | Choice |
| --- | --- |
| Use compression | **Yes — gzip on disk (SHOULD in 9B)** |
| Content hash | **Uncompressed bytes** |
| On disk | `abc...hex.gz` or raw + flag in sidecar |
| Decompress before hash verify on read |

---

## 25. Atomic writes (LOCKED — 9B requirement)

```text
write to temp path in same directory
fsync / close
hash verify
atomic rename to content-addressed final path
write sidecar only after payload verified
```

Failed retrieval must **not** leave a valid-looking snapshot at final path.

---

## 26. Failed / empty responses (LOCKED)

| Case | Behavior |
| --- | --- |
| HTTP 401/429/500, timeout, HTML error page | **Not** canonical snapshots; diagnostic log only |
| HTTP 200 empty Tiingo list | **Build FAIL** (existing `TiingoError`) |
| HTTP 200 empty FRED observations | Source-specific validation — macro build already fails on empty ALFRED |
| Malformed snapshot before normalize | **FAIL** — do not proceed to canonical build |

---

## 27. Snapshot validation before normalize (LOCKED)

Minimum checks:

```text
hash verified
payload readable
content_type matches
expected structure (JSON parse / non-empty HTML)
not provider error page
request_identity matches expected build request
```

---

## 28. Provenance chain (LOCKED)

```text
provider / request identity
    ↓
retrieval event (retrieved_at)
    ↓
immutable snapshot (snapshot_id / sha256)
    ↓
build manifest reference
    ↓
normalization code @ Git commit
    ↓
canonical tables
    ↓
database fingerprint
```

**Per-row `snapshot_id` in canonical tables:** **NO** (LOCKED default). Dataset/build-level lineage sufficient.

---

## 29. Replay architecture (9B design)

Target separation:

```text
acquire  → bytes
snapshot → bytes (store/retrieve)
parse(bytes) → provider records
normalize(records) → canonical rows
```

### Current violations (refactor in 9B)

| Location | Issue |
| --- | --- |
| `providers/*.py` | Returns parsed JSON/list — need `fetch_bytes()` + `parse_*()` split |
| `market_data/build.py` | Calls `fetch_daily_prices()` directly — should read from snapshot adapter |
| `macro/build.py` | Same for FRED/ALFRED |
| `events/fomc.py` | Parses HTML inline after fetch — split parse from bytes |

Ideal: single normalization path whether bytes come from live fetch or snapshot store.

---

## 30. Secrets & privacy (LOCKED)

| Rule | Detail |
| --- | --- |
| Request metadata | Sanitized — no tokens |
| Snapshot payload | Preserve provider response as-is (responses should not contain our secrets) |
| Tiingo auth | Header only — never in snapshot |
| FRED api_key | Query param — strip before logging; **not in sidecar** |
| Manifest / sidecar scan | Reuse Phase 8 `scan_secrets()` patterns |
| Error messages | Truncate response text in exceptions (already ~200 chars) |

---

## 31. Future verify command (design only)

```text
python -m stockballdb.snapshots verify
```

Capabilities:

- Enumerate snapshots referenced by manifests
- Verify existence + hash
- Detect orphan snapshots / orphan metadata
- Report corruption

**9B MUST implement** basic verify; full orphan audit MAY defer.

---

## 32. Snapshot index (LOCKED)

**No SQLite/PostgreSQL index in 9B.**

Sufficient:

- Content-addressed filesystem
- Sidecar `.meta.json` per snapshot
- Manifest snapshot list
- Optional `snapshots/index.json` append-only catalog (SHOULD, not MUST)

---

## 33. Pre-Phase-9 build boundary (LOCKED)

> Builds created before Phase 9 snapshot capture **cannot** retroactively become exact-rebuild capable.

- Do **not** reconstruct historical raw payloads from current providers and pretend they were original.
- Existing Phase 8 `1.0` manifests: **`PROVENANCE-CAPABLE`**, **`NOT EXACT-REBUILD-CAPABLE`**.

First exact-rebuild-capable build = first successful BUILD LATEST after 9B snapshot capture ships.

---

## 34. Operational boundaries

| Phase | Owns |
| --- | --- |
| **9** | capture, verify, resolve, exact rebuild, fingerprint |
| **10** | when builds run, orchestration, recovery, scheduling |
| **11** | explorer UI for snapshots/provenance |

---

## 35. Architecture decision table

| Decision | Locked choice | Reason |
| --- | --- | --- |
| Payload location | Filesystem `snapshots/` (gitignored) | Portable, no large PG blobs |
| Snapshot identity | SHA-256 uncompressed bytes | Content-addressed dedup |
| Raw vs parsed | Hybrid — raw primary | Prove provider response; optional parsed preview |
| Deduplication | Same hash → one payload | Efficient; multiple retrieval events |
| Compression | gzip storage, hash uncompressed | Save disk; stable identity |
| Manifest linkage | 1.1 `snapshots[]` in build manifest | Simple; no snapshot-set abstraction |
| Exact rebuild network | **Offline — zero provider calls** | True exact rebuild |
| Equality target | Logical canonical fingerprint | Practical vs byte-identical PG |
| DB fingerprint | Per-table + database SHA-256 | Deterministic proof |
| Per-row snapshot IDs | **No** | Schema pollution; manifest sufficient |
| Pre-Phase-9 builds | Provenance only, not exact-rebuild | No retroactive fabrication |
| PostgreSQL payload table | **No** | Phase 9A finds no justification |
| Failed HTTP as snapshot | **No** | Not canonical source material |
| Election/calendar snapshots | **No** | Code/config provenance |
| HTML snapshots | **Raw HTML bytes** | Extraction is transform |
| ALFRED snapshots | Full vintage JSON | PIT requires vintages |
| Tiingo snapshots | Full JSON array | Future fields preserved |
| Pagination | Deterministic concat v1 | Stable hash across pages |
| Atomic writes | temp → verify → rename | Prevent corruption |
| REPROCESS mode | Conceptual distinction locked | Different from exact rebuild |
| Dependency lock | SHOULD for 9B | Transform reproducibility |
| Snapshot index DB | **No** | Keep simple |

---

## 36. Phase 9B implementation backlog

### MUST IMPLEMENT IN 9B

| Item | Notes |
| --- | --- |
| `snapshots/` store with content-addressed layout | Gitignore |
| SHA-256 identity on uncompressed bytes | |
| Atomic write protocol | |
| Sidecar metadata JSON | |
| Secret sanitization in metadata | |
| Provider `fetch_bytes` + `parse` refactor | Tiingo, FRED, Fed |
| BUILD LATEST: capture before normalize | All active HTTP sources |
| Manifest schema 1.1 with `snapshots[]` | |
| `database_fingerprint` computation | |
| `source_mode` live vs snapshot | |
| REBUILD EXACT entrypoint | Offline enforced |
| Missing/corrupt snapshot → hard fail | |
| `python -m stockballdb.snapshots verify` (basic) | |
| Integrate WTI (`build_wti`) into snapshot capture | |
| FOMC per-page HTML snapshots | |
| FRED/ALFRED per-series snapshots | |
| Tiingo per-symbol snapshots | |
| Tests per §37 | |
| `.gitignore` update | |

### SHOULD IMPLEMENT IN 9B

| Item | Notes |
| --- | --- |
| gzip compression on disk | |
| `build_v1` writes manifest 1.1 with snapshots | |
| Optional parsed preview sidecar | |
| `requirements.lock` + manifest fingerprint | |
| Post-build fingerprint in health/provenance display | |
| Retrieval event log separate from manifest | |

### DEFER TO PHASE 10

| Item | Notes |
| --- | --- |
| Incremental fetch + snapshot chains | |
| Orphan snapshot GC | |
| Automated scheduled BUILD LATEST | |
| Per-API-call retrieval timestamps in pipelines | |

### DEFER TO PHASE 11

| Item | Notes |
| --- | --- |
| Snapshot explorer UI | |
| Visual provenance chain browser | |

### NO ACTION

| Item | Notes |
| --- | --- |
| New canonical PostgreSQL tables for payloads | Rejected |
| Per-row snapshot_id columns | Rejected |
| Retroactive snapshots for pre-9 builds | Forbidden |
| REPROCESS SNAPSHOTS CLI | Optional — concept locked only |
| Docker reproducibility | Not required |

### 9B phasing recommendation

**Single Phase 9B** is feasible — all sources share the same snapshot store pattern; complexity is refactor + wiring, not heterogeneous storage.

Optional internal order:

```text
9B-a: snapshot store + Tiingo + manifest 1.1 + fingerprint
9B-b: FRED/ALFRED + FOMC HTML + WTI + exact rebuild CLI + tests
```

Only subdivide if implementation blocks — **not required upfront**.

---

## 37. Phase 9B test strategy (design)

| Test | Purpose |
| --- | --- |
| Identical payload → identical snapshot_id | Content addressing |
| Changed payload → different snapshot_id | Revision detection |
| Same payload twice → deduplicated storage | |
| Mutated file → verify fails | |
| Missing snapshot → exact rebuild fails | |
| Corrupt hash → exact rebuild fails | |
| Exact rebuild zero HTTP calls | Network isolation |
| Metadata contains no secrets | |
| Manifest lists all snapshots | |
| fingerprint A == fingerprint B after rebuild | End-to-end |
| Pre-9 manifest → NOT_EXACT_REBUILD_CAPABLE | |

Integration pattern:

```text
fixture provider bytes → BUILD LATEST → DB fingerprint A
clear canonical tables → REBUILD EXACT → fingerprint B
assert A == B
```

---

## 38. Phase 9A verification

| Check | Result (2026-08-29) |
| --- | --- |
| pytest | **103/103 PASS** |
| validate_v1 | **STATUS: V1 VALID** |
| health | **HEALTHY** (exit 0) |
| Canonical data modified | **No** |

---

## 39. Phase 9 / 10 boundary

Phase 9 delivers **immutable source snapshots and exact-rebuild proof**.

Phase 10 delivers **when and how builds run** — not snapshot semantics.

Phase 8 provenance (provider identity, Git, calendar pin) remains valid for all builds; Phase 9 adds **snapshot_id linkage** for post-9B builds only.

---

## 40. Phase 9B implementation record (2026-08-29)

### Delivered

| Component | Location |
| --- | --- |
| Snapshot store | `src/stockballdb/snapshots/` |
| Fingerprints | `src/stockballdb/fingerprint/` |
| Exact rebuild CLI | `python -m stockballdb.rebuild_exact` |
| Snapshot verify CLI | `python -m stockballdb.snapshots verify` |
| Fingerprint CLI | `python -m stockballdb.fingerprint` |
| Manifest 1.1 | `health/provenance.py` |
| build_v1 integration | `live_build_context` + snapshots + fingerprint |
| build_wti integration | snapshot capture for DCOILWTICO |
| Operator guide | `docs/StockBallDB_snapshots_and_rebuilds.md` |

### Verification (2026-08-29)

| Check | Result |
| --- | --- |
| pytest | **120/120 PASS** (+17 snapshot tests) |
| validate_v1 | **PASS** |
| health | **HEALTHY** |
| Fingerprint stability | **PASS** (double compute match) |
| Live BUILD LATEST + REBUILD EXACT certification | **COMPLETE** (2026-08-29) |

### Certification record (2026-08-29)

| Check | Result |
| --- | --- |
| BUILD LATEST (`build_v1`) | **PASS** |
| Manifest schema | **1.1** |
| `exact_rebuild_capable` | **true** |
| Manifest git commit | **1700ce6** (clean) |
| Snapshots captured | **91** (Tiingo 14, FRED 6, ALFRED 6, federal_reserve 65) |
| Snapshot verify | **PASS** (missing=0, corrupt=0) |
| Sidecar secret audit | **PASS** (Tiingo, FRED, ALFRED, FOMC representative) |
| REBUILD EXACT (offline) | **PASS** — zero provider calls (network guard) |
| validate_v1 (rebuild) | **PASS** |
| health (rebuild) | **HEALTHY** |
| Table fingerprints | **7/7 MATCH** |
| Database fingerprint | **MATCH** `sha256:9e474ed3105b9fbdd43b213ce36f415d3f11e804f01aa20716b3629ae7a65138` |
| Primary DB regression | validate_v1 **PASS**, health **HEALTHY**, pytest **120/120 PASS** |
| Certified manifest | `build_reports/manifest_20260829T033624-eebe4514.json` |

Post-certification fix commits (required for certification):

| Commit | Fix |
| --- | --- |
| `7794fc0` | WTI-coexistent `build_v1` stage validation + `wti_context` stage |
| `1700ce6` | Preserve snapshot references in `build_v1` manifest (**certified BUILD commit**) |
| `dd5e7c5` | `rebuild_exact` empty-DB migrate-before-truncate + dotenv load |

### Certification steps (operator)

```text
1. git commit Phase 9B implementation (clean tree)
2. export STOCKBALLDB_REBUILD_DATABASE_URL=postgresql+psycopg://.../rebuild_test
3. python -m stockballdb.build_v1   # creates manifest 1.1 + snapshots/
4. python -m stockballdb.snapshots verify --manifest build_reports/manifest_<id>.json
5. python -m stockballdb.rebuild_exact --manifest build_reports/manifest_<id>.json
6. Confirm fingerprint match + zero provider calls
```
