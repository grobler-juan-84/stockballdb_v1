# StockBallDB — Operational Update (Phase 10B)

Concise operator reference for the unified update command. The authoritative contract is [`StockBallDB_phase10a_operational_workflow_contract.md`](StockBallDB_phase10a_operational_workflow_contract.md).

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

Operational stages (no `migrate`):

```text
trading_days → daily_market_data → derive_market_data → market_outcomes → asset_regimes → wti_context → macro_conditions → scheduled_events → calendar_context
```

Every run writes `build_reports/run_<run_id>.json`. Successful runs also write Manifest 1.1 under `build_reports/manifest_<run_id>.json`.

## Preflight

Before any provider acquisition or canonical writes:

- `DATABASE_URL` configured and reachable
- Alembic revision equals code head (**no auto-migrate**)
- Required provider credentials present
- `build_reports/` and snapshot store writable
- Primary `DATABASE_URL` must not target the same database as `STOCKBALLDB_REBUILD_DATABASE_URL` when both are set
- Non-empty `trading_days` (bootstrap with `python -m stockballdb.build_v1` first)

## Success classification

| Condition | Result |
| --- | --- |
| `fingerprint_before == fingerprint_after` | `SUCCESS_NO_CHANGE` |
| `fingerprint_before != fingerprint_after` | `SUCCESS_UPDATED` |

## Failure & recovery

- Partial stage commits may remain; run is marked **FAILED**
- No success manifest on failure
- Fix cause and rerun `python -m stockballdb.update` (no `--resume`)
- Catastrophic recovery: Phase 9 `python -m stockballdb.rebuild_exact`

## Health gate

Unlike `build_v1`, **`update` fails** when health status is **UNHEALTHY**. **HEALTHY** and **HEALTHY WITH WARNINGS** succeed. INFO findings (e.g. expected WTI lag) do not fail the run.

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

- Mutating integration tests (`tests/test_trading_days_db.py`, `tests/test_daily_market_data_db.py`) use **only** `STOCKBALLDB_TEST_DATABASE_URL`.
- They **never** fall back to `DATABASE_URL`. If the test URL is unset, those tests **skip**.
- If the test URL identifies the same host/port/database as `DATABASE_URL` (credentials ignored), the tests **refuse** to run.
- Read-only tests may still use `DATABASE_URL`.
- Canonical primary refresh remains: `python -m stockballdb.update`

## Related commands

```text
python -m stockballdb.validate_v1
python -m stockballdb.health
python -m stockballdb.fingerprint
python -m stockballdb.snapshots --manifest build_reports/manifest_<run_id>.json
python -m stockballdb.rebuild_exact --manifest build_reports/manifest_<run_id>.json
```

## Certification (Phase 10C)

Certified **2026-08-30** on implementation commit `77906f3` (fix `71ee638` for `--json` logging).

Authoritative certification record: [`StockBallDB_phase10a_operational_workflow_contract.md`](StockBallDB_phase10a_operational_workflow_contract.md) §27.

Certified operational manifest: `build_reports/manifest_20260830T021244-06a37e08.json` (91 snapshots; `exact_rebuild_capable=true`; rebuild_exact **7/7** fingerprint match on dedicated rebuild DB).
