# StockBallDB — Validation, Health & Provenance

Canonical reference for whole-database validation, health reporting, severity semantics, provenance expectations, and certification procedure.

Companion docs: [definitions](StockBallDB_definitions.md) · [sources](StockBallDB_sources.md) · [schema](StockBallDB_schema.md) · [snapshots_and_rebuilds](StockBallDB_snapshots_and_rebuilds.md) · [operational_update](StockBallDB_operational_update.md) · [explorer](StockBallDB_explorer.md) · [workflow](StockBallDB_workflow.md)

StockBallDB is a historical financial and market-context database. It is not an experiment, strategy engine, or trading system.

---

## 1. Responsibilities

### `validate_v1`

Hard whole-database structural and semantic invariants. No provider network calls.

```text
python -m stockballdb.validate_v1
```

Proves (among other checks):

- Alembic head matches the locked V1 revision
- `pandas_market_calendars` pin matches the required calendar version
- Spine 1:1: `macro_conditions` and `calendar_context` counts equal `trading_days`
- Market chain 1:1: `market_outcomes` and `asset_regimes` counts equal `daily_market_data`
- No orphan FK rows for spine-backed tables; all `daily_market_data` dates ∈ `trading_days`
- ETF vs WTI observation row-shapes
- Locked symbol count (14 ETFs + WTI)
- Selected cross-table identities (e.g. drawdown / return_1d consistency; event flags ↔ on-calendar `scheduled_events`)

`validate_v1` **PASS** means hard invariants hold. It does **not** score freshness, expected publication lag, or known provider gaps inside active spans.

### `health`

Coverage, freshness, gap, integrity, provenance, and limitation reporting. Reuses hard checks (including `validate_v1`) and adds dataset-specific expectations.

```text
python -m stockballdb.health
python -m stockballdb.health --json
python -m stockballdb.health --strict
```

| Status | Meaning |
| --- | --- |
| **HEALTHY** | No ERROR/FATAL findings; structural and cross-table invariants pass |
| **HEALTHY WITH WARNINGS** | Structurally sound; WARNING findings present (investigate; not proven corrupt) |
| **UNHEALTHY** | Any ERROR or FATAL finding |

There is **no** subjective data-quality score.

### Database fingerprint

```text
python -m stockballdb.fingerprint
```

Deterministic SHA-256 over all seven canonical tables (PK-ordered rows, alphabetical columns, stable `Decimal` serialization). Purpose: prove byte-level identity of canonical table contents (rebuild match, update before/after, Explorer non-mutation). Fingerprint is not a substitute for `validate_v1` or `health`.

---

## 2. Severity ladder

| Level | When | Blocks build stage? | Fails `validate_v1`? |
| --- | --- | --- | --- |
| **PASS** | Invariant satisfied | — | — |
| **INFO** | Expected limitation or normal publication lag | No | No |
| **WARNING** | Suspicious but not proven corrupt; investigate | No | No (optional elevation via `health --strict`) |
| **ERROR** | Canonical contract violation; data untrustworthy | Yes (stage) | Yes |
| **FATAL** | Schema / FK / PK / migration corruption | Yes | Yes |

Examples:

```text
WTI 1–3 session lag vs ETFs          → INFO
ICSA sparse pre-2009                 → INFO (contract)
ETF missing ≥10 consecutive sessions → ERROR
orphan FK row                        → FATAL
Alembic head mismatch                → FATAL
```

### `health` exit codes

| Status | Default exit | `--strict` exit |
| --- | ---: | ---: |
| HEALTHY | 0 | 0 |
| HEALTHY WITH WARNINGS | 0 | 1 |
| UNHEALTHY | 1 | 1 |

`--strict` elevates **HEALTHY WITH WARNINGS** to a non-zero exit. INFO-only reports remain HEALTHY and exit 0.

---

## 3. What a healthy instance means

A healthy StockBallDB instance is:

```text
STRUCTURALLY sound
COVERAGE-consistent with locked contracts
FRESH within dataset-specific expectations
SEMANTICALLY aligned with canonical definitions
PROVENANCE-describable (provider/series/normalization; build/manifest metadata)
REPRODUCIBLE-READY (deterministic transforms from known inputs)
```

Health report sections (human and `--json`):

```text
SYSTEM STATUS
DATABASE / MIGRATION
TABLE COVERAGE
MARKET DATA (per symbol)
MACRO (per field)
EVENTS
CALENDAR
FRESHNESS
PROVENANCE
CROSS-TABLE INTEGRITY
WARNINGS
ERRORS
→ HEALTHY | HEALTHY WITH WARNINGS | UNHEALTHY
```

JSON includes at least: `status`, `timestamp`, `alembic_head`, `findings[]` (`severity`, `code`, `dataset`, `message`), coverage, and freshness.

---

## 4. Missingness classes

| Class | Meaning | Health treatment |
| --- | --- | --- |
| **PRE-INCEPTION** | Before symbol/series history starts; no row expected | ignore / INFO |
| **NON-TRADING DAY** | Outside NYSE trading spine; no market row expected | ignore |
| **PRE-SERIES** | Before authoritative macro/event floor | INFO |
| **NOT YET PUBLISHED** | Provider has not released the next observation | INFO |
| **EXPECTED LAG** | Normal publication delay vs spine | INFO |
| **PROVIDER GAP** | Source lacks an observation inside active span | INFO or WARNING by length/pattern |
| **UNEXPECTED GAP** | Missing where a row/value is required | WARNING → ERROR by rule |
| **NOT APPLICABLE** | Field does not apply (e.g. range on close-only WTI) | ignore |
| **UNRESOLVED SOURCE** | Out of V1 scope (XAU/USD, DXY, PMI) | N/A |
| **STALE** | Last observation older than freshness threshold | WARNING+ |
| **MISSING** | NULL or absent where a value could exist | context-dependent |

Market-data missingness shorthand:

```text
PRE-INCEPTION     → no row expected
NON-TRADING DAY   → no row expected
EXPECTED LAG      → provider not yet published (INFO)
PROVIDER GAP      → missing inside active span (ERROR if sustained)
UNEXPECTED GAP    → ERROR
```

Pre-floor NULLs are **not** defects.

---

## 5. Freshness principles

**Datasets need not share the same max date.**

| Dataset | Freshness anchor | Expected lag | Thresholds |
| --- | --- | --- | --- |
| `trading_days` | latest known NYSE session | 0–1 sessions vs calendar | WARNING if >5 sessions behind today |
| ETF `daily_market_data` | last Tiingo EOD per symbol | 0–3 sessions vs spine | INFO ≤3; WARNING >5; ERROR if ≥10 consecutive missing in active span |
| WTI | last FRED observation | 1–3 sessions vs spine | INFO ≤3; WARNING >5 |
| `macro_conditions` row date | spine date | matches `trading_days` | ERROR if macro max < TD max |
| macro field values | per-series publication | daily–monthly | INFO inside known cycle; staleness by native frequency |
| `scheduled_events` | last `event_date` | may trail or lead market max | INFO for historical-only lag |
| `calendar_context` | = `trading_days` max | 0 | ERROR if mismatch |

Rules respect native frequency (monthly macro holes ≠ daily market holes).

---

## 6. Gap rules

| Rule | Detection |
| --- | --- |
| ETF missing ≥N consecutive sessions inside active span | **ERROR** if N≥10 |
| WTI / ETF lag vs spine | INFO ≤3; WARNING >5 |
| Macro field long NULL run after series start | WARNING → ERROR by length / frequency |
| Event family missing expected periodic occurrence | WARNING (family-specific) |
| `calendar_context` missing a `trading_days` date | FATAL |
| `daily_market_data` row missing for symbol on session in active span | WARNING/ERROR by count and consecutive length |

---

## 7. Cross-table invariant categories

| Category | Requirement |
| --- | --- |
| Spine 1:1 | `COUNT(macro_conditions) = COUNT(trading_days)`; `COUNT(calendar_context) = COUNT(trading_days)` |
| Market 1:1 | `COUNT(market_outcomes) = COUNT(daily_market_data)`; `COUNT(asset_regimes) = COUNT(daily_market_data)` |
| Referential | No orphan outcomes/regimes; all DMD dates ∈ `trading_days` |
| Row shape | ETF complete OHLC shape; WTI close-only shape |
| Calendar/events | Event flags on `calendar_context` match on-calendar `scheduled_events` |
| Derived identity | `drawdown_pct` ≡ `drawdown_from_high`; outcomes `return_1d` ≡ next DMD `return_1d` |
| Migration / pin | Alembic head and calendar library pin match locked V1 |

Enforcement layers: PostgreSQL PK/FK/CHECK; app table validators; `validate_v1` for hard release gates; `health` for freshness, gaps, coverage, and provenance summary; pytest for PIT and unit/integration coverage.

---

## 8. Provenance expectations

StockBallDB must be able to state, for each dataset:

```text
which provider and series/identifier
which canonical normalization rule
when build/retrieval last ran (manifest / run report)
resulting coverage and validation / health status
that derived tables follow deterministic transforms from canonical inputs
```

| Concern | Where it lives |
| --- | --- |
| Provider + series ID | code (`universe.py`, `macro/series.py`, providers) + [sources](StockBallDB_sources.md) |
| Normalization / PIT | code + [definitions](StockBallDB_definitions.md) + domain contracts |
| Event `source` enum | `scheduled_events.source` per row |
| Build/retrieval timestamps, row counts, alembic head, calendar pin, validation/health | `build_reports/manifest_*.json` and `run_*.json` |
| Environment / dependency fingerprint | manifest / health provenance payload |
| Database content identity | `python -m stockballdb.fingerprint` |

### Not persisted per row

```text
retrieval timestamp per observation
raw provider payload hash on each row
observation source date vs publication date (except scheduled_events.event_date)
updated_at columns on canonical tables
```

Byte-level raw payload archive and exact offline rebuild proof belong to snapshot/rebuild tooling — see [snapshots_and_rebuilds](StockBallDB_snapshots_and_rebuilds.md). Validation/health prove provider/series identity, coverage, and invariants; they do **not** replace immutable snapshot verification.

---

## 9. Validation vs snapshot reproducibility

| Layer | Proves |
| --- | --- |
| **Validation & health** | Provider/series mapping, normalization rules, coverage/freshness, hard invariants, build metadata |
| **Snapshots & exact rebuild** | Exact raw source payload used, byte-identical rebuild from archived snapshots, fingerprint match |

Do not confuse INFO freshness findings with snapshot corruption. Use `verify` / fingerprint tooling for payload integrity.

---

## 10. Expected limitations (not defects)

```text
CPI events from ~1972 (ALFRED)
Employment events from ~1960
Election distance from effective 1958-11-05
ICSA macro sparse pre-~2009
core CPI from ~1996
BAA10Y from ~1986
Treasury 2Y from 1976-06-01
WTI from 1986-01-02
WTI/ETF publication lag vs spine
Per-symbol ETF inception dates
Forward outcome NULL tail
Regime warm-up NULL zones
PMI absent (UNRESOLVED)
XAU/USD, DXY absent (UNRESOLVED)
No per-row retrieval timestamps
scheduled_events is occurrence calendar, not full historical schedule-knowability
calendar_context has no days_until_next_* fields
```

Authoritative market symbol registry: `src/stockballdb/market_data/universe.py`. Unresolved assets must not be treated as coverage failures.

---

## 11. Acceptable INFO findings vs actual failures

### Acceptable (do not fail certification when only these appear)

- ETF expected lag within INFO threshold vs trading spine
- WTI expected lag within INFO threshold vs spine
- Documented WTI provider gaps below ERROR consecutive threshold
- Pre-series / pre-inception NULLs and absent rows
- Forward-horizon and lookback warm-up NULLs on derived tables
- Unresolved XAU/USD, DXY, PMI (out of scope)

### Failures (block certification / release)

- `validate_v1` not PASS
- `health` **UNHEALTHY** (any ERROR/FATAL)
- Alembic head or calendar pin mismatch
- Cross-table count or orphan violations
- Invalid ETF/WTI row shapes
- ETF consecutive missing ≥10 sessions inside active span
- Snapshot verify: missing or corrupt payloads (when certifying rebuild capability)
- Fingerprint mismatch when identity is required (exact rebuild, update mutation check, Explorer non-mutation proof)

`HEALTHY WITH WARNINGS` is structurally acceptable for routine operation; use `--strict` when warnings must fail CI or gates. Operational `update` fails on **UNHEALTHY** only — see [operational_update](StockBallDB_operational_update.md).

---

## 12. Validation / certification procedure

Run against the canonical database (or a dedicated rebuild DB when proving exact rebuild).

1. **Migrate / confirm head** — Alembic at locked V1 head.
2. **`validate_v1`** — must PASS.
3. **`health`** — must be HEALTHY (or HEALTHY WITH WARNINGS only if INFO/WARNING are understood and accepted; use `--strict` when warnings are disallowed).
4. **`pytest`** — full suite green (skips only where intentionally marked).
5. **Fingerprint** — record `database_fingerprint` when identity matters.
6. **Snapshots** (when certifying rebuild capability) — verify all referenced snapshots; then optional `rebuild_exact` with fingerprint match — [snapshots_and_rebuilds](StockBallDB_snapshots_and_rebuilds.md).
7. **Explorer** (when certifying UI) — read-only inspection; fingerprint before/after must match — [explorer](StockBallDB_explorer.md).

Orchestrated build path: `build_v1` then validate/health. Incremental path: `update` embeds validate_v1 + health + before/after fingerprint — [workflow](StockBallDB_workflow.md), [operational_update](StockBallDB_operational_update.md).

---

## 13. Current Certified Baseline

| Check | Result |
| --- | --- |
| `validate_v1` | PASS |
| `health` | HEALTHY |
| `pytest` | 220 passed, 2 skipped |
| Explorer tests | 70 passed |
| Explorer manual certification | Phase 11C completed |
| Database fingerprint | `sha256:5055ae10f216ff33141eb137fc396ce29481e896c3ea828983e4ca8b12291aca` |
| Explorer mutation | Did **not** mutate the canonical database |
| Alembic head | `a8f3c2d1b4e5` |
| `trading_days` | 1957-01-02 through 2026-08-31 |
| `daily_market_data` / `market_outcomes` / `asset_regimes` | 99,633 rows each |
| `macro_conditions` / `calendar_context` | 17,533 rows each |
| `scheduled_events` | 2,641 rows |
| Current market symbols | 14 ETFs + WTI |
| Known health INFO | ETF lag 1 session; WTI lag 3 sessions; WTI provider gaps 39 sessions (max consecutive 2) |
| Snapshot verification | 91 checked, 0 missing, 0 corrupt |
| Explorer launch | `python -m stockballdb.explorer` |

Re-certify after schema changes, universe changes, rebuilds, or any write path that can alter canonical tables. Update this section only when a new baseline is intentionally certified.
