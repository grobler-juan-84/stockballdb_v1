# StockBallDB — Operational Update

Operator reference for the unified incremental update command. Architecture and dependency graph: [StockBallDB_workflow.md](StockBallDB_workflow.md). Validation gates: [StockBallDB_validation.md](StockBallDB_validation.md). Snapshots: [StockBallDB_snapshots_and_rebuilds.md](StockBallDB_snapshots_and_rebuilds.md).

## Commands

```text
python -m stockballdb.update
python -m stockballdb.update --as-of YYYY-MM-DD
python -m stockballdb.update --json
```

| Flag | Meaning |
| --- | --- |
| `--as-of` | Deterministic build boundary (default: today in America/New_York). Does **not** replay historical provider state; live sources return current material bounded to this date. |
| `--json` | Machine-readable run report on **stdout**; human progress on **stderr**. |

V1 update does **not** expose dry-run, status-only, per-stage, or `--resume` switches.

## Exit codes

| Code | Meaning |
| --- | --- |
| `0` | `SUCCESS_UPDATED` or `SUCCESS_NO_CHANGE` |
| `1` | Operational failure (stage, validation, health, internal) |
| `2` | Preflight / configuration failure |
| `3` | Concurrent update refused (advisory lock held) |

## Workflow

```text
preflight → advisory lock → fingerprint_before → UPDATE_STAGES → validate_v1 → health → fingerprint_after → manifest (success only)
```

Operational stages (**no** `migrate`):

```text
trading_days → daily_market_data → derive_market_data → market_outcomes → asset_regimes → wti_context → macro_conditions → scheduled_events → calendar_context
```

Every run writes `build_reports/run_<run_id>.json`. Successful runs also write Manifest 1.1 under `build_reports/manifest_<run_id>.json`. Snapshot capture is mandatory for mutable HTTP sources on update (same preserve-then-normalize path as build).

## FULL-REFETCH-BY-DESIGN

Mutable HTTP sources (Tiingo ETFs, WTI, FRED/ALFRED, Fed FOMC HTML) are **full-refetched** each update — not append-only tails. Providers may revise past values; StockBallDB absorbs revisions via refetch + upsert/replace.

Derived market tables (`derive_market_data`, `market_outcomes`, `asset_regimes`) are **full-symbol recomputed** (drawdown from inception, forward horizons, expanding volatility windows). See [workflow](StockBallDB_workflow.md).

## Preflight

Before any provider acquisition or canonical writes:

- `DATABASE_URL` configured and reachable
- Alembic revision equals code head (**no auto-migrate** in `update`)
- Required provider credentials present
- `build_reports/` and snapshot store writable
- Primary `DATABASE_URL` must not target the same database as `STOCKBALLDB_REBUILD_DATABASE_URL` when both are set
- Non-empty `trading_days` (bootstrap with `python -m stockballdb.build_v1` first)

Dirty git working tree is allowed for `update`. Clean tree is required for certified `rebuild_exact` (see snapshots doc).

## Provider success requirement

All required live providers for the run must succeed (Tiingo for each of the 14 ETFs, FRED/ALFRED series used by macro/events, Fed FOMC HTML pages, WTI). Skipping a required source is **FAILED**, not `SUCCESS_UPDATED` / `SUCCESS_NO_CHANGE`.

Typical HTTP budgets (implementation): Tiingo ~120s / 0 retries; FRED ~120s / 4 retries; Fed HTML ~90s / 5 retries. Exhausted retries → stage failure.

## Concurrency

PostgreSQL advisory lock prevents overlapping updates. If the lock is held, exit **3**.

## Success classification

| Condition | Result |
| --- | --- |
| `fingerprint_before == fingerprint_after` | `SUCCESS_NO_CHANGE` |
| `fingerprint_before != fingerprint_after` | `SUCCESS_UPDATED` |

## Failure & recovery

- Partial stage commits may remain; run is marked **FAILED**
- No success manifest on failure
- Fix cause and **rerun** `python -m stockballdb.update` (no `--resume`)
- `trading_days` sync may use multiple transactions (delete out-of-range then upsert); an interrupted spine sync can leave a damaged calendar — recover by full successful rerun
- Catastrophic recovery: `python -m stockballdb.rebuild_exact` (see [snapshots_and_rebuilds](StockBallDB_snapshots_and_rebuilds.md))

## Health gate

Unlike `build_v1`, **`update` fails** when health status is **UNHEALTHY**. **HEALTHY** and **HEALTHY WITH WARNINGS** succeed. INFO findings (e.g. expected WTI lag) do not fail the run. Expected provider lag must not fail the update solely as lag.

## Bootstrap vs update

| Situation | Command |
| --- | --- |
| Empty / new database | `python -m stockballdb.build_v1` (includes migrate) |
| Established StockBallDB routine refresh | `python -m stockballdb.update` |

## Test database boundary

| Variable | Role |
| --- | --- |
| `DATABASE_URL` | Primary / normal StockBallDB (operational + read-only checks) |
| `STOCKBALLDB_TEST_DATABASE_URL` | Separate disposable PostgreSQL DB for **mutating** pytest integration tests |

Rules:

- Mutating integration tests use **only** `STOCKBALLDB_TEST_DATABASE_URL`.
- They **never** fall back to `DATABASE_URL`. If the test URL is unset, those tests **skip**.
- If the test URL identifies the same host/port/database as `DATABASE_URL` (credentials ignored), the tests **refuse** to run.
- Read-only tests may still use `DATABASE_URL`.
- Canonical primary refresh remains: `python -m stockballdb.update`

## Related commands

```text
python -m stockballdb.validate_v1
python -m stockballdb.health
python -m stockballdb.fingerprint
python -m stockballdb.snapshots [--manifest build_reports/manifest_<run_id>.json]
python -m stockballdb.rebuild_exact --manifest build_reports/manifest_<run_id>.json
python -m stockballdb.explorer
```
