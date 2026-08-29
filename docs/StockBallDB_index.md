# StockBallDB — Documentation Index

**Version 0.02**  
**Date:** 2026-08-27

StockBallDB is a historical financial and market-context database. Philosophy, scope, and structure live in separate docs below. Start here when a workflow needs a reference.

## Documents

1. [StockBallDB_manifesto.md](StockBallDB_manifesto.md)  
   Why StockBallDB exists and the rules that govern it: observed vs derived data, reproducibility, providers, historical integrity, and how this project differs from MoneyBallApp.

2. [StockBallDB_universe.md](StockBallDB_universe.md)  
   Which assets and market indicators are in Version 1 scope, and how the universe may expand later.

3. [StockBallDB_schema.md](StockBallDB_schema.md)  
   Tables, grains, keys, relationships, and principal fields for the Version 1 PostgreSQL schema.

4. [StockBallDB_sources.md](StockBallDB_sources.md)  
   Where observed data comes from, how providers are selected and accessed, and how sources stay replaceable without owning the schema.

5. [StockBallDB_definitions.md](StockBallDB_definitions.md)  
   Meaning, calculation, and interpretation of fields so derived values stay unambiguous and reproducible across builds.

6. [StockBallDB_Tech_stack.md](StockBallDB_Tech_stack.md)  
   Locked technical stack for building, validating, and reproducing StockBallDB (PostgreSQL, Python, SQLAlchemy, Alembic, and related tools).

7. [StockBallDB_workflow.md](StockBallDB_workflow.md)  
   How StockBallDB is built, updated, derived, validated, and phased from project foundation through acquisition pipelines.

8. [StockBallDB_phase4a_macro_contract.md](StockBallDB_phase4a_macro_contract.md)  
   Phase 4A lock: `macro_conditions` source map, point-in-time rules, trading-day alignment, units, and unresolved fields.

9. [StockBallDB_phase5a_market_context_contract.md](StockBallDB_phase5a_market_context_contract.md)  
   Phase 5A lock: WTI / XAU/USD / DXY definitions, source evaluation, schema fit, and Phase 5B readiness.

10. [StockBallDB_phase6a_scheduled_events_contract.md](StockBallDB_phase6a_scheduled_events_contract.md)  
   Phase 6A lock: `scheduled_events` definition, PIT semantics, V1 event universe, schema fit, and Phase 6B readiness.

11. [StockBallDB_phase7a_calendar_context_contract.md](StockBallDB_phase7a_calendar_context_contract.md)  
   Phase 7A lock: `calendar_context` audit, trading_days boundary, derivation semantics, PIT classification, and Phase 7B validation requirements.

12. [StockBallDB_phase8a_validation_provenance_contract.md](StockBallDB_phase8a_validation_provenance_contract.md)  
   Phase 8A lock: whole-DB health definition, validation matrix, coverage/freshness/provenance contracts, and Phase 8B backlog.

13. [StockBallDB_phase9a_snapshot_rebuild_contract.md](StockBallDB_phase9a_snapshot_rebuild_contract.md)  
   Phase 9A lock + Phase 9B/C certification record: immutable snapshots, BUILD LATEST vs REBUILD EXACT, manifest 1.1, fingerprints, and certified rebuild proof (**Phase 9 COMPLETE**).

14. [StockBallDB_snapshots_and_rebuilds.md](StockBallDB_snapshots_and_rebuilds.md)  
   Phase 9B operator reference: snapshot storage, BUILD LATEST, verify, fingerprint, REBUILD EXACT commands (includes 2026-08-29 certification summary).

15. [StockBallDB_phase10a_operational_workflow_contract.md](StockBallDB_phase10a_operational_workflow_contract.md)  
   Phase 10A lock: operational workflow audit, dependency graph, source classification, `update` stage model, failure/recovery/concurrency contract, and 10B/10C backlog.

## Routing

| Need | Open |
| ---- | ---- |
| Purpose, principles, and operating rules | manifesto |
| Why the trading calendar starts in 1957 | manifesto |
| Which symbols / assets to collect | universe |
| Table layout, keys, and fields | schema |
| Data providers and acquisition choices | sources |
| Field-level definitions and formulas | definitions |
| Macro source/PIT contract (Phase 4A) | phase4a_macro_contract |
| Market context contract (Phase 5A) | phase5a_market_context |
| Scheduled events contract (Phase 6A) | phase6a_scheduled_events |
| Calendar context contract (Phase 7A) | phase7a_calendar_context |
| Validation & provenance contract (Phase 8A) | phase8a_validation_provenance |
| Snapshot & exact-rebuild contract (Phase 9A) | phase9a_snapshot_rebuild |
| Snapshots & rebuild operator guide (Phase 9B) | snapshots_and_rebuilds |
| Operational workflow contract (Phase 10A) | phase10a_operational_workflow |
| Languages, libraries, and tooling | Tech stack |
| Build / update / derive / validate steps | workflow |
| Development phases (0 → N) | workflow |
