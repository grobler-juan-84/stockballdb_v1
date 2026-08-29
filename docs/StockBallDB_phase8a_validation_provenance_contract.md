# StockBallDB — Phase 8A Validation & Provenance Contract

**Version:** 1.0  
**Status:** LOCKED (audit + definition)  
**Date:** 2026-08-29  
**Scope:** Whole-DB health definition, validation inventory, coverage/freshness/provenance contracts, Phase 8B backlog. No Phase 8B implementation in 8A.

> Companion: [schema](StockBallDB_schema.md) · [workflow](StockBallDB_workflow.md) · Phase contracts 4A–7A

---

## 1. Purpose

Phase 8 hardens **validation and provenance** around the current seven-table architecture.

Phase 8A answers:

```text
What data exists?
How complete and fresh is it?
Where did it come from?
Which gaps are expected vs defects?
Which cross-table invariants must hold?
What can StockBallDB prove today vs Phase 9?
```

**Phase 8 ≠ Phase 9**

| Phase | Scope |
| --- | --- |
| **8 — Validation & provenance hardening** | Health contracts, validators, build metadata, freshness semantics |
| **9 — Snapshot reproducibility** | Immutable raw source payloads, exact historical rebuild proof |

Phase 8 does **not** require raw response archiving.

---

## 2. Whole-DB health definition

A **healthy** StockBallDB instance is:

```text
STRUCTURALLY sound
COVERAGE-consistent with locked contracts
FRESH within dataset-specific expectations
SEMANTICALLY aligned with canonical definitions
PROVENANCE-describable (even if not fully persisted)
REPRODUCIBLE-READY (deterministic transforms; live sources)
```

### 2.1 Health states (Phase 8B CLI target)

| State | Meaning |
| --- | --- |
| **HEALTHY** | No ERROR/FATAL findings; structural + cross-table invariants pass |
| **HEALTHY WITH WARNINGS** | PASS structurally; INFO/WARNING for expected lag, known limitations |
| **UNHEALTHY** | Any ERROR or FATAL finding |

No subjective “data quality score.”

### 2.2 Severity taxonomy

| Level | When | Build block? | validate_v1? |
| --- | --- | --- | --- |
| **PASS** | Invariant satisfied | — | — |
| **INFO** | Expected limitation or normal publication lag | No | No |
| **WARNING** | Suspicious but not proven corrupt; investigate | No | Optional future |
| **ERROR** | Canonical contract violation; data untrustworthy | Yes (stage) | Yes |
| **FATAL** | Schema/FK/PK corruption | Yes | Yes |

Examples:

```text
WTI 1–3 session lag vs ETFs          → INFO
ICSA sparse pre-2009                 → INFO (contract)
ETF missing 10+ consecutive sessions → ERROR
orphan FK row                        → FATAL
Alembic head mismatch                → FATAL
```

---

## 3. Seven-table inventory (live audit 2026-08-29)

| Table | Grain | PK | FK | Rows | First | Last | Build CLI |
| --- | --- | --- | --- | ---: | --- | --- | --- |
| `trading_days` | trading day | `date` | — | 17,532 | 1957-01-02 | 2026-08-28 | `build_trading_days` |
| `daily_market_data` | date × symbol | `(date,symbol)` | → `trading_days` | 99,605 | 1986-01-02 | 2026-08-26 | `build_daily_market_data` + `derive_daily_market_data` |
| `market_outcomes` | date × symbol | `(date,symbol)` | → `trading_days` | 99,605 | 1986-01-02 | 2026-08-26 | `build_market_outcomes` |
| `asset_regimes` | date × symbol | `(date,symbol)` | → `trading_days` | 99,605 | 1986-01-02 | 2026-08-26 | `build_asset_regimes` |
| `macro_conditions` | trading day | `date` | → `trading_days` | 17,532 | 1957-01-02 | 2026-08-28 | `build_macro_conditions` |
| `scheduled_events` | event | `event_id` | — (no TD FK) | 2,641 | 1957-01-08 | 2026-08-12 | `build_scheduled_events` |
| `calendar_context` | trading day | `date` | → `trading_days` | 17,532 | 1957-01-02 | 2026-08-28 | `build_calendar_context` |

**Orchestrated full rebuild:** `build_v1` (8 stages + migrate)  
**Whole-DB validation:** `validate_v1`

### 3.1 Per-table notes

#### `trading_days`
- **Acquired:** pinned `pandas_market_calendars` NYSE (`5.4.0`)
- **Derived fields:** ordinals, month/quarter/year boundaries, prev/next
- **Floor:** 1957-01-02 (manifesto)
- **Provenance in DB:** none (config/code pinned)

#### `daily_market_data`
- **Acquired:** Tiingo daily EOD (14 ETFs); FRED `DCOILWTICO` (WTI)
- **Derived columns:** `return_1d`, `gap_pct`, `intraday_return`, `range_pct`, `drawdown_from_high`
- **Row shapes:** full OHLC ETF vs close-only WTI (CHECK `ck_daily_market_data_observation_shape`)
- **Floor:** per-symbol inception (not spine start)
- **Provenance in DB:** none per row

#### `market_outcomes` / `asset_regimes`
- **Fully derived** from `daily_market_data`
- **NULL zones:** forward-horizon tail, lookback warm-up (legitimate)
- **1:1** with `daily_market_data` rows

#### `macro_conditions`
- **Acquired:** FRED/ALFRED per `macro/series.py`
- **Derived:** `yield_curve_10y_2y`, `inflation_regime`, `rate_regime`
- **1:1** with `trading_days`
- **PIT rules:** Phase 4A contract

#### `scheduled_events`
- **Acquired:** Fed FOMC pages, ALFRED first-print, statutory elections
- **Provenance in DB:** `source` enum per row; no retrieval timestamp
- **Future dates:** current build includes future CPI/Employment/FOMC occurrences through provider/calendar horizon where fetched (audit: 0 future rows at 2026-08-29 snapshot for FOMC; CPI last 2026-08-12)

#### `calendar_context`
- **Fully derived** from `trading_days`, NYSE metadata, `scheduled_events`
- **1:1** with `trading_days`; Phase 7A contract

---

## 4. Validation matrix

| Guarantee | DB constraint | App validator | validate_v1 | Health audit | pytest |
| --- | --- | --- | --- | --- | --- |
| PK uniqueness | PK | frame/db validators | — | — | partial |
| FK to trading_days | FK (most tables) | db validators | orphan checks | quick checks | partial |
| dmd row-shape ETF/WTI | CHECK | `validate_daily_market_data_*` | malformed counts | quick checks | yes |
| OHLC high≥low | CHECK | frame validation | — | — | yes |
| macro 1:1 spine | — | `validate_macro_*` | count match | audit | yes |
| calendar 1:1 spine | FK | `validate_calendar_*` | count match | audit | yes |
| outcomes/regimes 1:1 dmd | — | `validate_*_db` | count + orphan | audit | yes |
| drawdown identity dmd↔regimes | — | frame | SQL check | — | yes |
| return_1d outcome↔dmd | — | frame | SQL check | — | yes |
| event flags ↔ events | — | calendar validate | validate_v1 | phase7b audit | yes |
| FOMC scheduled-only | — | `validate_fomc_scheduled_only` | — | — | yes |
| macro PIT leak | — | assert_* macro | — | — | yes |
| Alembic head | — | preflight | validate_v1 | audit | yes |
| pandas_market_calendars pin | — | preflight | validate_v1 | — | yes |
| symbol count = 15 | — | universe constant | validate_v1 | audit | yes |
| freshness / gaps | — | — | — | **Phase 8B** | — |
| retrieval timestamp | — | — | — | **Phase 8B** | — |

**Classification key:** DATABASE CONSTRAINT · INGESTION VALIDATION · TABLE VALIDATION · CROSS-TABLE VALIDATION · PIPELINE PREFLIGHT · POST-BUILD AUDIT · TEST-ONLY

---

## 5. Coverage contract

### 5.1 Market data (15 symbols)

Authoritative registry: `src/stockballdb/market_data/universe.py`

| Symbol | Type | Provider | ID | First (live) | Last (live) | Rows | Notes |
| --- | --- | --- | --- | --- | --- | ---: | --- |
| SPY…XLRE (14) | etf | Tiingo | ticker | 1993–2018 | 2026-08-26 | varies | 100% coverage in active span |
| WTI | commodity | FRED | DCOILWTICO | 1986-01-02 | 2026-08-25 | 10,201 | close-only; ~99.6% in span |

**Missingness classes:**

```text
PRE-INCEPTION     → no row expected
NON-TRADING DAY   → no row expected
EXPECTED LAG      → provider not yet published (INFO)
PROVIDER GAP      → missing inside active span (ERROR if sustained)
UNEXPECTED GAP    → ERROR
```

Live finding: ETFs lag spine max by 2 sessions (2026-08-26 vs 2026-08-28) → **INFO** (Tiingo refresh / build timing). WTI lag 1 day → **INFO**.

### 5.2 Macro fields (Phase 4A)

Authoritative: `src/stockballdb/macro/series.py` + Phase 4A contract

| Field | Series | First non-null (live) | Coverage % | Expected floor |
| --- | --- | --- | ---: | --- |
| inflation_rate | CPIAUCSL PIT | 1972-07-21 | 77.8% | ALFRED CPI |
| core_inflation_rate | CPILFESL PIT | 1996-12-12 | 42.6% | ~1996 |
| unemployment_rate | UNRATE PIT | 1960-03-15 | 95.4% | ~1960 |
| jobless_claims | ICSA PIT | 2009-05-28 | 24.8% | sparse pre-~2009 |
| fed_funds_rate | DFF | 1957-01-02 | ~100% | spine |
| treasury_2y_yield | DGS2 | 1976-06-01 | 71.5% | 1976 |
| treasury_10y_yield | DGS10 | 1962-01-02 | 91.9% | ~1962 |
| yield_curve_10y_2y | derived | 1976-06-01 | 71.5% | both legs |
| fed_balance_sheet | WALCL | 2002-12-20 | 34.0% | ~2002 |
| credit_spread | BAA10Y | 1986-01-02 | 57.9% | ~1986; FRED current only |

Pre-floor NULLs are **NOT defects**.

### 5.3 Scheduled events (Phase 6A)

| Family | Rows | First | Last | On-cal flags | Off-cal | Time metadata |
| --- | ---: | --- | --- | ---: | ---: | --- |
| FOMC | 711 | 1957-01-08 | 2026-07-29 | 709 | 2 | 108 timed |
| CPI | 954 | 1972-07-21 | 2026-08-12 | 644 | 5 | 726 timed |
| Employment | 942 | 1960-03-15 | 2026-08-07 | 776 | 21 | 439 timed |
| Election | 34 | 1958-11-04 | 2024-11-05 | 25 | 9 | 0 timed |

### 5.4 Derived tables

| Table | Eligibility | NULL zones |
| --- | --- | --- |
| `market_outcomes` | 1:1 with each dmd row | forward horizons incomplete |
| `asset_regimes` | 1:1 with each dmd row | SMA/vol warm-up |
| `daily_market_data` derived cols | after first row per symbol | first-row returns NULL |
| WTI | close-only path | gap/range NULL |

---

## 6. Freshness contract

**Principle:** datasets need **not** share the same max date.

| Dataset | Freshness anchor | Expected lag | Threshold (PROVISIONAL) | Status |
| --- | --- | --- | --- | --- |
| `trading_days` | latest known NYSE session | 0–1 sessions vs calendar | WARNING if >5 sessions behind today | LOCKED semantics |
| ETF `daily_market_data` | last Tiingo EOD per symbol | 0–3 sessions vs spine | INFO ≤3; WARNING >5; ERROR >10 consecutive missing | PROVISIONAL |
| WTI | last FRED observation | 1–3 sessions vs spine | INFO ≤3; WARNING >5 | PROVISIONAL |
| `macro_conditions` row date | spine date | matches TD | ERROR if macro max < TD max | LOCKED |
| macro field values | per-series publication | daily–monthly | INFO inside known cycle | PROVISIONAL |
| `scheduled_events` | last event_date | may exceed market max | INFO if historical-only lag | PROVISIONAL |
| `calendar_context` | = `trading_days.max` | 0 | ERROR if mismatch | LOCKED |

Live snapshot (2026-08-29):

```text
trading_days     → 2026-08-28  CURRENT
ETF market data  → 2026-08-26  EXPECTED LAG (INFO)
WTI              → 2026-08-25  EXPECTED LAG (INFO)
macro row date   → 2026-08-28  CURRENT
scheduled_events → 2026-08-12  CURRENT (release calendar)
```

---

## 7. Missingness taxonomy

| Class | Meaning | Health treatment |
| --- | --- | --- |
| **MISSING** | NULL or absent row where value could exist | context-dependent |
| **STALE** | Last observation older than freshness threshold | WARNING+ |
| **NOT YET PUBLISHED** | Provider has not released next observation | INFO |
| **NOT APPLICABLE** | Field does not apply (e.g. range_pct on WTI) | ignore |
| **PRE-SERIES** | Before authoritative history starts | INFO |
| **PROVIDER GAP** | Source lacks observation | INFO/ WARNING |
| **UNRESOLVED SOURCE** | XAU/USD, DXY, PMI not in V1 | N/A |

---

## 8. Provenance matrix

| Dataset | Provider | Identifier | Normalization | PIT rule | In DB | In code/config | In docs | In logs |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| trading_days | NYSE via PMC | `NYSE` calendar 5.4.0 | session schedule | n/a | — | `calendar/nyse.py` | sources | build log |
| ETFs | Tiingo | per ticker | `market_data/normalize.py` | n/a | — | universe | sources | build log |
| WTI | FRED | DCOILWTICO | close-only row | n/a | — | `market_context/wti.py` | Phase 5A | build log |
| macro fields | FRED/ALFRED | see `macro/series.py` | `macro/pit.py`, align | Phase 4A | — | series specs | Phase 4A | build log |
| FOMC events | Federal Reserve | historical pages + calendars | `events/fomc.py` | occurrence | `source` | types | Phase 6A | build log |
| CPI/Employment events | ALFRED | CPIAUCSL/UNRATE vintages | `events/releases.py` | first-print | `source` | types | Phase 6A | build log |
| Elections | statutory | formula | `events/elections.py` | n/a | `source` | types | Phase 6A | — |
| NYSE holidays | PMC | early_closes/adhoc | `calendar_context/holidays.py` | n/a | — | code | definitions | — |
| calendar_context | derived | — | `calendar_context/derive.py` | Phase 7A | — | contract | — |
| outcomes/regimes | derived | — | derive modules | retrospective | — | definitions | — |

### 8.1 Not currently persisted

```text
retrieval timestamp (per dataset)
git commit / code version (optional in build_reports only)
raw provider payload hash
per-row observation source date vs publication date (except scheduled_events.event_date)
database updated_at on any table
```

**Phase 8B minimum:** build manifest with dataset-level retrieval time, row counts, validation result, alembic head, calendar pin.

---

## 9. Provider mapping inventory (authoritative sources)

| Canonical | Provider | Provider ID | Module |
| --- | --- | --- | --- |
| SPY…XLRE | Tiingo | ticker symbol | `providers/tiingo.py` |
| WTI | FRED | DCOILWTICO | `providers/fred.py`, `market_context/wti.py` |
| inflation_rate | ALFRED | CPIAUCSL | `macro/series.py` |
| core_inflation_rate | ALFRED | CPILFESL | `macro/series.py` |
| unemployment_rate | ALFRED | UNRATE | `macro/series.py` |
| jobless_claims | ALFRED | ICSA | `macro/series.py` |
| fed_funds_rate | FRED | DFF | `macro/series.py` |
| treasury_* | FRED | DGS2/DGS10 | `macro/series.py` |
| fed_balance_sheet | FRED | WALCL | `macro/series.py` |
| credit_spread | FRED | BAA10Y | `macro/series.py` |
| fomc events | Fed | fomchistorical*, fomccalendars.htm | `providers/fed.py`, `events/fomc.py` |
| cpi events | ALFRED | CPIAUCSL vintages | `events/releases.py` |
| employment events | ALFRED | UNRATE vintages | `events/releases.py` |
| election events | statutory | — | `events/elections.py` |
| trading calendar | PMC NYSE | 5.4.0 | `calendar/nyse.py` |

**Symbol registry audit:** `market_data/universe.py` is authoritative for market symbols. **NEEDS HARDENING IN 8B:** health/validate should import registry — not duplicate symbol lists (validate_v1 already uses `V1_MARKET_SYMBOL_COUNT`).

**Event types:** `events/types.py` `EVENT_TYPES` — extensible frozenset; validators should reference it in 8B.

---

## 10. Cross-table invariants (locked)

| Invariant | Status (live) |
| --- | --- |
| `COUNT(calendar_context) = COUNT(trading_days)` | PASS |
| `COUNT(macro_conditions) = COUNT(trading_days)` | PASS |
| `COUNT(market_outcomes) = COUNT(daily_market_data)` | PASS |
| `COUNT(asset_regimes) = COUNT(daily_market_data)` | PASS |
| No orphan outcomes/regimes | PASS |
| All dmd dates ∈ trading_days | PASS |
| ETF row-shape complete | PASS |
| WTI close-only row-shape | PASS |
| Event flags = on-calendar scheduled_events | PASS |
| drawdown_pct ≡ drawdown_from_high | PASS |
| outcomes.return_1d ≡ next dmd.return_1d | PASS |
| Alembic head `a8f3c2d1b4e5` | PASS |
| `validate_v1` | PASS |

Phase 7 invariants: see Phase 7A/7B audit scripts (not re-run in 8A; assumed PASS at checkpoint).

---

## 11. Contract drift audit (docs vs code vs DB)

| Area | Result |
| --- | --- |
| Phase 4 macro | **NONE** — live floors match contract |
| Phase 5 WTI | **NONE** — close-only rows valid |
| Phase 6 events | **NONE** — 2,641 rows, 37 off-calendar |
| Phase 7 calendar | **NONE** — 1:1 spine |
| Schema column counts | **DOCUMENTATION DRIFT (minor)** — Phase 7A prose said “21 columns”; live `calendar_context` has **19** (correct in schema) |
| Universe doc “17 assets” | **DOCUMENTATION DRIFT (minor)** — counts unresolved XAU/DXY in narrative; V1 ingests 15 |

No code or data drift requiring 8A fixes.

---

## 12. Health report design (Phase 8B)

**Command (planned):** `python -m stockballdb.health`

### 12.1 Sections

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

### 12.2 Machine-readable output

**Recommendation:** single validation engine → human CLI + `--json` flag.

JSON should include: `status`, `timestamp`, `alembic_head`, `findings[]` with `{severity, code, dataset, message}`, `coverage`, `freshness`.

For Phase 10 ops and Phase 11 Explorer — **SHOULD FIX IN 8B**.

---

## 13. Failure behavior (Phase 8B)

| Class | Action |
| --- | --- |
| schema / Alembic mismatch | FATAL — block build |
| duplicate PK / orphan FK | FATAL |
| invalid row shape | ERROR — block stage |
| validate_v1 hard invariant fail | ERROR — block release |
| expected macro/event pre-floor NULL | INFO — pass |
| WTI/ETF publication lag | INFO — pass |
| suspicious gap inside active span | WARNING — pass with flag |
| missing cross-table validator | ERROR on detection |

---

## 14. Expected limitations (NOT defects)

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
No raw snapshot archive (Phase 9)
scheduled_events includes occurrence calendar, not full historical schedule-knowability
calendar_context: no days_until_next_* (Phase 7)
```

---

## 15. Unexpected gap rules (Phase 8B)

| Rule | Detection |
| --- | --- |
| ETF missing ≥N consecutive sessions inside active span | ERROR if N≥10 |
| macro field long NULL run after series start | WARNING → ERROR by length |
| event family missing expected periodic occurrence | WARNING (family-specific) |
| calendar_context missing TD date | FATAL |
| dmd row missing for symbol on session in span | WARNING/ERROR by count |

Rules must respect native frequency (monthly macro ≠ daily holes).

---

## 16. Future expansion safety (Phase 8B guidance)

- Import symbol universe from `universe.py` — do not hard-code `15` in multiple places
- Import `EVENT_TYPES`, `MACRO_SERIES` for validator scope
- Health report lists **active** vs **deferred** assets explicitly

---

## 17. Enforcement layer recommendations

| Invariant | Best layer |
| --- | --- |
| Row-shape | PostgreSQL CHECK + app validator |
| FK / PK | PostgreSQL + app |
| Freshness | health audit only |
| PIT macro leak | app assert + pytest |
| Cross-table counts | validate_v1 + health |
| Coverage gaps | health audit |
| Provenance | build manifest (8B) + docs |

---

## 18. Phase 8 vs Phase 9 boundary

### Phase 8 can prove

```text
which provider and series ID
which canonical normalization rule
when build/retrieval last ran (8B target)
resulting coverage and validation status
deterministic derivation from current canonical inputs
```

### Phase 9 must prove

```text
exact raw source payload/file used for each build
byte-identical rebuild from archived snapshot
```

Do not implement snapshot storage in Phase 8B.

---

## 19. Phase 8B backlog (prioritized)

### MUST FIX IN 8B

1. `python -m stockballdb.health` CLI (human + JSON)
2. Dataset-level build/retrieval manifest (extend `build_reports/` pattern)
3. Freshness checks with PROVISIONAL thresholds (INFO/WARNING/ERROR)
4. Market-data gap detector inside active symbol spans
5. Wire health to reuse `validate_v1` + table validators

### SHOULD FIX IN 8B

6. Centralize event-type / macro-field lists in health (no drift)
7. Document retrieval timestamp convention in build manifest
8. Optional `--strict` mode elevates WARNING → ERROR
9. Post-`build_v1` automatic health summary

### DEFER

| Item | Phase |
| --- | --- |
| Raw immutable snapshots | 9 |
| Exact rebuild proof | 9 |
| Orchestrated scheduling | 10 |
| Explorer UI dashboard | 11 |
| XAU/USD, DXY, PMI ingestion | unresolved |
| Jobless Claims events, GDP | 6C+ |

### NO ACTION

- Subjective quality score
- New canonical tables for provenance (unless manifest file suffices)
- Redesign Phase 4–7 semantics

---

## 20. Phase 8A live audit summary

**Script:** `scripts/phase8a_health_audit.py`  
**Overall:** **HEALTHY** (INFO: WTI 1-day lag; ETF 2-session lag vs spine)  
**validate_v1:** PASS  
**pytest:** 92/92 PASS  
**Cross-table quick checks:** all PASS

---

## 21. Phase 8A completion

| Item | Result |
| --- | --- |
| Seven-table audit | Complete |
| Validation inventory | §4 |
| Health/freshness/provenance contracts | §2, §6–§8 |
| Provider mapping | §9 |
| Phase 8B backlog | §19 |
| Live audit | §20 |

**Recommendation:** Proceed to Phase 8B implementing `health` CLI + build manifest + freshness/gap audits per §19 MUST list.

---

## 22. Phase 8B verification (implementation record)

**Status:** COMPLETE (2026-08-29)

### Health CLI

```text
python -m stockballdb.health           # human report, exit 0 if HEALTHY
python -m stockballdb.health --json    # machine-readable JSON
python -m stockballdb.health --strict  # exit 1 on HEALTHY WITH WARNINGS
```

**Module:** `src/stockballdb/health/` (`engine`, `models`, `coverage`, `freshness`, `gaps`, `integrity`, `provenance`, `render`, `limitations`)

### Live run (2026-08-29)

| Metric | Value |
| --- | --- |
| Status | **HEALTHY** |
| Runtime | ~2.4 s |
| INFO | 3 (ETF_EXPECTED_LAG, WTI_EXPECTED_LAG, WTI_PROVIDER_GAP) |
| WARNING / ERROR / FATAL | 0 |
| validate_v1 | PASS (reused) |
| Exit code | 0 |

### Build manifest

- **Location:** `build_reports/manifest_<build_id>.json`
- **Schema version:** 1.0
- **Fields:** build_id, command, started/finished/retrieved timestamps, datasets, providers, validation_result, health_status, alembic_head, calendar_pin, git, stages, limitations
- **Integration:** `build_v1` writes manifest + health summary on successful completion
- **Secrets:** scan rejects api_key/password/connection URLs in manifest

### Exit codes

| Status | Default exit | `--strict` exit |
| --- | ---: | ---: |
| HEALTHY | 0 | 0 |
| HEALTHY WITH WARNINGS | 0 | 1 |
| UNHEALTHY | 1 | 1 |

### Phase 8 closeout

**PHASE 8 = COMPLETE.** **NEXT:** Phase 9 — Immutable Source Snapshots & Exact Rebuild Reproducibility (not started).

### Tests

pytest **103/103 PASS** (+11 health tests).
