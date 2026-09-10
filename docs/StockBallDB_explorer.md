# StockBallDB Explorer — Operator Guide

**Phase 11** — local, read-only inspection UI for the certified StockBallDB database.  
**Status:** Phase 11C CERTIFIED; **Phase 11D IMPLEMENTED — MANUAL CERTIFICATION PENDING** (desktop UI refresh).

## Desktop UI (Phase 11D)

- Wide layout (`layout="wide"`), top navigation, compact application header
- Shared presentation helpers under `src/stockballdb/explorer/ui/`
- Theme: `.streamlit/config.toml` + narrow CSS in `explorer/ui/css.py`
- Visual contract: [StockBallDB_phase11d_explorer_desktop_ui_contract.md](StockBallDB_phase11d_explorer_desktop_ui_contract.md)

## Install

Explorer requires Streamlit (included in project dependencies):

```bash
pip install -e .
# or
pip install -r requirements.txt
```

## Launch

From the project root:

```bash
python -m stockballdb.explorer
```

Streamlit binds to **localhost** only. The app opens in your browser with six areas:

| Page | Purpose |
| --- | --- |
| Control Center | Health, diagnostics, latest manifest/run, on-demand fingerprint |
| Data Explorer | Paginated table browse with filters and optional CSV export |
| Day Inspector | Cross-table view for one calendar date (+ optional symbol) |
| Coverage Explorer | Table/symbol coverage, freshness, gap findings |
| Provenance Explorer | Manifests, run reports, snapshot metadata (no credentials) |
| Validation Center | On-demand health, validate_v1, fingerprint, manifest verify |

Use **Refresh** in the sidebar to invalidate cached data after external changes.

## Configuration

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | Primary PostgreSQL URL (default when Explorer URL unset) |
| `STOCKBALLDB_EXPLORER_DATABASE_URL` | Optional dedicated read-only connection URL |

Explorer uses a **separate SQLAlchemy engine** from build/update workflows. Each connection attempts `SET TRANSACTION READ ONLY` on PostgreSQL.

Explorer constants (`DEFAULT_PAGE_SIZE=100`, `MAX_PAGE_SIZE=500`, CSV export cap `10_000`) live in `stockballdb.explorer.config`.

## Read-only guarantee

- Query layer uses parameterized SQLAlchemy `select()` only — table and column names come from an explicit registry allowlist.
- No INSERT, UPDATE, DELETE, TRUNCATE, DROP, or ALTER in the Explorer package.
- No raw SQL console, no update/rebuild triggers, no schema mutation.
- Artifacts and manifests are scanned for secret-like keys before display; URLs and credentials are never shown.

## Optional PostgreSQL read-only role (document only)

StockBallDB does **not** create this role automatically. For production-style separation, a DBA may grant read-only access:

```sql
CREATE ROLE stockballdb_explorer LOGIN PASSWORD 'choose-a-strong-password';
GRANT CONNECT ON DATABASE your_db TO stockballdb_explorer;
GRANT USAGE ON SCHEMA public TO stockballdb_explorer;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO stockballdb_explorer;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT SELECT ON TABLES TO stockballdb_explorer;
```

Then set:

```bash
STOCKBALLDB_EXPLORER_DATABASE_URL=postgresql+psycopg://stockballdb_explorer:PASSWORD@host:5432/your_db
```

## Related docs

- [StockBallDB_phase11a_explorer_contract.md](StockBallDB_phase11a_explorer_contract.md) — authoritative Explorer contract (§27 Phase 11C certification)
- [StockBallDB_phase11d_explorer_desktop_ui_contract.md](StockBallDB_phase11d_explorer_desktop_ui_contract.md) — Phase 11D desktop UI refresh
- [StockBallDB_operational_update.md](StockBallDB_operational_update.md) — operational update (not available from Explorer)
