# StockBallDB — Phase 6A Scheduled Events Source, Definition & PIT Contract

**Status:** LOCKED (design contract only — no ingestion changes in this phase)  
**Applies to:** `scheduled_events` and its relationship to `macro_conditions`, `calendar_context`, `trading_days`  
**Package version:** 1.0.0

Phase 6A locks **what counts as a scheduled event**, **which families belong in V1**, **authoritative sources**, **point-in-time semantics**, and **schema fit**. No PostgreSQL population or pipeline changes in this phase.

---

## 1. Audit — repository vs planning artifacts

### Authoritative state (implemented V1)

The **repository is authoritative**. Phase 2F already implemented `scheduled_events` acquisition, validation, and V1 build integration (`build_scheduled_events`, `sync_scheduled_events`).

| Area | Implemented truth |
| --- | --- |
| **Schema** | `event_id`, `event_type`, `event_date`, `symbol`, `reference_period`, `release_session`, `event_time_et`, `source` |
| **No FK** | `event_date` is a **calendar occurrence date** — not FK to `trading_days` |
| **V1 event types** | `fomc`, `cpi`, `employment_situation`, `election` |
| **Values** | Macro **values** live in `macro_conditions`; **not** duplicated in `scheduled_events` |
| **Calendar flags** | `calendar_context.is_*_day` derived from `scheduled_events` on matching trading dates |

### Mismatch with older planning sketches

Some early design notes referenced columns such as:

```text
importance, consensus, previous, surprise, actual, event_name
```

**These columns do not exist** in the V1 migration (`e5c83b2d4a16`), ORM, or builders. V1 deliberately deferred or rejected them (see §8). Phase 6A **does not reintroduce** them.

### Relationship to Phases 4–5

- **Phase 4A/4B:** `macro_conditions` holds PIT macro **state** on trading days; BLS release **occurrences** remain in `scheduled_events`.
- **Phase 5:** Market context (WTI) is unrelated to `scheduled_events`.

---

## 2. Schema column classification (actual V1)

| Column | Classification | Notes |
| --- | --- | --- |
| `event_id` | **CANONICAL FACT** | Deterministic identity (see §10) |
| `event_type` | **CANONICAL FACT** | Closed vocabulary per phase |
| `event_date` | **CANONICAL FACT** | Calendar occurrence date |
| `symbol` | **OPTIONAL METADATA** | V1: always `NULL` (market-wide) |
| `reference_period` | **CANONICAL FACT** | When semantically required (`YYYY-MM`, `presidential`, `midterm`) |
| `release_session` | **DERIVED FACT** | Coarse NYSE-session bucket from time + calendar rules |
| `event_time_et` | **CANONICAL FACT** (when asserted) | Local **America/New_York** clock time; `NULL` when unknown |
| `source` | **CANONICAL FACT** | Provenance tag for acquisition path |

### Columns from legacy sketches — not in schema

| Concept | Classification | Phase 6A decision |
| --- | --- | --- |
| `actual` | Would duplicate `macro_conditions` | **REJECTED** from `scheduled_events` |
| `previous` | Result/metadata | **REJECTED** — not schedule facts |
| `consensus` | Forecast / provider judgment | **REJECTED / UNRESOLVED** — no free reproducible historical source |
| `surprise` | **RESEARCH/INTERPRETATION** | **REJECTED** — derived from forecasts |
| `importance` | Subjective provider rating | **REJECTED** — no StockBallDB objective definition |
| `event_name` | Display text | **OPTIONAL METADATA** — defer; use `event_type` + `reference_period` |

---

## 3. Definition — what is a `scheduled_event`?

A **scheduled event** in StockBallDB is a **historically reconstructible occurrence** of a **systematically knowable** official publication or institutional calendar event that serves as **objective market context**.

### Inclusion criteria (all required)

1. **Identifiable event family** with stable semantics.
2. **Authoritative historical source** for occurrence date (and time when justified).
3. **Deterministic storage** — same inputs → same rows across rebuilds.
4. **Objective context** — not bullish/bearish, not strategy features, not experiment labels.

### Exclusion (do not store in `scheduled_events`)

```text
unexpected news, wars, disasters, company announcements, market crashes,
unscheduled political actions, analyst commentary, earnings (V1 deferred),
emergency Fed actions, consensus forecasts, surprise scores,
subjective importance ratings, market reaction labels
```

StockBallDB is **not** a generic news or catalyst database.

### Conceptual chain (Phase 6 scope)

```text
scheduled / knowable event  →  scheduled_events (occurrence calendar)
actual released values       →  macro_conditions (when applicable)
trading-day interpretation →  calendar_context (flags, days_since_*)
```

Phase 6A locks the **first** layer. It does **not** interpret outcomes.

---

## 4. Point-in-time contract

### Terminology

| Term | Meaning in StockBallDB |
| --- | --- |
| **reference_period** | What the release **covers** (e.g. CPI for `2020-02`, Q1 GDP) — **never** the event date |
| **event_date** | Calendar date of the **occurrence** StockBallDB stores |
| **event_time_et** | Local release clock time when confidently asserted (`America/New_York`) |
| **release_session** | Coarse market-session bucket: `pre_open`, `during_session`, `after_close`, `unknown` |
| **first-print / ALFRED `realtime_start`** | Earliest vintage publication date knowable from ALFRED — used for BLS releases in V1 |
| **scheduled_at (original announcement)** | When the public **first learned** the release would occur — **generally NOT reconstructible in V1** |

### What V1 can prove

| Family | What we store | PIT strength |
| --- | --- | --- |
| **FOMC** | Final scheduled meeting **decision/statement day** from Fed historical HTML | Strong for **occurrence date**; weak for original schedule-announcement history |
| **CPI / Employment** | **First ALFRED print date** per reference month | Strong for **first publication**; not full BLS pre-announcement calendar history |
| **Election** | Statutory Election Day | Strong — formulaically knowable in advance |

### What V1 cannot prove

- That a BLS release was **originally announced** for Date A before being rescheduled to Date B.
- Complete historical **08:30 ET** times before conventions were stable (V1 uses `NULL` time pre-1990 for BLS).
- Emergency Fed actions as “scheduled” events.

**Rule:** Do not fabricate `scheduled_at`, consensus, surprise, or importance.

### Schedule revisions

BLS publishes advance schedules (from 1961) and maintains `histreleasedates.pdf` with **actual** historical release dates (including documented reschedules, e.g. Oct 1998 Employment Situation). V1 builders currently use **ALFRED first-print** for CPI/Employment — equivalent to **actual first publication**, not the announced schedule at an earlier date.

Phase 6B may optionally add a BLS PDF path for occurrence dates where ALFRED coverage is thin; that remains an implementation choice, not a 6A schema change.

---

## 5. Timezone contract

- All asserted clock times are **`event_time_et`** = **U.S. Eastern Time** (`America/New_York`), including DST transitions.
- Never store naked `08:30` without this contract.
- When time is unknown, `event_time_et = NULL` and `release_session` reflects coarse knowledge (`pre_open` vs `unknown`).

### V1 time assertions

| Family | From | Session | Time (ET) |
| --- | --- | --- | --- |
| BLS CPI / Employment | 1990-01-01 | `pre_open` | `08:30` |
| BLS CPI / Employment | before 1990 | `pre_open` | `NULL` |
| FOMC decision | 2013-03-20 | `during_session` | `14:00` |
| FOMC decision | before 2013-03-20 | `unknown` | `NULL` |
| Election Day | all | `unknown` | `NULL` |

Fed statement time standardization reference: Federal Reserve Board, 2013-03-13.

---

## 6. Trading-day relationship

```text
scheduled_events.event_date  — calendar date (may be weekend/holiday)
trading_days.date            — NYSE trading sessions only
```

**No FK** from `event_date` → `trading_days`. Legitimate events on non-trading days must be preserved.

### `calendar_context` linkage (existing V1)

- **`is_fomc_day` / `is_cpi_release_day` / etc.:** true iff an event of that type has `event_date = trading_days.date` (same calendar date only).
- **`days_since_last_*`:** uses **effective session** — if `event_date` is not a trading day, effective session = first trading day **strictly after** `event_date`.
- Off-calendar events **do not** set `is_*_day` on the event calendar date; they affect retrospective distance from the effective session onward.

Phase 6A does **not** add forward `days_to_next_*` (deferred).

---

## 7. Event identity

Deterministic `event_id`:

```text
{event_type}:{event_date}:{reference_period_or_NA}:{symbol_or_MARKET}
```

Examples:

```text
fomc:2020-04-29:NA:MARKET
cpi:2020-03-11:2020-02:MARKET
employment_situation:2020-03-06:2020-02:MARKET
election:2020-11-03:presidential:MARKET
```

Uniqueness constraint (application layer): `(event_type, event_date, reference_period, symbol)`.

**Why not `(date, event_type)` alone?** Multiple reference months could theoretically collide on rare calendar edge cases; Employment and CPI are distinguished by `reference_period`. GDP advance/second/third on same day would require **`event_subtype`** (deferred column — see §16).

---

## 8. Actual values, consensus, surprise, importance

### `actual`

**REJECTED** in `scheduled_events`. Released macro values belong in `macro_conditions` (ALFRED/FRED PIT). Duplicating here would create competing truths.

### `consensus`

**UNRESOLVED / REJECTED for V1.** No free, historically reproducible, provider-neutral consensus archive approved. Consensus is forecast data, not official schedule fact. Absence must not block event ingestion.

### `surprise`

**REJECTED.** Derived interpretation (`actual - consensus`). Not an independent source fact. Experiment-agnostic foundation excludes it.

### `importance`

**REJECTED.** Provider star ratings and editorial “high/medium/low” are subjective. No objective StockBallDB definition locked in 6A.

---

## 9. Event family research & V1 classification

### A. FOMC / Federal Reserve — **LOCKED**

| Aspect | Decision |
| --- | --- |
| **Definition** | Regularly scheduled FOMC **meeting decision/statement day** (final day of multi-day meeting) |
| **Source** | Federal Reserve `fomchistorical{YYYY}.htm` (1957–2020), `fomccalendars.htm` (2021+) |
| **Exclude** | Unscheduled, conference call, notation vote, cancelled meetings |
| **Historical start** | **1957** (aligned with `COVERAGE_START`) |
| **Time** | 14:00 ET from 2013-03-20; else unknown |
| **Subtypes deferred** | Minutes release, press conference (separate occurrence types — Phase 6B+ ) |
| **Emergency actions** | **REJECTED** from `scheduled_events` |

### B. CPI — **LOCKED**

| Aspect | Decision |
| --- | --- |
| **Definition** | BLS CPI **news release occurrence** for a reference month |
| **Source (V1)** | ALFRED `CPIAUCSL` first-print `realtime_start` |
| **Reference period** | `YYYY-MM` (month of price index) |
| **Historical start** | Limited by ALFRED vintage depth (~1947 series; V1 filters from 1957) |
| **Time** | 08:30 ET from 1990-01-01; date-only before |
| **PIT limitation** | First publication date, not original BLS announced schedule |
| **Values** | In `macro_conditions` only |

Alternative authoritative path for Phase 6B: BLS `histreleasedates.pdf` / news release schedules.

### C. Employment Situation — **LOCKED**

| Aspect | Decision |
| --- | --- |
| **Definition** | Single scheduled **Employment Situation** release (NFP + unemployment rate + related tables) — **one event per reference month** |
| **Source (V1)** | ALFRED `UNRATE` first-print (proxy for release occurrence) |
| **Not separate events** | NFP level vs unemployment rate — same release |
| **Historical start** | ALFRED / BLS employment release history (~1957+) |
| **Time** | Same BLS convention as CPI |
| **ICSA / jobless claims** | **Different release** — not `employment_situation` |

### D. Jobless Claims — **PROVISIONALLY LOCKED** (Phase 6B candidate)

| Aspect | Decision |
| --- | --- |
| **Definition** | DOL ETA **Unemployment Insurance Weekly Claims** news release |
| **Source** | DOL ETA (weekly PDF archive); ALFRED `ICSA` first-print possible but sparse pre-2009 |
| **Schedule** | Thursday 08:30 ET; **exceptions** on federal holidays (DOL publishes exception list) |
| **Reference period** | Week ending (typically prior Saturday) — needs `YYYY-MM-DD` or week label in Phase 6B |
| **Status** | **PROVISIONALLY LOCKED** — strong official source; weekly grain and holiday exceptions require careful Phase 6B design |
| **Not in V1 today** | Deferred from Phase 2F scope |

### E. GDP — **DEFERRED**

| Aspect | Decision |
| --- | --- |
| **Definition** | BEA quarterly GDP estimate releases (advance, second, third) |
| **Source** | BEA release schedule + news releases |
| **Complexity** | Three distinct **subtypes** per quarter; annual/comprehensive revisions |
| **Status** | **DEFERRED** — needs `event_subtype` (`advance` / `second` / `third`) and reference quarter encoding |
| **Historical start** | BEA modern schedule well documented; deep history requires archive work |

### F. Other major releases — **DEFERRED**

| Candidate | Source | Verdict |
| --- | --- | --- |
| **PCE / Personal Income** | BEA | **DEFERRED** — often paired with GDP releases; scope overlap |
| **PPI** | BLS | **DEFERRED** — add only if BLS schedule path mirrors CPI |
| **Retail Sales** | Census | **DEFERRED** — separate agency pipeline |
| **ISM PMI** | ISM (private) | **DEFERRED** — not government primary; licensing/terms TBD |
| **JOLTS** | BLS | **DEFERRED** — 10:00 ET release; lower priority than CPI/NFP |
| **Consumer Confidence** | Conference Board | **DEFERRED** — private survey; reproducibility concerns |

Prefer **small, authoritative** universe over incomplete breadth.

### G. U.S. Elections — **LOCKED**

| Aspect | Decision |
| --- | --- |
| **Definition** | Federal general **Election Day** (presidential + midterm) |
| **Source** | Statutory formula (2 U.S.C. §7); `us_statutory_election_day` |
| **Historical start** | 1957+ even years in coverage window |
| **Time** | All-day statutory; `unknown` / NULL time |
| **vs `calendar_context`** | **Both:** `scheduled_events` holds occurrence; `calendar_context.is_election_day` flags trading-day match — not duplication of semantics, different grains |
| **Excluded** | Winners, parties, market reaction |

---

## 10. Source hierarchy

```text
1. Primary agency (Fed, BLS, BEA, DOL, statutory law)
2. ALFRED/FRED (when mapping to official first-print vintage dates)
3. Agency historical PDFs / schedule pages
4. — REJECTED: scraped economic calendars, consensus vendors, news aggregators
```

Evaluate on: authority, historical depth, calendar availability, time metadata, automation, reproducibility, revision behavior.

---

## 11. Historical coverage (expected)

| Family | Earliest reliable occurrence history | Time metadata | Known gaps |
| --- | --- | --- | --- |
| **FOMC** | 1957 | 14:00 ET from 2013 only | Pre-2013 intraday unknown |
| **CPI** | ~1957 (ALFRED) / 1953 (BLS PDF) | 08:30 ET from 1990 | ALFRED sparse early vintages; revision dates excluded |
| **Employment** | ~1957 | 08:30 ET from 1990 | Same as CPI |
| **Election** | 1958 (first even year ≥1957) | None | Odd years correctly absent |
| **Jobless claims** | ~1980s DOL archive / 1967 ICSA | 08:30 ET modern | Pre-2009 ALFRED PIT sparse; holiday moves |
| **GDP** | ~1990s BEA schedule | 08:30 ET modern | Subtype complexity |

**No 1957 claim** for families whose authoritative history starts later. Absence = unknown outside validated coverage, not “no event.”

---

## 12. Proposed V1 event universe summary

| Event Family | Status | Phase 6B |
| --- | --- | --- |
| FOMC decision day | **LOCKED** | **READY** (already implemented; re-validate) |
| CPI release | **LOCKED** | **READY** |
| Employment Situation | **LOCKED** | **READY** |
| U.S. Election Day | **LOCKED** | **READY** |
| Jobless Claims | **PROVISIONALLY LOCKED** | Design + ingest in 6B |
| GDP (advance/second/third) | **DEFERRED** | Needs subtype schema |
| FOMC minutes / press conf. | **DEFERRED** | Separate subtypes |
| PCE, PPI, Retail, JOLTS, ISM, Consumer Confidence | **DEFERRED** | — |
| Emergency Fed actions | **REJECTED** | Different future table if ever |
| Earnings | **REJECTED** (V1) | ETF universe mismatch |
| Consensus / surprise / importance | **REJECTED** | — |

---

## 13. Schema recommendation

### Current schema (sufficient for LOCKED V1 four-family universe)

```text
event_id             TEXT PK
event_type           TEXT NOT NULL
event_date           DATE NOT NULL   -- no trading_days FK
symbol               TEXT NULL
reference_period     TEXT NULL
release_session      TEXT NOT NULL
event_time_et        TIME NULL
source               TEXT NOT NULL
```

**Phase 6A: no migration required.**

### Optional Phase 6B extensions (only if DEFERRED families unlock)

| Addition | When needed |
| --- | --- |
| `event_subtype` | GDP advance/second/third; FOMC minutes vs decision |
| `reference_period` format docs | Week-ending date for jobless claims (`YYYY-MM-DD`) |
| `source_identifier` | Explicit URL/series/dataset id (currently embedded in `source` enum) |

Do **not** add: `actual`, `consensus`, `surprise`, `importance`, `event_name` unless a future phase explicitly reverses this contract.

---

## 14. Phase 6B provenance requirements

Each ingested row must be traceable to:

```text
source organization     (Federal Reserve, BLS via ALFRED, statutory)
source dataset/series     (CPIAUCSL, UNRATE, fomchistorical2020.htm, …)
retrieval timestamp       (build log)
event_date / event_time_et
reference_period (if any)
normalization rule        (e.g. "FOMC multi-day → final day", "ALFRED min realtime_start")
StockBallDB event_id
```

Flag mutable agency web pages for future snapshot phase. No comprehensive immutable archive in 6B unless already required by V1 patterns.

---

## 15. Relationship to existing pipelines

| Component | Role |
| --- | --- |
| `build_scheduled_events` | Acquisition orchestrator (exists; do not re-run in 6A) |
| `macro_conditions` | PIT macro values; CPI/UNRATE levels |
| `calendar_context` | Trading-day flags and `days_since_last_*` |
| `validate_v1` | Cross-table checks including event-flag counts vs on-calendar events |

Phase 4A documents alignment: macro PIT `realtime_start` should be **consistent with** but not duplicated as first-print dates in `scheduled_events`.

---

## 16. Unresolved issues (explicit)

1. **Original schedule vs actual release:** V1 stores occurrence (Fed pages / ALFRED first print), not “when first scheduled.”
2. **BLS historical times pre-1990:** Date known; clock time not asserted.
3. **Jobless claims weekly grain + holiday exceptions:** Needs Phase 6B reference-period convention.
4. **GDP tri-estimate subtypes:** Needs schema extension before lock.
5. **Consensus/surprise:** No V1 path without paid/non-reproducible vendors.
6. **ISM / Conference Board:** Private sources — not locked.

---

## 17. Rejected alternatives

| Alternative | Reason |
| --- | --- |
| FK `event_date` → `trading_days` | Drops legitimate weekend/holiday events |
| Store macro `actual` in events | Duplicates `macro_conditions` |
| Scraped TradingEconomics / investing.com calendars | Not authoritative |
| Emergency Fed as `fomc` | Mislabels unscheduled actions |
| Separate NFP vs UNRATE events | Same Employment Situation release |
| `open=high=low=close` style fabrication | N/A here; same principle — no invented fields |
| importance / surprise columns | Subjective or derived |

---

## 18. Phase 6B readiness

| Family | Ready for Phase 6B ingestion? |
| --- | --- |
| FOMC | **YES** — re-validate existing pipeline against this contract |
| CPI | **YES** |
| Employment Situation | **YES** |
| Elections | **YES** |
| Jobless Claims | **YES (after subtype/reference-period spec in 6B open)** |
| GDP | **NO** — schema + subtype design first |
| All others | **NO** |

Phase 6B may run full `build_scheduled_events` + dependent `calendar_context` resync if spine advances — not in 6A.

---

## 19. Phase 6B verification (execution record)

**Status:** COMPLETE (2026-08-28)

### Database result

| Event family | Rows | First | Last |
| --- | ---: | --- | --- |
| FOMC | 711 | 1957-01-08 | 2026-07-29 |
| CPI | 954 | 1972-07-21 | 2026-08-12 |
| Employment Situation | 942 | 1960-03-15 | 2026-08-07 |
| U.S. Election Day | 34 | 1958-11-04 | 2024-11-05 |
| **Total** | **2,641** | — | — |

Integrity: 0 duplicate `event_id`; 0 duplicate canonical occurrences; 37 events on non-trading days preserved (no FK to `trading_days`).

### Historical coverage notes

- **FOMC:** Full scheduled-meeting span from 1957 per Fed historical pages + `fomccalendars.htm` (2021+). Pre-2013 `event_time_et` NULL; 14:00 ET from 2013-03-20. Parser hardening fixed under-count of 2021+ calendar rows (`Apr/May`, asterisk dates).
- **CPI:** ALFRED `CPIAUCSL` first-print floor at **1972-07-21** — expected, not a pipeline defect vs ~1957 aspiration.
- **Employment:** ALFRED `UNRATE` first-print floor at **1960-03-15** — expected vintage depth limit.
- **Election:** Even-year federal general elections only; 1958–2024 (17 midterms + 17 presidential cycles).

### Non-trading-day / calendar_context

Off-calendar events remain on actual calendar dates. `calendar_context` maps `days_since_last_*` to the **first trading day strictly after** the event (e.g. election 1958-11-04 → effective session 1958-11-05, `days_since_last_election=0`).

### Idempotency

`build_scheduled_events` run 1 = run 2 = **2,641** rows; internal double-upsert unchanged. `build_calendar_context` ×2 = **17,532** rows unchanged.

### Validation

Event validators + `validate_v1` **PASS**; pytest **90/90 PASS**.

### Phase 6B code change

Only production fix: `src/stockballdb/events/fomc.py` row-wise `fomccalendars.htm` parser (`Apr/May`, `19-20*`, cross-row bleed). Audit script: `scripts/phase6b_scheduled_events_audit.py`.

No contract amendments required beyond this verification record.
