# StockBallDB — V2 Decisions

**Purpose:** Decision log for StockBallDB V2 planning and implementation.  
**Companion docs:** [index](StockBallDB_index.md) · [V2 scope](StockBallDB_V2_scope.md) · [V2 progress](StockBallDB_V2_progress.md) · [future / deferred](StockBallDB_future.md)

Record:

* what was decided;
* why;
* alternatives considered where relevant;
* consequences;
* whether the decision is **Proposed** or **Locked**.

Do not add architecture or technology decisions until they are actually made.

---

## Decision entry template

```markdown
### Decision: <short title>

| Field | Value |
| ----- | ----- |
| Status | Proposed \| Locked |
| Date | YYYY-MM-DD |
| Owner doc | link if applicable |

**Decision:** One-paragraph statement of what was decided.

**Why:** Short rationale.

**Alternatives considered:** Optional. List only when useful.

**Consequences:** What this commits the project to, and what it excludes.
```

---

## Locked decisions

### Decision: V2 is an evolution of V1

| Field | Value |
| ----- | ----- |
| Status | Locked |
| Date | 2026-09-17 |
| Owner doc | [StockBallDB_V2_scope.md](StockBallDB_V2_scope.md) |

**Decision:** StockBallDB V2 extends the certified V1 foundation. It does not rebuild StockBallDB from scratch.

**Why:** V1 is complete and certified. The database foundation, pipelines, validation, health checks, fingerprints, snapshots, exact rebuild, update orchestration, provenance, schema, and tests are already trustworthy. Rewriting them would discard proven work without necessity.

**Alternatives considered:**

* Full rewrite of storage / pipelines / schema — rejected for V2.
* Treat V2 as an unrelated greenfield application — rejected; V2 builds on V1.

**Consequences:** Preserve existing PostgreSQL, schema, Python acquisition/normalization/derivation, SQLAlchemy, Alembic, validation, health, fingerprints, provenance, snapshots, exact rebuild, update orchestration, and tests where practical. The primary V2 work is the application/UI layer and clean interfaces to existing capabilities. Material foundation changes require an explicit later decision.

---

### Decision: V2 scope boundary

| Field | Value |
| ----- | ----- |
| Status | Locked |
| Date | 2026-09-17 |
| Owner doc | [StockBallDB_V2_scope.md](StockBallDB_V2_scope.md) |

**Decision:** V2 is limited to helping the user view, filter, explore, inspect, understand, validate, maintain, update, and reproduce what StockBallDB already contains. Research, experiment, prediction, backtesting, strategy, portfolio, and trading functionality are outside V2.

**Why:** StockBallDB’s responsibility is a trustworthy historical foundation. Mixing inspection/management with predictive discovery would blur the certified V1 boundary and invite experiment logic into the database product.

**Alternatives considered:**

* Include lightweight “what happens next” analytics in V2 — rejected; that is research/experiment work.
* Keep V2 strictly read-only forever — rejected as a permanent rule; V2 may surface existing update/snapshot/rebuild maintenance paths, subject to safe UX later.

**Consequences:** Filtering and inspecting canonical fields (including retrospective `market_outcomes` labels) is allowed. Turning those fields into outcome studies, signal tools, or strategy engines is not. Deferred ideas belong in [StockBallDB_future.md](StockBallDB_future.md).

---

### Decision: Documentation model

| Field | Value |
| ----- | ----- |
| Status | Locked |
| Date | 2026-09-17 |
| Owner doc | [StockBallDB_index.md](StockBallDB_index.md) |

**Decision:** StockBallDB uses a **Canonical + historical + V2 working** documentation model.

| Layer | Role |
| ----- | ---- |
| Canonical documents | Describe the current StockBallDB system as it exists. Change only when the system they describe changes. |
| Historical / version documents | Preserve certified baselines (e.g. [StockBallDB_V1_status.md](StockBallDB_V1_status.md)). Do not rewrite history. A future `StockBallDB_V2_status.md` is created only when V2 reaches certification. |
| V2 working / governance documents | Capture scope, decisions, progress, and deferred ideas during V2 development. |

**Why:** Rewriting canonical docs into “V2 docs” would mix current-system truth with planning intent. Separating certified history from working V2 material keeps authorities clear for developers and AI sessions.

**Alternatives considered:**

* Replace canonical docs with V2-branded equivalents now — rejected.
* Keep all V2 planning only in chat / informal notes — rejected; durable working docs are required.

**Consequences:** V2 planning lives in `StockBallDB_V2_scope.md`, this decision log, `StockBallDB_V2_progress.md`, and `StockBallDB_future.md`. Canonical docs remain authoritative for V1/current-system facts until the implemented system changes.
