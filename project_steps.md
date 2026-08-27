# StockBallDB — Project Steps

## Step 1 — Commit and push documentation updates

Committed and pushed tech stack, schema/definitions/sources/manifesto updates for raw vs adjusted market data, and ownership research notes to GitHub `main`.

## Step 2 — Plan Phase 0 foundation

Inspected the documentation-only repo and produced an approved Phase 0 plan: `src/stockballdb` package, config/logging/DB health check, Alembic scaffold, pytest, README — no schema tables yet.

## Step 3 — Implement Phase 0 project foundation

Created the Python package scaffold (`config`, `db`, `logging_config`, `check_db`), `requirements.txt`, `pyproject.toml`, Alembic (empty versions), pytest suite, `.gitignore`, `.env.example`, README, and updated `docs/StockBallDB_index.md`. Install and unit tests passed; live DB check was blocked pending `.env`.

## Step 4 — Catch up project_steps and verify Phase 0

Added `project_steps.md` per the project-steps rule (backfilling prior work). With local `.env` configured, re-ran Phase 0 verification: `check_db` SUCCESS, Alembic online, pytest green including DB integration after loading dotenv in the connection test.

## Step 5 — Add phase-summary Cursor rule

Created `.cursor/rules/phase-summary-rule.mdc` (`alwaysApply`) to keep `phase_history.md` updated during phases and close each phase with Done / Problems / Remember. Seeded `phase_history.md` with completed Phase 0.

## Step 6 — Phase 1A trading_days design

Produced and locked the Phase 1A design: `pandas_market_calendars` NYSE authority, keep all 15 fields, ISO week/weekday, NULL prev/next edges, generate/upsert/validate pipeline — no other tables yet.

## Step 7 — Implement Phase 1 trading_days

Implemented model + Alembic migration, NYSE calendar build/validate CLI, docs updates, and verification (17,531 rows; pytest 13 passed). Sync now deletes out-of-range dates for idempotent rebuilds.

## Step 8 — Confirm rebuild and pytest success

Background verification finished successfully: trading_days rebuild SUCCESS and pytest 13/13 passed.

## Step 9 — Implement Phase 2A daily_market_data

Added `daily_market_data` migration and Tiingo pipeline for 14 ETFs; stored observed OHLCV + corp actions; left derived fields NULL. Verified 89,404 rows, idempotent rebuild, pytest 19/19; updated docs and phase history.

## Step 10 — Phase 2B derived-field definition investigation

Investigated raw vs adjusted bases using live ETF dividend/split examples. Produced recommendations for the five derived columns and corp-action 0/1 interpretation; no derivation implemented pending approval.

## Step 11 — Implement Phase 2B derivation

Locked approved formulas in docs; added `derive_daily_market_data` CLI; populated derived columns for all 14 ETFs (89,404 rows); validated QQQ split and SPY dividend behavior; pytest 23/23.

## Step 12 — Phase 2C market_outcomes definition investigation

Investigated forward-outcome conventions on live ETF data (close-close vs open-entry, max excursion, horizon completeness, look-ahead). Produced recommendations only — no `market_outcomes` table or migration.

## Step 13 — Implement Phase 2C market_outcomes

Locked approved outcome definitions in docs; added model + Alembic migration; built `market_outcomes` from `daily_market_data` only (89,404 rows, 14 ETFs); validated horizons/NULLs/consistency/idempotency; pytest 27/27. Stopped before `asset_regimes`.

## Step 14 — Phase 2D asset_regimes definition investigation

Investigated point-in-time `asset_regimes` field definitions on live ETF data (trailing returns, SMAs, vol, drawdown, regime labels). Recommendations only — no table, migration, or data changes.

## Step 15 — Implement Phase 2D asset_regimes

Locked approved definitions in docs; added model + Alembic migration; built `asset_regimes` from `daily_market_data` only (89,404 rows, 14 ETFs); validated NULL boundaries, drawdown identity, PIT vol regimes, idempotency; pytest 36/36. Stopped before `macro_conditions`.

## Step 16 — Phase 2E macro_conditions definition investigation

Investigated FRED/ALFRED series IDs, revision/PIT rules, release alignment, PMI reproducibility, credit-spread and regime options using live API metadata. Recommendations only — no `macro_conditions` table or data changes.

## Step 17 — Note stale FRED probe failure notification

Initial heavy FRED metadata script timed out; leaner retry already succeeded and fed the Phase 2E investigation. No further action required from that failure.

## Step 18 — Implement Phase 2E macro_conditions

Locked approved FRED/ALFRED series (pmi deferred); inflation_regime uses distinct PIT releases; built `macro_conditions` 1:1 with `trading_days` (17,531 rows); validated PIT/alignment/regimes; pytest 47/47. Stopped before `scheduled_events`.

## Step 19 — Phase 2F scheduled_events investigation

Investigated V1 scope/semantics for `scheduled_events` against Fed/BLS/FRED/ALFRED/election/earnings sources. Recommended KEEP FOMC/CPI/employment_situation/election; DEFER earnings and consensus surprise fields; schema CHANGE vs draft actual/expected/event_window. No table, migration, or data changes.

## Step 20 — Implement Phase 2F scheduled_events

Locked approved occurrence-calendar schema; added model + Alembic `e5c83b2d4a16`; built FOMC/CPI/employment/election loaders and CLI; loaded 2,613 rows; pytest 58/58. Stopped before `calendar_context`.

## Step 21 — Phase 2G calendar_context investigation

Investigated V1 `calendar_context` using live trading_days/scheduled_events and pandas_market_calendars early-close/adhoc evidence. Recommended schema CHANGE: keep holiday/session/week + narrow transitions; event-day + days_since only; DEFER forward event distances, tax/payday/earnings windows. No table or migration.

## Step 22 — Implement Phase 2G calendar_context

Locked approved schema; added model + Alembic `f6d94c3e5b27`; derived 17,531 rows 1:1 with trading_days from NYSE metadata + scheduled_events; pytest 71/71. All seven original V1 canonical tables complete.

## Step 23 — Phase 3A V1 integration investigation

Audited build CLIs, upsert semantics, credentials, and cross-table dependencies. Recommended `build_v1` orchestrator + `validate_v1`, empty-DB contract, fail-fast policy, and structural vs snapshot reproducibility distinction. No runner implemented.

## Step 24 — Implement Phase 3B V1 integration & reproduction

Implemented `build_v1` / `validate_v1` orchestration (`v1/preflight|stages|report`), whole-DB invariants, docs, and tests. Fresh proof on `stockballdb_v1_rebuild` (Run1+Run2 idempotent, validate PASS); working `stockballdb` untouched; pytest 84/84; version left at `0.0.1` (no tag).

## Step 25 — Confirm background build/validate task results

Acknowledged completed shell tasks: Run1 `build_v1`, Run2 idempotent rebuild, and `validate_v1` on `stockballdb_v1_rebuild` all succeeded (already covered in Step 24). No further code changes.

## Step 26 — Stamp StockBallDB V1.0.0

Bumped package/project version to `1.0.0` (`pyproject.toml`, `stockballdb.__version__`); updated README, `phase_history.md` V1 freeze milestone, workflow §12 title. pytest 84/84; Git tag `v1.0.0` not created (V1 codebase not yet committed to git).

## Step 27 — Confirm V1.0.0 verification run

Post-stamp `pip install -e .` reported package `1.0.0`; pytest **84/84 PASS**. Git tag `v1.0.0` still pending commit of full V1 codebase.

## Step 28 — Finalize V1.0.0 Git snapshot

Staged accepted V1 tree (secrets audit PASS; `.env`/`build_reports/` excluded); commit `700424c` `release: StockBallDB v1.0.0`; annotated tag `v1.0.0` created locally; nothing pushed.
