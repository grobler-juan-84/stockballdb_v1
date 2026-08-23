# StockBallDB — Documentation Index

**Version 0.01**  
**Date:** 2026-08-23

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

## Routing

| Need | Open |
| ---- | ---- |
| Purpose, principles, and operating rules | manifesto |
| Why the trading calendar starts in 1957 | manifesto |
| Which symbols / assets to collect | universe |
| Table layout, keys, and fields | schema |
| Data providers and acquisition choices | sources |
| Field-level definitions and formulas | definitions |
| Build / update / derive / validate steps | workflow *(planned)* |
