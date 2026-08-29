# StockBallDB — Phase 5A Additional Market Context Source & Definition Contract

**Status:** LOCKED (design contract only — no ingestion in this phase)  
**Applies to:** `WTI`, `XAU/USD`, `DXY` (universe “Additional Market Context”)  
**Package version:** 1.0.0

Phase 5A determines **what each asset means**, **which source is authoritative**, and **how it fits** the existing canonical schema. No PostgreSQL population in this phase.

---

## 1. Audit — reuse from Phases 0–4

| Pattern | Reuse for Phase 5 |
| --- | --- |
| `daily_market_data` grain `(date, symbol)` | **Yes** — same table for non-ETF context series |
| `trading_days` spine + date FK | **Yes** — align observations to NYSE trading days |
| Tiingo ETF pipeline (`market_data/build.py`) | **Pattern only** — Phase 5 uses FRED/EIA/other providers |
| `macro_conditions` FRED client | **Pattern** — `providers/fred.py` reusable for WTI |
| Validation / logging / CLI style | **Yes** |
| `ASSET_TYPE_BY_SYMBOL` in `universe.py` | **Extend** in Phase 5B |

**Do not create a new canonical table** merely because providers differ. Provider logic belongs in acquisition/normalization layers.

**Critical schema finding:** V1 `daily_market_data` ORM/migration requires **NOT NULL** on `open`, `high`, `low`, `close`, `volume`, all `adj_*`, `dividend_cash`, `split_factor`. Phase 5 sources often provide **one daily level only**. Phase 5B requires a **minimal migration** to allow NULL on non-applicable OHLCV/adjusted/corp-action columns (see §8).

---

## 2. Decision summary

| Asset | Canonical definition (locked) | Source | Identifier | Start (expected) | Status |
| --- | --- | --- | --- | --- | --- |
| **WTI** | WTI **spot** crude, Cushing OK FOB | FRED (EIA) | **DCOILWTICO** | **1986-01-02** | **LOCKED** |
| **XAU/USD** | USD **spot gold** per troy oz (benchmark fix, not ETF) | — | — | — | **UNRESOLVED** |
| **DXY** | ICE **U.S. Dollar Index** (USDX), not TWI | — | — | — | **UNRESOLVED** |

---

## 3. Full contract matrix

| Asset | Definition | Provider | Series / ID | Freq | Units | Date semantics | Revisions | PIT/vintage | Alignment | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| WTI | Daily WTI spot at Cushing, Oklahoma (cash/reference market; **not** CL futures, not USO) | FRED → EIA | DCOILWTICO | Daily (business days) | USD/barrel | **Observation date** = EIA spot price date | EIA may revise; current FRED series | Not required (same class as DFF/DGS) | Map to `trading_days` only when obs date is a trading day; **no forward-fill** | **LOCKED** |
| XAU/USD | LBMA Gold Price **PM fix**, USD/troy oz (institutional spot benchmark; **not** GLD/COMEX continuous) | *TBD* | *TBD* | Daily (fix days) | USD/troy oz | **Fixing date** (London PM auction date) | IBA benchmark | Not ALFRED-style unless licensed vintage feed | TBD in 5B once source locked | **UNRESOLVED** |
| DXY | ICE U.S. Dollar Index (6-currency basket, USDX) | *TBD* | *TBD* | Daily | Index points | Index **calculation date** | ICE publishes levels | TBD | TBD | **UNRESOLVED** |

---

## 4. WTI — LOCKED

### Definition

**West Texas Intermediate spot crude oil**, Cushing, Oklahoma, FOB — the EIA/FRED **cash-market reference**, not NYMEX CL front-month or continuous futures, not USO/UCO ETF NAV.

Includes negative prices when observed (e.g. April 2020); do not clip or substitute.

### Source selection

| Candidate | Verdict |
| --- | --- |
| **FRED DCOILWTICO** (EIA) | **SELECTED** — daily from 1986-01-02, USD/bbl, automatable via existing `FRED_API_KEY` |
| EIA API `PET.RWTC.D` | **Equivalent underlying** — acceptable fallback path via `EIA_API_KEY`; FRED preferred for consistency with macro stack |
| NYMEX CL futures / continuous | **Rejected** — futures, not spot reference |
| USO / XLE ETF | **Rejected** — ETF proxy, expense roll, not commodity spot |
| datahub.io oil CSV | **Rejected** — duplicate of EIA; no advantage over FRED API |

### Coverage

- **Start:** 1986-01-02 (not 1957 — pre-inception NULL/absent on spine)
- **Gaps:** Weekends/US holidays (no observation); occasional EIA missing days (`.`)
- **Negative prices:** Real (April 2020)

### Date semantics

Observation date = calendar date of the spot quote. Align like macro `observation_date`: store on row `date` only if that date ∈ `trading_days`.

---

## 5. XAU/USD — UNRESOLVED

### Definition (locked semantics; source not locked)

Canonical meaning: **USD price of one troy ounce of gold** using an institutional **spot benchmark**, not an ETF share price.

**Preferred benchmark when a licensed source exists:** **LBMA Gold Price PM fix** (USD/troy oz, London, ICE Benchmark Administration). This is a fixing benchmark, not a retail FX tick — but it is the standard defensible “spot gold” reference for historical research when true XAU/USD spot feeds are unavailable.

Explicitly **not**:

- GLD / IAU / SGOL (ETF proxies)
- COMEX GC front-month / continuous (futures)
- Synthetic retail FX “XAU/USD” scrapers without reproducible terms

### Source research

| Candidate | Authority | Automation | Reproducibility | Verdict |
| --- | --- | --- | --- | --- |
| FRED GOLDPMGBD228NLBM / GOLDAMGBD228NLBM | LBMA/IBA via FRED | Was API; **removed Jan 2022** (ICE license) | Was excellent | **Rejected** — no longer free API |
| LBMA / IBA direct | Gold standard | Licensed MyLBMA portal | Yes with license | **Blocked** — license required for redistribution/storage |
| ICE Benchmark Administration | Gold standard | Commercial license | Yes | **Blocked** — not free/automatable under V1 principles |
| UniRateAPI / metals APIs | Aggregator | Paid API | Depends on vendor | **Deferred** — third-party ToS; not locked without explicit approval |
| World Bank / IMF commodity series | Official | API | Often **monthly**, not daily spot | **Rejected** for daily XAU/USD intent |
| Kitco / Moody's (CPGLDPM) | Industry | Not free reproducible API | Redistribution unclear | **Rejected** |

### Outcome

**Definition locked; source UNRESOLVED.** Phase 5B must **not** ingest XAU/USD until an approved automatable source is selected (likely ICE/IBA license or explicitly approved paid feed with documented terms).

---

## 6. DXY — UNRESOLVED

### Definition (locked semantics; source not locked)

**ICE U.S. Dollar Index (USDX / DXY)** — geometric weighted index of EUR, JPY, GBP, CAD, SEK, CHF vs USD. Trademarks and methodology owned by **ICE Data Indices, LLC**.

Explicitly **not**:

- **DTWEXBGS** / **DTWEXAFEGS** (Fed trade-weighted dollar — 26 currencies, different basket/weights)
- **UUP** ETF (proxy, fees, tracking error)
- Generic “dollar strength” composites

### Source research

| Candidate | Semantic fit | Free API | Verdict |
| --- | --- | --- | --- |
| **ICE Data Indices / ICE Data API** | **Exact DXY** | **No** — commercial license | **Correct source but blocked** without license |
| FRED **DTWEXBGS** | Broad trade-weighted USD | Yes | **Rejected** — not DXY; must not label `DXY` |
| FRED **DTWEXAFEGS** | Advanced economies TWI | Yes | **Rejected** — not DXY |
| Yahoo / Stooq scraped DX-Y.NYB | DXY-like | Scraping | **Rejected** — not reproducible/authorized |
| UUP adjusted NAV | ETF proxy | Tiingo possible | **Rejected** — not the index |

### Coverage note

Even with ICE license, historical DXY daily index levels exist from ICE publication history (~1985+ for futures-related index); exact start depends on licensed ICE dataset. **Do not fabricate pre-inception history on the 1957 spine.**

### Outcome

**UNRESOLVED** — proceeding would require either ICE Data license or a deliberate project decision to add a **different** canonical dollar index under a **different** symbol (not `DXY`).

---

## 7. Historical coverage vs trading spine

| Asset | Earliest reliable | vs spine start 1957-01-02 |
| --- | --- | --- |
| WTI | 1986-01-02 | Absent before — **correct** |
| XAU/USD | ~1968 (LBMA fix history) if licensed | Absent before source start |
| DXY | ~1985–1986 (ICE index history) if licensed | Absent before source start |

Never backfill pre-inception values.

---

## 8. Schema & storage decision (Phase 5B prerequisite)

### Storage location

**Extend `daily_market_data`** — same `(date, symbol)` grain as ETFs.

Canonical symbols (internal):

```text
WTI
XAU/USD
DXY
```

### Single daily value vs OHLCV

**Decision: Option A with schema change**

- Store the canonical daily **level in `close`** (native units).
- **`open`, `high`, `low`, `volume`, all `adj_*`, `dividend_cash`, `split_factor` → NULL** for Phase 5 context assets.
- **Do NOT** set `open = high = low = close`.
- Requires Alembic migration relaxing NOT NULL constraints on observed columns (check constraints on `high >= low` must allow NULL legs).

### Adjustments

No splits/dividends/adjusted close for WTI, gold, or DXY. Adj columns NULL; not “copy of close”.

### Derived columns (`return_1d`, `gap_pct`, etc.)

Phase 5B must define close-only derive rules:

- `return_1d`: from **`close`** (only series available); NULL first row per symbol
- `gap_pct`, `intraday_return`, `range_pct`: **NULL** when OHLC incomplete
- `drawdown_from_high`: from **`close`** expanding max
- `market_outcomes` / `asset_regimes`: Phase 5B must use close-based paths or skip until defined — **out of Phase 5A scope**

---

## 9. Provider architecture (Phase 5B)

| Asset | Adapter | Credential |
| --- | --- | --- |
| WTI | Extend `providers/fred.py` (`fetch_current_observations("DCOILWTICO", ...)`) | `FRED_API_KEY` (existing) |
| WTI fallback | New thin `providers/eia.py` optional | `EIA_API_KEY` |
| XAU/USD | **Blocked** until source resolved | TBD |
| DXY | **Blocked** until ICE license or new decision | TBD |

CLI sketch (Phase 5B): extend or add `build_market_context.py` calling same upsert/validate patterns as ETFs — **not implemented in 5A**.

---

## 10. Provenance (Phase 5B must retain)

For each observation eventually stored:

```text
provider (fred | eia | ice | …)
series_id / instrument_id
request timestamp (build log)
observation date (source-native)
native units
normalization rule (e.g. "observation_date → trading_days.date")
StockBallDB symbol (WTI | XAU/USD | DXY)
```

No comprehensive raw archive in V1 — flag mutable FRED/EIA revisions for later snapshot phase.

---

## 11. Source evaluation (summary)

### WTI — DCOILWTICO

| Dimension | Rating |
| --- | --- |
| Authority | High (EIA primary, FRED distribution) |
| Semantic fit | High (spot Cushing WTI) |
| Historical depth | From 1986 |
| Daily coverage | Business days |
| Automation | High (FRED API) |
| Access stability | High |
| Licensing | Free FRED |
| Reproducibility | Current-source yes; exact snapshot no |
| Ongoing updates | Yes |

### XAU/USD — LBMA PM fix (intended)

| Dimension | Rating |
| --- | --- |
| Authority | High |
| Semantic fit | High for benchmark “spot gold” |
| Automation | **Blocked without IBA license** |
| Status | UNRESOLVED |

### DXY — ICE USDX

| Dimension | Rating |
| --- | --- |
| Authority | High (index owner) |
| Semantic fit | Exact if licensed |
| Automation | **Commercial ICE Data only** |
| Status | UNRESOLVED |

---

## 12. Rejected alternatives (explicit)

| Alternative | Why rejected |
| --- | --- |
| USO, GLD, UUP | ETF proxies — universe forbids when underlying exists |
| CL futures / GC futures | Futures ≠ locked spot/index definitions |
| DTWEXBGS, DTWEXAFEGS | Not DXY — different basket/methodology |
| FRED LBMA gold (removed) | API access withdrawn 2022 |
| open=high=low=close | Manufactures OHLC — forbidden |
| New table for 3 symbols | Unnecessary — extend `daily_market_data` with nullable OHLC |

---

## 13. Phase 5B readiness (per asset)

| Asset | Phase 5B |
| --- | --- |
| **WTI** | **IMPLEMENTED** (Phase 5B) — FRED DCOILWTICO |
| **XAU/USD** | **NOT READY** — source research / licensing required |
| **DXY** | **NOT READY** — ICE license or explicit alternate-index decision required |

---

## 15. Phase 5B — WTI implementation (2026-08-28)

**Status:** COMPLETE

- Migration `a8f3c2d1b4e5`: nullable OHLC/adj/corp-action + row-shape CHECK (full OHLC **or** close-only).
- Ingestion: `python -m stockballdb.build_wti` via FRED `DCOILWTICO`; **10,201** rows (`1986-01-02` → `2026-08-25`).
- Close-only derive: `return_1d`, `drawdown_from_high` from `close`; `gap_pct`/`intraday_return`/`range_pct` NULL; outcomes `max_up_*`/`max_down_*` NULL.
- Negative WTI preserved (`2020-04-20` = **-36.98**, matches FRED). Idempotent ×2; `validate_v1` PASS; pytest **90/90**.
- **30** FRED observations dropped (native date ∉ `trading_days`); no forward/back-fill.

**Done:** WTI canonical storage in `daily_market_data`; ETF integrity preserved via CHECK + asset-aware validation; audit script `scripts/phase5b_wti_audit.py`.

## 14. Phase 4C / regimes

Unchanged — regime re-lock remains optional Phase 4C. Phase 5 does not depend on it.
