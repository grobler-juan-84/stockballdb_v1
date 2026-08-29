# StockBallDB — Phase 4A Macro Conditions Source & Definition Contract

**Status:** LOCKED (design contract only — no population in this phase)  
**Applies to:** `macro_conditions` observed input fields  
**Implementation reference:** `src/stockballdb/macro/series.py`, `align.py`, `pit.py` (V1.0.0)

This document is the authoritative Phase 4A contract for **what each macro field means**, **where it comes from**, **how point-in-time history is handled**, and **how observations align to `trading_days`**.

Phase 4A scope is **observed inputs** and their alignment. Derived fields `yield_curve_10y_2y`, `inflation_regime`, and `rate_regime` are noted but **not re-locked** in this phase (regime thresholds remain outside Phase 4A scope).

---

## 1. Audit summary (Phases 1–3 reuse)

StockBallDB V1.0.0 already implements `macro_conditions` (Phase 2E). Phase 4A **codifies** that implementation as the locked contract rather than redesigning it.

| Pattern | Reused from | Macro usage |
| --- | --- | --- |
| FRED/ALFRED HTTP client | `providers/fred.py` | Current obs + full vintage pulls |
| Series configuration | `macro/series.py` | Frozen field → FRED ID map |
| Trading-day spine | `trading_days` | 1:1 output grain |
| Release timing | `macro/align.py` | `pre_open` / `after_close` / `observation_date` |
| PIT reconstruction | `macro/pit.py` | ALFRED `realtime_start` windows |
| Forward-fill policy | `macro/pit.py` | Latest **publicly knowable** value only |
| Validation | `macro/validate.py` | Anti-leakage + shape checks |
| Build orchestration | `macro/build.py`, `build_macro_conditions.py` | Fetch → align → derive → upsert |
| Documentation | `StockBallDB_definitions.md` §5, `StockBallDB_sources.md` §2–3 | Series IDs and rules |

**Doc ↔ code gap resolved in Phase 4A:** Global §Percentage Representation in `StockBallDB_definitions.md` states decimal returns for **market** fields. Macro rate fields intentionally use **FRED-native percentage points** (see §4).

---

## 2. Overriding rule (point-in-time)

For historical trading date `t`, every `macro_conditions` value must represent information that could have been known by the market **no later than** `t`.

```text
reference period (what the statistic describes)
        ↓
publication / release (when it becomes knowable)
        ↓
StockBallDB availability mapping → trading day
        ↓
forward-fill (only where semantically “latest known reading”)
        ↓
value stored on trading_days.date = t
```

**Never:** copy a future release backward, use today's revised history where ALFRED is required, or treat reference month as availability month.

---

## 3. Percentage / units convention (LOCKED)

| Domain | Convention | Example |
| --- | --- | --- |
| Market returns (`daily_market_data`, outcomes) | Decimal return | `0.03` = +3% |
| Macro rates & spreads (`macro_conditions`) | **Percentage points** (FRED-native) | `3.0` = 3%, `4.2` = 4.2% |
| Inflation YoY | Percentage points | `2.5` = 2.5% YoY |
| Jobless claims | Persons (SA) | `220000` |
| Fed balance sheet | Millions USD | WALCL native units |

CPI / core CPI: store **computed YoY %** in DB; reproducibility requires underlying **PIT index levels** from ALFRED at transform time (not a pre-computed opaque FRED transformation series).

---

## 4. Field contract matrix

| Field | Provider | Series | Freq | Source units | DB units | Reference period | Release / availability | Revision | ALFRED required | Alignment rule | Forward-fill | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `inflation_rate` | FRED/ALFRED | **CPIAUCSL** | Monthly index | Index (1982–84=100) | YoY **%** (pp) | Calendar month of index | BLS CPI release; `realtime_start` = first print / revision event | Revisions change PIT state | **Yes** | `pre_open`: release calendar date → same TD if open else next TD | Yes — latest knowable YoY | **LOCKED** |
| `core_inflation_rate` | FRED/ALFRED | **CPILFESL** | Monthly index | Index | YoY **%** (pp) | Calendar month | BLS core CPI release | Revisions change PIT state | **Yes** | `pre_open` | Yes | **LOCKED** |
| `unemployment_rate` | FRED/ALFRED | **UNRATE** | Monthly | % SA | % (pp) | Calendar month | BLS Employment Situation | Revisions change PIT state | **Yes** | `pre_open` | Yes | **LOCKED** |
| `jobless_claims` | FRED/ALFRED | **ICSA** | Weekly | Persons SA | Persons | Week ending | DOL release (typically Thursday) | Revisions change PIT state | **Yes** (best-effort) | `pre_open` | Yes | **LOCKED** (see limitation) |
| `fed_funds_rate` | FRED | **DFF** | Daily | % | % (pp) | Calendar day | Same-day observation | Minor same-day revisions possible | No | `observation_date`: value only if obs date is a trading day | **No** | **LOCKED** |
| `treasury_2y_yield` | FRED | **DGS2** | Daily | % | % (pp) | Calendar day | Same-day Treasury yield | Revised history on FRED | No | `observation_date` | **No** | **LOCKED** |
| `treasury_10y_yield` | FRED | **DGS10** | Daily | % | % (pp) | Calendar day | Same-day Treasury yield | Revised history on FRED | No | `observation_date` | **No** | **LOCKED** |
| `fed_balance_sheet` | FRED | **WALCL** | Weekly (Wed level) | Millions USD | Millions USD | Week ending Wednesday | H.4.1 release (Thu); obs Wed → `obs+1` cal → `after_close` | Revised levels on FRED | No | `after_close`: first TD **strictly after** release calendar date | Yes | **LOCKED** |
| `credit_spread` | FRED | **BAA10Y** | Daily | % spread | % (pp) | Calendar day | FRED daily observation | Revised on FRED; not vintage-reconstructed in V1 | No | `observation_date` | **No** | **LOCKED** (caveats §6) |
| `pmi` | — | — | — | — | — | — | — | — | — | — | — | **UNRESOLVED** |
| `yield_curve_10y_2y` | Derived | — | — | — | % (pp) | — | — | — | — | Same TD as inputs | N/A | Derived (out of 4A inputs scope) |
| `inflation_regime` | Derived | — | — | — | enum | — | — | — | — | — | — | **Out of Phase 4A scope** (V1 impl exists; thresholds not re-locked here) |
| `rate_regime` | Derived | — | — | — | enum | — | — | — | — | — | — | **Out of Phase 4A scope** (V1 impl exists; thresholds not re-locked here) |

### Missing-data rules (all fields)

- No backward-fill before first availability.
- No interpolation across missing releases.
- No fabrication for weekends/holidays except explicit alignment rules above.
- NULL remains NULL when no observation exists and forward-fill is disabled.

---

## 5. Point-in-time rules by frequency class

### Monthly revised (ALFRED required)

**Fields:** `inflation_rate`, `core_inflation_rate`, `unemployment_rate`

1. Pull full ALFRED vintage history (`realtime_start` / `realtime_end` windows).
2. On each ALFRED event date `realtime_start`, build `as_of` state map for reference months knowable that day.
3. For CPI fields: compute YoY from PIT **index levels** for the latest reference month in state (`(index_t / index_t-12 - 1) × 100`).
4. Map `realtime_start` calendar date → trading day via `pre_open`.
5. Forward-fill on trading days until the next mapped release event updates the reading.

**Anti-leak test:** value must be NULL on all trading days strictly before the first mapped availability day for that release path.

### Weekly revised (ALFRED required, coverage caveat)

**Field:** `jobless_claims` (ICSA)

Same PIT machinery as monthly, but weekly reference periods.  
**Known limitation:** ALFRED vintage depth for ICSA is sparse/incomplete before ~2009 → early history is best-effort with extended NULL regions (`ICSA_VINTAGE_LIMITATION` in `series.py`).

### Daily market rates (current FRED acceptable)

**Fields:** `fed_funds_rate`, `treasury_2y_yield`, `treasury_10y_yield`, `credit_spread`

1. Fetch current FRED observation history (not ALFRED vintages in V1).
2. Map each observation calendar date with `observation_date` — value appears **only** on that trading day if it is a trading day.
3. No forward-fill — NULL on days without a same-day observation.

**Rationale:** Same-day market/fixing series; revision risk is materially lower than monthly BLS restatements. Acceptable trade-off documented; ALFRED upgrade is a future optional hardening, not required to lock Phase 4A.

### Weekly Fed balance sheet (current FRED + release lag)

**Field:** `fed_balance_sheet` (WALCL)

1. Wednesday level in FRED.
2. Treat Thursday as release calendar date (`observation_date + 1 day`).
3. Map with `after_close` → first trading day strictly after Thursday.
4. Forward-fill until next release.

---

## 6. Unresolved / caveats

### `credit_spread` — LOCKED with documented limitations

**Approved series:** `BAA10Y` (Moody's Seasoned Baa corporate yield minus 10-Year Treasury constant maturity, FRED-precomputed).

**Why not left TBD:** FRED provides long, automatable, free daily history adequate for V1 research context; alternative composite spreads (ICE BofA) are not on the same free reproducible path.

**Caveats (must be understood):**

| Issue | Impact |
| --- | --- |
| Current FRED series only (no ALFRED vintages in V1) | Historical restatements on FRED could differ from true PIT spread on old dates |
| FRED-precomputed spread | StockBallDB does not derive from separate Baa and 10Y legs |
| Coverage starts ~1986 | NULL before series availability |
| Missing observations (`.`) | Remain NULL; no forward-fill |
| Not an investment-grade or high-yield index | Baa is a specific Moody's rating bucket |

**Alternatives rejected for Phase 4A lock:** manual `BAA` − `DGS10` (methodology mismatch vs FRED spread); proprietary indices without free API; convenience substitutes without historical sufficiency.

### `pmi` — UNRESOLVED

| Candidate | Verdict |
| --- | --- |
| ISM Manufacturing PMI via FRED | **Rejected** — ISM series removed from FRED (post-2016); not freely reproducible via locked V1 providers |
| ISM direct / scraped | **Rejected** — not automatable/reproducible under StockBallDB V1 principles |
| S&P Global PMI (ex- Markit) | **Rejected** — licensing / access not aligned with free reproducible V1 stack |

**Schema:** no `pmi` column in V1 (`macro_conditions` migration omits it).  
**Status:** remain NULL/absent until a source meets manifesto requirements. **Missing is correct.**

### Regime fields — out of Phase 4A scope

`inflation_regime` and `rate_regime` exist in V1 code/docs but Phase 4A intentionally does **not** re-lock thresholds or methodology. See `StockBallDB_definitions.md` §5 for current V1 behavior reference only.

### Provenance

Current schema stores values only (no per-row `source_series` / `vintage_id` columns). Provenance for Phase 4B is answerable from:

- locked series map (`macro/series.py`);
- ALFRED vintage reconstruction logic;
- build CLI logs and FRED pull parameters.

**No schema extension required** for Phase 4B ingestion under this contract. Optional future metadata (e.g. release calendar date column) is **not** mandated in Phase 4A.

---

## 7. Relationship to `scheduled_events`

BLS **release occurrences** (CPI, Employment Situation) live in `scheduled_events`.  
Macro **values** live in `macro_conditions`. Phase 4A PIT availability for CPI/UNRATE is driven by ALFRED `realtime_start`, which should be consistent with but not duplicated as — first-print dates in `scheduled_events`.

---

## 8. Phase 4B readiness

Phase 4B may implement or re-run ingestion **using this contract only** — no new source or semantic decisions required.

**READY FOR PHASE 4B — MACRO CONDITIONS INGESTION** (contract locked; V1 reference implementation already exists).

---

## 9. Reproducibility note

| Claim | Phase 4A |
| --- | --- |
| Structural reproducibility (rules + series map) | YES |
| Current-source rebuild | YES |
| Exact historical snapshot (byte-identical) | NO — live FRED/ALFRED revisions; no durable raw archive in V1 |

Do not describe macro history as byte-for-byte reproducible across months-long rebuild gaps.

---

## 10. Phase 4B verification snapshot (2026-08-28)

Live ingestion on working DB after `build_macro_conditions` (run ×2, idempotent):

| Field | First non-NULL | Coverage |
| --- | --- | --- |
| `inflation_rate` | 1972-07-21 | 77.8% |
| `core_inflation_rate` | 1996-12-12 | 42.6% |
| `unemployment_rate` | 1960-03-15 | 95.4% |
| `jobless_claims` | 2009-05-28 | 24.8% |
| `fed_funds_rate` | 1957-01-02 | ~100% |
| `treasury_2y_yield` | 1976-06-01 | 71.5% |
| `treasury_10y_yield` | 1962-01-02 | 91.9% |
| `fed_balance_sheet` | 2002-12-20 | 34.0% |
| `credit_spread` | 1986-01-02 | 57.9% |

Grain: **one row per `trading_days.date`** (including all-NULL early history). Audit script: `scripts/phase4b_macro_audit.py`.
