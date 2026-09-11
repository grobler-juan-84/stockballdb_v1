# StockBallDB — Documentation Index

StockBallDB is a **historical financial and market-context database**: acquisition, source preservation, normalization, deterministic derivation, validation, provenance, updates, reproducibility, and PostgreSQL storage.

It is **not** an experiment, strategy, prediction, or trading-decision system.

Start here when you need the right document. Git history is the archive of how V1 was built; these docs describe **how StockBallDB works now**.

## Canonical documents

| Document | Responsibility |
| -------- | -------------- |
| [StockBallDB_V1_status.md](StockBallDB_V1_status.md) | V1 scope, completed foundation, certified baseline snapshot, boundaries, remaining closeout |
| [StockBallDB_manifesto.md](StockBallDB_manifesto.md) | Purpose, boundaries, PIT philosophy, provenance, reproducibility, architectural principles |
| [StockBallDB_universe.md](StockBallDB_universe.md) | Implemented symbols and unresolved candidates (XAU/USD, DXY) |
| [StockBallDB_schema.md](StockBallDB_schema.md) | Seven canonical tables, grains, keys, row-shape constraints |
| [StockBallDB_sources.md](StockBallDB_sources.md) | Providers, series maps, PIT/source limitations, date floors |
| [StockBallDB_definitions.md](StockBallDB_definitions.md) | Field meanings, formulas, derivation and semantic rules |
| [StockBallDB_Tech_stack.md](StockBallDB_Tech_stack.md) | PostgreSQL / Python / pandas / SQLAlchemy / Alembic / pytest / Streamlit stack |
| [StockBallDB_workflow.md](StockBallDB_workflow.md) | Lifecycle, dependency graph, build vs update vs exact rebuild |
| [StockBallDB_validation.md](StockBallDB_validation.md) | validate_v1, health, severity, fingerprint, provenance, certification baseline |
| [StockBallDB_snapshots_and_rebuilds.md](StockBallDB_snapshots_and_rebuilds.md) | Snapshot identity, Manifest 1.1, exact rebuild, operator commands |
| [StockBallDB_operational_update.md](StockBallDB_operational_update.md) | Safe `python -m stockballdb.update`, locks, gates, recovery |
| [StockBallDB_explorer.md](StockBallDB_explorer.md) | Read-only Explorer: architecture, six pages, safety, certification |

## Routing

| Need | Open |
| ---- | ---- |
| V1 status / what is in or out of V1 | V1_status |
| Why StockBallDB exists / operating rules | manifesto |
| Which symbols are implemented vs unresolved | universe |
| Table layout, keys, constraints | schema |
| Providers and acquisition limitations | sources |
| Formulas and field semantics | definitions |
| Languages and libraries | Tech stack |
| Build / update / rebuild lifecycle | workflow |
| Health, validate_v1, fingerprint, certification | validation |
| Snapshots and exact rebuild | snapshots_and_rebuilds |
| Day-to-day update operations | operational_update |
| Local read-only inspection UI | explorer |
