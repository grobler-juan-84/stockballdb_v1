# StockBallDB — Phase 7A Calendar Context Contract

**Version:** 1.0  
**Status:** LOCKED (audit + definition)  
**Date:** 2026-08-29  
**Scope:** `calendar_context` table only — audit, boundary, derivation semantics, PIT classification. No schema migration in 7A.

> Companion: [schema](StockBallDB_schema.md) · [definitions §7](StockBallDB_definitions.md#7-calendar_context) · [Phase 6A scheduled events](StockBallDB_phase6a_scheduled_events_contract.md)

---

## 1. Purpose and boundary

### 1.1 Purpose

`calendar_context` stores **deterministic, objective contextual relationships** for each StockBallDB **trading session** (`trading_days.date`).

It answers:

```text
Where does this trading day sit in calendar/session geometry?
What scheduled events occurred on this calendar date (if any)?
How many trading sessions have elapsed since the last effective event anchor?
```

It does **not** answer:

```text
How did the market react?
Was this day bullish?
What strategy signal applies?
What will happen at the next event?
When was a future event first knowable to participants?
```

StockBallDB remains experiment-agnostic, strategy-agnostic, and prediction-agnostic.

### 1.2 Grain and lineage

| Property | Value |
| --- | --- |
| Grain | One row per `trading_days.date` (exact 1:1) |
| PK / FK | `date` PK; FK → `trading_days.date` |
| Build | `python -m stockballdb.build_calendar_context` |
| Resync trigger | After `trading_days` or `scheduled_events` rebuild |

**Lineage preference:** External facts enter through canonical tables first; `calendar_context` derives relationships only. The sole external metadata path is pinned NYSE calendar rules (`pandas_market_calendars`) used for holiday adjacency and early closes — not stored as a separate acquisition table.

### 1.3 Verified checkpoint (Phase 7A audit)

```text
calendar_context rows = 17,532  (1:1 trading_days, 1957-01-02 → 2026-08-28)
scheduled_events rows = 2,641
validate_v1 = PASS
pytest = 90/90 PASS
```

---

## 2. `trading_days` vs `calendar_context` ownership

### 2.1 Principle

> **`trading_days`** owns intrinsic properties of a valid market session.  
> **`calendar_context`** owns contextual relationships derived from the spine, NYSE session metadata, and `scheduled_events`.

Do not duplicate spine fields in `calendar_context` without a compelling canonical reason. V1 follows this rule.

### 2.2 `trading_days` (intrinsic — do not duplicate)

| Column | Meaning |
| --- | --- |
| `date` | Valid NYSE trading session |
| `weekday` | ISO weekday (Mon=1 … Fri=5) |
| `month`, `quarter`, `year` | Calendar decomposition |
| `day_of_month` | Calendar day 1–31 |
| `week_of_year` | ISO 8601 week number |
| `trading_day_of_month` | Ordinal session within calendar month (1 = first) |
| `trading_day_of_year` | Ordinal session within calendar year |
| `days_to_month_end` | Remaining trading sessions after today until month-end session (0 on month-end) |
| `is_month_end` | Last trading session of calendar month |
| `is_quarter_end` | Last trading session of calendar quarter |
| `is_year_end` | Last trading session of calendar year |
| `prev_trading_date`, `next_trading_date` | Spine navigation |

**Important distinction (locked):**

```text
calendar month end     ≠  last trading session of month
calendar quarter end   ≠  last trading session of quarter
calendar year end      ≠  last trading session of year
```

Boundary flags in `trading_days` always refer to **trading sessions**, never naive calendar last-days.

### 2.3 `calendar_context` (contextual — current V1)

Holiday/session geometry, ISO-week session counts, narrow period transitions, retrospective scheduled-event flags and distances.

---

## 3. Current schema inventory

Every V1 column with exact semantics.

| Column | Type | NULL | Source inputs | Derivation rule |
| --- | --- | --- | --- | --- |
| `date` | DATE PK/FK | NO | `trading_days.date` | 1:1 copy |
| `is_day_before_holiday` | BOOLEAN | NO | `prev/next_trading_date`, NYSE catalog | TRUE iff ∃ closed weekday strictly between `date` and `next_trading_date` |
| `is_day_after_holiday` | BOOLEAN | NO | same | TRUE iff ∃ closed weekday strictly between `prev_trading_date` and `date` |
| `holiday_name` | TEXT | YES | NYSE regular + adhoc rules | Pipe-joined unique closure label(s) when before/after; else NULL |
| `holiday_type` | TEXT | YES | NYSE adhoc vs regular | `regular` \| `exceptional` when before/after; else NULL |
| `is_shortened_trading_day` | BOOLEAN | NO | NYSE `early_closes` | TRUE iff `date` is a scheduled early-close session |
| `is_shortened_week` | BOOLEAN | NO | ISO week session count | TRUE iff `trading_days_in_week < 5` |
| `trading_days_in_week` | SMALLINT | NO | ISO `(iso_year, iso_week)` | Count of spine sessions sharing ISO week with `date` (1–5) |
| `is_turn_of_month` | BOOLEAN | NO | `trading_days` | `is_month_end OR trading_day_of_month = 1` |
| `is_quarter_transition` | BOOLEAN | NO | `trading_days` | `is_quarter_end OR first spine session of calendar quarter` |
| `is_year_transition` | BOOLEAN | NO | `trading_days` | `is_year_end OR first spine session of calendar year` |
| `is_fomc_day` | BOOLEAN | NO | `scheduled_events` | TRUE iff ∃ `fomc` with `event_date = date` |
| `days_since_last_fomc` | SMALLINT | YES | events + spine index | Trading-session distance from latest effective FOMC anchor ≤ `date`; NULL before first |
| `is_cpi_release_day` | BOOLEAN | NO | `scheduled_events` | TRUE iff ∃ `cpi` with `event_date = date` |
| `days_since_last_cpi` | SMALLINT | YES | events + spine index | Same pattern for CPI |
| `is_employment_situation_day` | BOOLEAN | NO | `scheduled_events` | TRUE iff ∃ `employment_situation` with `event_date = date` |
| `days_since_last_employment_situation` | SMALLINT | YES | events + spine index | Same pattern for employment |
| `is_election_day` | BOOLEAN | NO | `scheduled_events` | TRUE iff ∃ `election` with `event_date = date` |
| `days_since_last_election` | SMALLINT | YES | events + spine index | Same pattern for election |

### 3.1 Implementation references

| Component | Path |
| --- | --- |
| ORM | `src/stockballdb/models/calendar_context.py` |
| Derivation | `src/stockballdb/calendar_context/derive.py` |
| Holiday metadata | `src/stockballdb/calendar_context/holidays.py` |
| Validation | `src/stockballdb/calendar_context/validate.py` |
| CLI | `src/stockballdb/build_calendar_context.py` |
| Migration | `alembic/versions/f6d94c3e5b27_create_calendar_context.py` |
| Unit tests | `tests/test_calendar_context.py` |
| Cross-table | `src/stockballdb/validate_v1.py` (flag counts vs on-calendar events) |

---

## 4. Derivation definitions (locked)

### 4.1 Holiday adjacency

**Holiday / full closure:** A Mon–Fri calendar date with **no** `trading_days` row. Weekends alone are **not** holidays.

```text
is_day_before_holiday(date):
  next = trading_days.next_trading_date(date)
  closed_weekdays in (date, next) ≠ ∅

is_day_after_holiday(date):
  prev = trading_days.prev_trading_date(date)
  closed_weekdays in (prev, date) ≠ ∅
```

`holiday_name`: chronologically ordered unique labels from `resolve_gap_closures`, joined with `|`.  
`holiday_type`: `exceptional` if any adjacent closure is adhoc/exceptional; else `regular`.

**Weekend-only gaps** (e.g. Fri → Mon): both flags FALSE; `holiday_name` NULL.

### 4.2 Shortened sessions

```text
is_shortened_trading_day = date ∈ NYSE.early_closes(schedule)
```

Full closures are **not** shortened sessions. Early-close time-of-day is **not** modeled in V1.

### 4.3 Week definition (locked)

StockBallDB uses **ISO 8601 week identity**:

```text
(iso_year, iso_week) = date.isocalendar()[:2]
```

**Not** `(trading_days.year, week_of_year)` for week grouping.

```text
trading_days_in_week = |{ d ∈ trading_days : d.isocalendar()[:2] == (iso_year, iso_week) }|
is_shortened_week = trading_days_in_week < 5
```

Half-sessions count as one trading day. Thanksgiving-short weeks may show 3–4 sessions; ISO year-boundary weeks may span calendar years (tested: 2024-12-30 – 2025-01-03 in ISO week 1 of 2025).

This is an **NYSE trading-week session count keyed by ISO week**, not a naive Mon–Fri calendar week.

### 4.4 Period transitions (narrow)

```text
is_turn_of_month =
  trading_days.is_month_end OR trading_day_of_month = 1

is_quarter_transition =
  trading_days.is_quarter_end OR date = first trading session in (year, quarter)

is_year_transition =
  trading_days.is_year_end OR date = first trading session in year
```

These flag **transition proximity** on the trading spine — not calendar effects, seasonality, or performance labels.

### 4.5 Same-day event flags (locked)

```text
is_*_day(date) = TRUE  ⟺  scheduled_events has matching event_type with event_date = date
```

**Rules:**

- Comparison is **exact calendar equality** on the trading spine date.
- Off-calendar events **never** set `is_*_day` on any trading row.
- Multiple families may be TRUE simultaneously (47 multi-family trading days in current DB; e.g. FOMC + Employment).
- Flags are **independent** — not mutually exclusive.

### 4.6 Effective session (locked)

For each scheduled event occurrence `E` with calendar date `event_date`:

```text
if event_date ∈ trading_days:
    effective_session(E) = event_date
else:
    effective_session(E) = min{ d ∈ trading_days : d > event_date }
    (NULL if no such d exists within spine)
```

**Verified example (Phase 6B):**

```text
Election 1958-11-04  (not a trading day)
effective session    1958-11-05
1958-11-05: is_election_day = FALSE, days_since_last_election = 0
```

This rule applies **consistently to all four V1 event families** (FOMC, CPI, Employment, Election). No family-specific exceptions.

Duplicate effective sessions from multiple off-calendar events collapsing to the same anchor are deduplicated before distance indexing.

### 4.7 `days_since_last_*` (locked)

**Unit:** StockBallDB **trading sessions** (spine index difference), not calendar days.

```text
Let eff[] = sorted unique effective_session dates for event type T, within spine.

days_since_last_T(date) =
  if no eff[j] ≤ date: NULL
  else: index(date) - index(eff[latest j where eff[j] ≤ date])
```

**Same-day / effective-session behavior:**

```text
On effective session T:     days_since = 0
Next trading session T+1:   days_since = 1
```

**Off-calendar event** with effective session `T`: same as above; the calendar event date itself has no row.

**NULL before history floor:** See §6.

### 4.8 Release session — explicit non-use in calendar_context

`scheduled_events.release_session` (`pre_open`, `during_session`, `after_close`, `unknown`) is **not** consulted by `calendar_context` derivation.

**Locked semantic classification:**

| Layer | What it represents |
| --- | --- |
| `calendar_context` | **Calendar-date contextual** — occurrence on calendar date and trading-session distance from effective anchor |
| `macro_conditions` | **Session-availability contextual (PIT)** — when macro values are available to a trading session |
| `scheduled_events` | **Intrinsic occurrence facts** — calendar date, clock time, release session label |

**Example:** CPI release 2020-03-11 at 08:30 ET on a trading day:

```text
scheduled_events: event_date=2020-03-11, release_session=pre_open
calendar_context: is_cpi_release_day=TRUE on 2020-03-11; days_since_last_cpi=0
macro_conditions: inflation available per Phase 4A pre-open alignment rules
```

A hypothetical `after_close` event on date `D` would still set `is_*_day=TRUE` on `D` if `D` is a trading day; calendar_context does **not** shift distance anchors to `D+1` based on release session. Session-availability semantics belong elsewhere.

**Phase 7A decision:** Do not add release-session-aware distance logic to `calendar_context` in 7B without a new explicit contract amendment.

---

## 5. Event history floors and NULL behavior

Event families start at different dates. **Do not fabricate** pre-history anchors.

| Family | First canonical event | First `days_since_last_*` non-NULL | Notes |
| --- | --- | --- | --- |
| FOMC | 1957-01-08 | 1957-01-08 | Aligns with spine start |
| CPI | 1972-07-21 | 1972-07-21 | NULL on all prior trading days (e.g. 1957-01-02 → NULL) |
| Employment | 1960-03-15 | 1960-03-15 | NULL before first employment release |
| Election | 1958-11-04 (calendar) | **1958-11-05** (effective session) | Off-calendar first event |

Before each family's floor:

```text
is_*_day = FALSE
days_since_last_* = NULL
```

---

## 6. Future event distances — REJECTED for V1

### 6.1 Decision

```text
days_until_next_*  →  REJECTED for V1 calendar_context
```

### 6.2 Reasoning

| Concern | Assessment |
| --- | --- |
| A. Neutral ex-post calendar structure | Deterministic today from full occurrence calendar |
| B. False PIT knowability | **High risk** — Phase 6A established complete historical *scheduled-at* knowledge is generally unavailable |
| C. Naming/metadata fix | Insufficient — misuse risk outweighs convenience |

Forward distances would embed **future occurrence dates** into every historical row. Even if labeled ex-post, consumers could treat them as contemporaneous knowledge. Phase 2G/6A explicitly deferred forward columns; validation forbids `days_to_next_*` columns.

**Alternative:** Compute ex-post in research queries when explicitly labeled non-PIT, or defer to a future phase with `ex_post_days_until_next_*` naming and documented misuse guards.

---

## 7. PIT classification

| Field | Classification | Rationale |
| --- | --- | --- |
| `date` | PIT SAFE | Spine identity |
| `is_day_before_holiday`, `is_day_after_holiday` | PIT SAFE | Known exchange schedule + closure history |
| `holiday_name`, `holiday_type` | PIT SAFE | Same |
| `is_shortened_trading_day`, `is_shortened_week`, `trading_days_in_week` | PIT SAFE | Exchange schedule geometry |
| `is_turn_of_month`, `is_quarter_transition`, `is_year_transition` | EX-POST CALENDAR FACT | Deterministic calendar/trading structure; not a performance label |
| `is_*_day` (on-calendar events) | PIT SAFE | Calendar occurrence on that date is knowable on/after that date |
| `days_since_last_*` | PIT SAFE (retrospective) | Counts trading sessions since last **known past** effective anchor; NULL before history floor |
| `days_until_next_*` | **PIT UNSAFE / REJECT** | See §6 |
| Monday effect, turn-of-month effect, Santa Claus rally, event drift, impact scores | **PIT UNSAFE / REJECT** | Research constructs — never in StockBallDB |

**Distinction:**

```text
PIT SAFE              = reasonable contemporaneous historical context
EX-POST CALENDAR FACT = objectively true calendar geometry, not a trading belief
PIT UNSAFE / REJECT   = future-dependent knowability or research interpretation
```

Deterministic derivation today ≠ historically knowable at the time.

---

## 8. Field classification table

### 8.1 Existing columns

| Field | Status | Reason |
| --- | --- | --- |
| `date` | **LOCK EXISTING** | PK/FK spine join |
| `is_day_before_holiday` | **LOCK EXISTING** | Objective closure adjacency |
| `is_day_after_holiday` | **LOCK EXISTING** | Same |
| `holiday_name` | **LOCK EXISTING** | Adjacent closure label(s); not a full holiday catalog |
| `holiday_type` | **LOCK EXISTING** | Regular vs exceptional closure |
| `is_shortened_trading_day` | **LOCK EXISTING** | NYSE early close membership |
| `is_shortened_week` | **LOCK EXISTING** | Derived identity from `trading_days_in_week < 5` |
| `trading_days_in_week` | **LOCK EXISTING** | ISO-week session count |
| `is_turn_of_month` | **LOCK EXISTING** | Narrow transition flag; not "turn-of-month effect" |
| `is_quarter_transition` | **LOCK EXISTING** | Quarter boundary proximity |
| `is_year_transition` | **LOCK EXISTING** | Year boundary proximity |
| `is_fomc_day` | **LOCK EXISTING** | Same-day calendar occurrence |
| `days_since_last_fomc` | **LOCK EXISTING** | Retrospective trading-session distance |
| `is_cpi_release_day` | **LOCK EXISTING** | Same |
| `days_since_last_cpi` | **LOCK EXISTING** | Same |
| `is_employment_situation_day` | **LOCK EXISTING** | Same |
| `days_since_last_employment_situation` | **LOCK EXISTING** | Same |
| `is_election_day` | **LOCK EXISTING** | Same |
| `days_since_last_election` | **LOCK EXISTING** | Same |

### 8.2 Candidates considered — not in schema

| Candidate | Status | Reason |
| --- | --- | --- |
| `weekday`, `month`, `quarter`, `year` | **REJECT** (in `trading_days`) | Duplication |
| `trading_day_of_month`, `trading_day_of_year` | **REJECT** (in `trading_days`) | Duplication |
| `days_to_month_end` | **REJECT** (in `trading_days`) | Duplication |
| `trading_day_of_quarter` | **DEFER** | Useful; derivable from spine at query time |
| `trading_days_remaining_in_week/month/quarter/year` | **DEFER** | Partially covered by `days_to_month_end`; remainder derivable |
| `trading_days_since_month_start` | **USEFUL BUT REDUNDANT** | Equals `trading_day_of_month - 1` |
| `days_until_next_*` | **REJECT** | PIT-unsafe / misuse risk (§6) |
| Generic standalone holiday label on every row | **REJECT** | Adds little beyond adjacency + spine |
| `is_payday_period`, tax deadlines | **REJECT** | Not foundational; research-specific |
| Options expiration / triple witching | **DEFER** | Requires separate authoritative calendar source |
| Earnings season windows | **REJECT** | Research-specific; earnings not in V1 events |
| Event impact / surprise / importance | **REJECT** | Phase 6A rejected |
| Monday effect / turn-of-month effect / Santa Claus rally | **REJECT** | Research constructs |
| `is_event_week` / broad pre-post windows | **DEFER** | Window catalog out of V1 scope |
| Early-close session end time | **DEFER** | Not modeled; flag-only in V1 |
| Exchange session hours database | **REJECT** | Out of Phase 7 scope |

---

## 9. Redundancy audit

| Pair | Verdict |
| --- | --- |
| `trading_day_of_month` vs `days_to_month_end` | Equivalent offset (`days_to_month_end = last_ordinal - trading_day_of_month`); **only in `trading_days`** |
| `is_shortened_week` vs `trading_days_in_week` | **Keep both** — boolean convenience + ordinal; identity validated |
| `is_month_end` vs `is_turn_of_month` | **Not redundant** — transition flag includes month-start sessions |
| `is_*_day` vs `days_since_last_*=0` | **Keep both** — same-day flag explicit; distance NULL before first event |

No redundant pairs justify removal. No new redundant fields recommended for 7B.

---

## 10. Historical calendar behavior

| Topic | V1 behavior |
| --- | --- |
| Spine start | 1957-01-02 |
| Exceptional closures | 9/11 week, etc. → `holiday_type=exceptional` |
| Early closes | Flag only; no intraday hour modeling |
| Leap years | Standard calendar arithmetic via Python `date` |
| DST | Irrelevant to `calendar_context` columns (date-level only); event clock times in `scheduled_events` |
| Pre-1957 history | Out of scope — no rows |
| Modern vs historical holidays | Pinned NYSE calendar rules + adhoc list |

**Limitation (documented):** `calendar_context` does not encode partial-session availability times for early closes. `is_shortened_trading_day` is boolean membership only.

---

## 11. Phase 7B schema recommendation

```text
Current calendar_context schema is SUFFICIENT for the locked Phase 7A contract.
Phase 7B requires NO migration.
```

Phase 7B scope: **implementation verification and hardening** — re-derive, validate invariants, confirm idempotency, extend tests where gaps exist. Do not add columns unless execution proves a locked assumption wrong.

---

## 12. Phase 7B validation contract

Phase 7B must prove at minimum:

| # | Invariant |
| --- | --- |
| 1 | `COUNT(calendar_context) = COUNT(trading_days)` |
| 2 | Exact date set match with `trading_days` (ordered) |
| 3 | No orphan or duplicate `date` |
| 4 | All NOT NULL boolean columns populated |
| 5 | `holiday_name` NULL ⟺ neither before nor after holiday |
| 6 | `holiday_type` ∈ {NULL, `regular`, `exceptional`} |
| 7 | `1 ≤ trading_days_in_week ≤ 5` |
| 8 | `is_shortened_week = (trading_days_in_week < 5)` |
| 9 | `is_shortened_trading_day` = NYSE early_closes ∩ spine |
| 10 | Each `is_*_day` TRUE count = on-calendar `scheduled_events` distinct dates for that type |
| 11 | Off-calendar events: effective session gets `days_since=0`; no `is_*_day` on spine for raw event date |
| 12 | `days_since_last_*` NULL before family history floor |
| 13 | `days_since_last_*` non-negative integers when present |
| 14 | No `days_to_next_*` / forward columns |
| 15 | Multi-family same-day flags independent (no forced exclusivity) |
| 16 | Idempotent rebuild: row count and content stable across two runs |
| 17 | Rebuild does not mutate other canonical tables |
| 18 | `validate_v1` PASS after resync |
| 19 | Full pytest PASS |

**Useful cross-table checks (already partially in `validate_v1`):**

- Event flag counts vs `scheduled_events JOIN trading_days`
- Fingerprint stability of peer tables during calendar build

---

## 13. Rejected / deferred concepts (summary)

**Rejected:** market seasonality labels; event impact scores; forward event distances; generic holiday column without adjacency; duplicating `trading_days` ordinals; earnings/event windows; PIT-unsafe future schedule embedding.

**Deferred:** `trading_day_of_quarter`; remaining-in-period ordinals; options expiration calendar; early-close clock times; broad event windows; `days_until_next_*` with explicit ex-post naming (future phase only).

---

## 14. Relationship to other tables

```text
trading_days ──────────────────────► calendar_context (geometry, transitions)
scheduled_events ──► effective_session ──► days_since_last_*
scheduled_events ──► event_date = date ──► is_*_day (on-calendar only)
NYSE calendar metadata ──► holiday_* , is_shortened_*
macro_conditions ──► separate PIT availability (not calendar_context)
```

After `build_scheduled_events`, run `build_calendar_context` to resync event-derived fields.

---

## 15. Phase 7A completion

| Item | Result |
| --- | --- |
| Audit | Complete against live implementation |
| Contract | This document |
| Schema change | None |
| Behavior change | None |
| Phase 7B | Verification/hardening only |

**Recommendation:** Existing implementation already matches this contract. Phase 7B should focus on formal verification, audit script, idempotency proof, and closeout — not redesign.

---

## 16. Phase 7B verification (execution record)

**Status:** COMPLETE (2026-08-29)

### Database result

```text
calendar_context rows = 17,532
first date          = 1957-01-02
last date           = 2026-08-28
schema columns      = 19 (date + 18 context fields)
```

1:1 with `trading_days`; no schema migration.

### Invariant audit (19/19 PASS)

| # | Invariant | Result |
| --- | --- | --- |
| 1 | 1:1 grain with trading_days | PASS |
| 2 | No duplicated trading_days fields | PASS |
| 3 | Holiday adjacency (weekend / regular / exceptional spot checks) | PASS |
| 4 | Holiday metadata consistency | PASS |
| 5 | Shortened days = NYSE early_closes ∩ spine (481) | PASS |
| 6 | ISO week geometry + shortened_week identity | PASS |
| 7 | is_turn_of_month | PASS |
| 8 | is_quarter_transition | PASS |
| 9 | is_year_transition | PASS |
| 10 | Same-day flags IFF on-calendar event | PASS |
| 11 | Flag counts = distinct on-calendar events | PASS |
| 12 | Effective session (incl. 1958-11-04 election) | PASS |
| 13 | days_since trading-session distance | PASS |
| 14 | History floors (CPI/Employment/Election) | PASS |
| 15 | Multi-family dates (47 independent flags) | PASS |
| 16 | Release session does not alter calendar_context | PASS |
| 17 | No forward event distance columns | PASS |
| 18 | Deterministic rebuild (hash stable) | PASS |
| 19 | validate_v1 + build validator integration | PASS |

Audit script: `scripts/phase7b_calendar_context_audit.py`.

### Event coverage (Phase 6B DB)

| Family | Total | On-calendar (distinct dates) | Off-calendar | Flag TRUE |
| --- | ---: | ---: | ---: | ---: |
| FOMC | 711 | 709 | 2 | 709 |
| CPI | 954 | 644 | 5 | 644 |
| Employment | 942 | 776 | 21 | 776 |
| Election | 34 | 25 | 9 | 25 |
| **Off-calendar total** | — | — | **37** | — |

Note: CPI/Employment row totals exceed distinct on-calendar dates when multiple canonical rows share a release date (distinct reference periods are separate `scheduled_events` rows; calendar flags are per calendar date).

### Idempotency

`build_calendar_context` run 1 = run 2 = **17,532** rows; internal double-upsert unchanged; SHA256 snapshot stable across rebuild.

### Validation

`validate_v1` **PASS**; pytest **92/92 PASS**.

### Phase 7 closeout

**PHASE 7 = COMPLETE.** No contract amendments required. **NEXT:** Phase 8 — Validation & Provenance Hardening (not started).
