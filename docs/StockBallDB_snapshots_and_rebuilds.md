# StockBallDB — Snapshots & Exact Rebuild (Operator Reference)

**Phase 9B** operational guide. Architecture details: [Phase 9A contract](StockBallDB_phase9a_snapshot_rebuild_contract.md).

---

## What snapshots are

Immutable, content-addressed copies of **raw provider bytes** captured during `BUILD LATEST`. Identity = `SHA-256(uncompressed bytes)`.

```text
snapshots/sha256/ab/<digest>.gz
snapshots/sha256/ab/<digest>.meta.json
```

Snapshots are **gitignored** — never commit them.

---

## BUILD LATEST

```text
python -m stockballdb.build_v1
```

During provider-backed stages:

```text
network fetch → bytes → gzip snapshot → read back from snapshot → parse → normalize
```

On success writes `build_reports/manifest_<build_id>.json` with:

```text
schema_version: "1.1"
snapshot_capture: true
exact_rebuild_capable: true   (when ≥23 API snapshots + validation PASS)
database_fingerprint
snapshots[]
```

WTI (separate pipeline):

```text
python -m stockballdb.build_wti
```

Also captures a FRED `DCOILWTICO` snapshot when run inside build context.

**Not snapshotted:** elections (statutory), NYSE calendar (pinned library + code).

---

## Verify snapshots

```text
python -m stockballdb.snapshots verify
python -m stockballdb.snapshots verify --manifest build_reports/manifest_<id>.json
```

Exit non-zero on missing/corrupt/invalid metadata.

---

## Database fingerprint

```text
python -m stockballdb.fingerprint
```

Deterministic SHA-256 over all seven canonical tables (PK-ordered rows, alphabetical columns, `Decimal` serialization).

---

## REBUILD EXACT

```text
python -m stockballdb.rebuild_exact --manifest build_reports/manifest_<id>.json \
  --database-url postgresql+psycopg://.../stockballdb_rebuild_test
```

Requirements:

- Manifest schema **1.1** with `exact_rebuild_capable: true`
- All referenced snapshots present and hash-valid
- **Git commit** matches manifest (checkout required)
- **Alembic head** matches
- **Clean working tree** (unless `--allow-dirty` — non-certified)
- **Zero provider network calls** (enforced)

Compares rebuilt `database_fingerprint` to manifest target. Mismatch = hard fail.

**Safety:** Prefer `STOCKBALLDB_REBUILD_DATABASE_URL` or `--database-url` over production `DATABASE_URL`. Use `--force-same-database` only when intentional.

---

## Pre-Phase-9 manifests

Schema **1.0** manifests remain **provenance-capable** but **NOT exact-rebuild-capable**. `rebuild_exact` refuses them.

---

## Phase boundaries

| Phase | Scope |
| --- | --- |
| **9** | Snapshot capture, verify, fingerprint, exact rebuild |
| **10** | Scheduled builds, orchestration, incremental fetch |
| **11** | Explorer UI |
