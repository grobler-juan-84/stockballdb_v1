# StockBallDB — Documentation Index

StockBallDB is a **historical financial and market-context database**: acquisition, source preservation, normalization, deterministic derivation, validation, provenance, updates, reproducibility, and PostgreSQL storage.

It is **not** an experiment, strategy, prediction, or trading-decision system.

Start here when you need the right document. Git history is the archive of how V1 was built; these docs describe **how StockBallDB works now**, plus V2 planning authorities.

## Documentation model

StockBallDB uses a **Canonical + historical + V2 working** documentation model:

| Layer | Role |
| ----- | ---- |
| **Canonical** | Current-system authorities. Change only when the implemented system changes. |
| **Historical / version** | Certified baselines preserved as history (do not rewrite). |
| **V2 working / governance** | Scope, decisions, progress, and deferred ideas during V2 development. |

## Canonical documents (current system)

| Document | Responsibility |
| -------- | -------------- |
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

## Historical / version documents

| Document | Responsibility |
| -------- | -------------- |
| [StockBallDB_V1_status.md](StockBallDB_V1_status.md) | **Certified V1 baseline** — V1 scope, completed foundation, certification snapshot, boundaries, deferred items |

A future `StockBallDB_V2_status.md` will be created only when V2 reaches certification.

## V2 working / governance documents

| Document | Responsibility |
| -------- | -------------- |
| [StockBallDB_V2_scope.md](StockBallDB_V2_scope.md) | **Authoritative V2 scope** — inspection/management boundary vs research/experiment |
| [StockBallDB_V2_decisions.md](StockBallDB_V2_decisions.md) | **V2 decision log** — locked/proposed decisions, rationale, consequences |
| [StockBallDB_V2_architecture.md](StockBallDB_V2_architecture.md) | **V2 architecture** — façade, React↔FastAPI localhost HTTP, Electron desktop runtime, frontend tiers |
| [StockBallDB_V2_progress.md](StockBallDB_V2_progress.md) | **Current V2 progress / status** — roadmap, completed, next |
| [StockBallDB_future.md](StockBallDB_future.md) | **Deferred beyond V2** — research/experiment and other parked ideas (not promised) |

## Routing

| Need | Open |
| ---- | ---- |
| V1 certified baseline / what is in or out of V1 | V1_status |
| V2 scope / what V2 may and may not do | V2_scope |
| V2 decisions (locked vs proposed) | V2_decisions |
| V2 backend / application / React communication architecture | V2_architecture |
| Where V2 stands / roadmap / next task | V2_progress |
| Deferred research or post-V2 ideas | future |
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
| Local read-only inspection UI (V1 Explorer) | explorer |
