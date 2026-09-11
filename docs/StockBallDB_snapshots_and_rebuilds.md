# StockBallDB — Snapshots & Exact Rebuild

**Canonical** snapshot identity, storage, BUILD LATEST / REBUILD EXACT, manifests, and fingerprint rules.

Companions: [validation](StockBallDB_validation.md) · [workflow](StockBallDB_workflow.md) · [operational update](StockBallDB_operational_update.md) · [sources](StockBallDB_sources.md)

---

## Snapshot definition

A **source snapshot** is an **immutable, content-addressed representation of source material received (or deterministically used) by an acquisition/build run, captured before canonical normalization**.

| Property | Rule |
| --- | --- |
| Mutability | Written once; never edited or overwritten |
| Identity | SHA-256 of **uncompressed** payload bytes |
| `snapshot_id` | `sha256:` + lowercase hex digest |
| Metadata in hash? | **No** — retrieval time, build_id, headers are not part of identity |
| Location | Filesystem only — **not** PostgreSQL |
| Role vs manifests | Manifests reference snapshots; snapshots may be reused across builds (dedup) |

**Hybrid storage (locked):**

```text
PRIMARY   = immutable raw provider payload bytes
METADATA  = sidecar JSON (request identity, retrieval event, hash, paths)
OPTIONAL  = parsed preview for inspection only — never identity
```

Normalization in BUILD LATEST **must consume the preserved snapshot bytes**, not a discarded in-memory twin.

---

## Storage layout

Gitignored root `snapshots/` (never commit payloads):

```text
snapshots/
  sha256/
    ab/
      <full64hex>.gz          # gzip on disk; hash is of uncompressed bytes
      <full64hex>.meta.json   # sidecar — does not affect content identity
```

Two-char shard prefix avoids huge flat directories. Relative paths in manifests stay portable.

**Atomic write:** temp path → verify SHA-256 → rename to content-addressed final path → write sidecar only after payload verified. Failed retrieval must not leave a valid-looking final object.

**Sidecar `.meta.json` (required fields include):** `snapshot_id`, `sha256`, `provider`, `source_identifier`, `source_type`, `retrieved_at`, `content_type`, `byte_size`, `encoding`, `request_identity`, `payload_path` (plus pagination metadata when applicable).

**Pre-normalize checks:** hash OK; payload readable; content-type/structure plausible; not an error page; `request_identity` matches the intended request.

**Not a canonical snapshot:** failed HTTP (4xx/5xx/timeout) and obvious error HTML — diagnostic only; do not treat as authoritative payload. Empty Tiingo `200` JSON list is a **build FAIL**, not an empty successful snapshot.

**Retention:** snapshots referenced by a successful Manifest 1.1 are retained indefinitely (immutable). Do not prune objects still referenced by capable manifests.

**Secrets:** never in sidecars or manifests (no API keys, Authorization headers, authenticated URLs, DB credentials). Sanitize `request_identity` and reuse secret-scan patterns.

---

## Content identity & integrity

| Decision | Choice |
| --- | --- |
| Algorithm | SHA-256 |
| Hashed material | Original **uncompressed** source bytes |
| Deduplication | Identical bytes → same `snapshot_id`; separate retrieval events may share one object |
| Mutation | Re-hash on read; mismatch → **corruption / FAIL** |
| Provider revision | Same request identity + different bytes → **two** immutable snapshots, both retained |

---

## What is snapshotted

| Source | Granularity | Payload |
| --- | --- | --- |
| Tiingo (14 ETFs) | One snapshot per symbol | Full JSON array as returned |
| FRED current | One snapshot per series | Full current-vintage observations JSON |
| ALFRED | One snapshot per series | Full vintage-window JSON including `realtime_start` / `realtime_end` |
| FOMC historical / calendar | One snapshot per HTML page | Raw HTML bytes (UTF-8) |
| WTI (`build_wti`) | One snapshot (`DCOILWTICO`) | Same as FRED current |

### Pagination (`full_concat_v1`)

Multi-page FRED/ALFRED bodies are concatenated in ascending offset order with separator:

```text
---STOCKBALLDB_PAGE_BOUNDARY---
```

Sidecar / request identity records `pagination: "full_concat_v1"`. Hash is over the concatenated uncompressed bytes.

### Not snapshotted

| Source | Exact-rebuild needs |
| --- | --- |
| Election days | Git commit + statutory generation code |
| NYSE trading calendar | `calendar_pin` (`pandas_market_calendars==5.4.0`) + date range + code at commit |
| Derived tables | Upstream snapshots + code |

Do **not** invent fake snapshot files for deterministic sources. **No per-row `snapshot_id`** in canonical tables — build/manifest lineage is sufficient.

---

## Build modes

### BUILD LATEST

```text
network → bytes → gzip snapshot → normalize FROM snapshot → validate → fingerprint → manifest 1.1
```

Operator:

```text
python -m stockballdb.build_v1
python -m stockballdb.build_wti
```

### REBUILD EXACT

```text
manifest 1.1 → resolve snapshots → verify hashes → offline normalize → validate → fingerprint match
```

| Condition | Result |
| --- | --- |
| Missing snapshot | **FAIL** — no provider fetch |
| Hash mismatch | **FAIL** — corruption |
| Schema 1.0 / no snapshots | **FAIL** — `NOT_EXACT_REBUILD_CAPABLE` |
| Silent provider fallback | **FORBIDDEN** |

Operator:

```text
python -m stockballdb.rebuild_exact --manifest build_reports/manifest_<id>.json \
  --database-url postgresql+psycopg://.../stockballdb_rebuild_test
```

Requirements:

- Manifest schema **1.1** with `exact_rebuild_capable: true`
- All referenced snapshots present and hash-valid
- Matching **git commit** from manifest (checkout required)
- Matching **Alembic head**
- **Clean working tree** (or `--allow-dirty` — non-certified)
- Prefer `--database-url` / `STOCKBALLDB_REBUILD_DATABASE_URL` over production `DATABASE_URL`

### EXACT HISTORICAL REBUILD ≠ REPROCESS SNAPSHOTS

| Operation | Meaning |
| --- | --- |
| **EXACT HISTORICAL REBUILD** | Historical snapshots + historical Git + historical Alembic |
| **REPROCESS SNAPSHOTS** | Historical snapshots + **current** code/schema |

Do not conflate these.

---

## Manifests

| Schema | Capability |
| --- | --- |
| **1.0** | Provenance only — **NOT** exact-rebuild capable |
| **1.1** | Snapshot list + `database_fingerprint`; exact-rebuild when capable |

Manifest **1.1** includes (among other build provenance): `snapshot_capture`, `snapshots[]`, `database_fingerprint`, and `exact_rebuild_capable`.

`exact_rebuild_capable` is **true** when there are **≥23 API snapshots** and validation **PASS**.

**Pre-Phase-9 builds** cannot become exact-rebuild capable retroactively. Do not fabricate historical raw payloads from today’s providers.

---

## Database fingerprint

Deterministic logical equality of the **seven canonical tables** (not PostgreSQL cluster bytes).

```text
python -m stockballdb.fingerprint
```

Rules:

1. Tables in alphabetical name order.
2. Columns alphabetical; rows ordered by primary key ascending.
3. Serialize rows as `col1|col2|...|colN\n`; NULL as `\N`; dates as `YYYY-MM-DD`.
4. Numerics via **Decimal** from the DB driver — **never float**. Format with `format(d, 'f')`; strip trailing zeros but keep at least one decimal place for integer-like numerics; normalize `-0.0` → `0.0`.
5. Per-table hash = SHA-256 of UTF-8 serialized rows.
6. `database_fingerprint` = `sha256:` + SHA-256 of `table_name:table_hash\n` lines in table order.

Stored on successful 1.1 manifests; REBUILD EXACT must match.

---

## Operator commands

```text
python -m stockballdb.build_v1
python -m stockballdb.build_wti
python -m stockballdb.snapshots
python -m stockballdb.snapshots --manifest build_reports/manifest_<id>.json
python -m stockballdb.fingerprint
python -m stockballdb.rebuild_exact --manifest build_reports/manifest_<id>.json --database-url ...
```

`python -m stockballdb.snapshots` exits non-zero on missing, corrupt, or invalid metadata.

---

## Historical certification note

Phase 9 once certified live BUILD LATEST + offline REBUILD EXACT with fingerprint match  
`sha256:9e474ed3105b9fbdd43b213ce36f415d3f11e804f01aa20716b3629ae7a65138`.

That value is **historical proof of the rebuild path**, **not** the current database identity.

**Current certified fingerprint:**  
`sha256:5055ae10f216ff33141eb137fc396ce29481e896c3ea828983e4ca8b12291aca`  
(after later data/code updates).
