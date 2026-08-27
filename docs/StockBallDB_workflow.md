# StockBallDB — Workflow

## 1. Purpose

This document defines the high-level workflow used to build, populate, validate, update, and maintain StockBallDB.

It describes **how data moves through the system**.

It does not define:

* the philosophical purpose of StockBallDB — see `StockBallDB_manifesto.md`;
* the canonical database structure — see `StockBallDB_schema.md`;
* provider-specific source details — see `StockBallDB_sources.md`;
* canonical definitions — see `StockBallDB_definitions.md`;
* the asset universe — see `StockBallDB_universe.md`;
* technical implementation choices — see `StockBallDB_Tech_stack.md`.

The workflow should remain simple, explicit, reproducible, and auditable.

---

# 2. Core Workflow

The fundamental StockBallDB data flow is:

```text
Sources
   ↓
Acquisition
   ↓
Raw / Preserved Source Data
   ↓
Normalization
   ↓
Canonical Historical Data
   ↓
Derivation
   ↓
Validation
   ↓
PostgreSQL
```

Each stage has a distinct responsibility.

Data should not silently bypass stages when doing so would weaken reproducibility, provenance, or validation.

---

# 3. Source Selection

Before data is acquired, StockBallDB must know:

* what data is required;
* which source provides it;
* what the source represents;
* what historical coverage is available;
* what limitations are known.

Provider selection belongs to the source layer.

The canonical database should not unnecessarily depend on the format or structure of any individual provider.

Where practical:

```text
Provider-specific data
        ↓
Normalization
        ↓
StockBallDB canonical representation
```

This allows providers to be replaced or supplemented without redesigning the canonical database.

---

# 4. Acquisition

The acquisition layer retrieves data from external sources.

Examples may eventually include:

* Tiingo;
* FRED / ALFRED;
* EIA;
* other approved historical sources.

Acquisition should be responsible for retrieving source data, not interpreting research meaning.

Where practical, acquisition should record enough information to determine:

* source;
* retrieval time;
* requested range;
* response status;
* coverage received;
* whether the acquisition completed successfully.

Acquisition failure must be visible.

The system must not silently treat failed acquisition as valid missing data.

---

# 5. Raw / Preserved Source Data

Where appropriate, StockBallDB should preserve the original source information before transforming it into canonical data.

The purpose is not to create a permanent duplicate of every provider response regardless of value.

The purpose is to preserve enough evidence to:

* reproduce transformations;
* investigate unexpected values;
* compare providers;
* audit historical corrections;
* understand where canonical values originated.

Raw preservation strategy may differ between sources depending on the nature, size, and reproducibility of the source.

---

# 6. Normalization

External data must be converted from provider-specific representations into StockBallDB's canonical definitions.

Normalization may include:

* date normalization;
* asset identifier mapping;
* column mapping;
* numeric type conversion;
* missing-value handling;
* unit normalization;
* provider-specific interpretation;
* duplicate handling.

Normalization must not silently change the meaning of the source data.

Provider-specific assumptions should remain isolated from the canonical database wherever practical.

---

# 7. Canonical Historical Data

After normalization, data may enter the canonical StockBallDB historical layer.

The canonical tables represent StockBallDB's trusted historical record.

The initial canonical model is defined separately in:

`StockBallDB_schema.md`

Canonical data should be:

* deterministic;
* consistently defined;
* traceable to its source;
* validated;
* reproducible;
* suitable for future research without knowledge of the original provider format.

The canonical layer must remain independent of future:

* experiments;
* predictions;
* strategies;
* portfolio decisions;
* trading decisions.

StockBallDB stores historical facts and deterministic historical context.

It does not decide what those facts mean for a trade.

---

# 8. Derivation

Some StockBallDB fields cannot be directly acquired and must be deterministically calculated from historical data.

Examples may include:

* returns;
* rolling values;
* drawdowns;
* volatility measures;
* calendar context;
* historical market regimes;
* derived market outcomes.

Derived data must follow definitions established in:

`StockBallDB_definitions.md`

A derived value should be reproducible from:

```text
Canonical Inputs
      +
Locked Definition
      ↓
Derived Value
```

Derivation logic should not depend on the result of a research experiment.

If an experiment discovers a useful condition, that does not automatically make the condition part of StockBallDB.

---

# 9. Validation

Validation is a first-class part of StockBallDB.

Data should not be considered trustworthy merely because an API request succeeded or a database insert completed.

Validation may operate at several levels.

### Structural validation

Examples:

* required columns exist;
* expected types are valid;
* primary keys are unique;
* required relationships are valid.

### Coverage validation

Examples:

* expected dates exist;
* expected assets exist;
* historical ranges are complete;
* unexpected gaps are identified.

### Value validation

Examples:

* impossible values are rejected or flagged;
* duplicate observations are detected;
* derived calculations satisfy known invariants.

### Cross-source validation

Where appropriate, important values may be compared against independent sources.

Validation failures must be visible.

StockBallDB should prefer:

```text
STOP / FLAG / INVESTIGATE
```

over silently accepting questionable historical data.

---

# 10. Database Write

Validated canonical and derived data may be written to PostgreSQL.

Database writes should be:

* deterministic;
* repeatable;
* safe against accidental duplication;
* explicit about failures.

Where practical, pipelines should be idempotent.

Running the same pipeline twice with the same source data and definitions should not corrupt or duplicate the canonical historical record.

---

# 11. Provenance

StockBallDB should be able to answer:

> Where did this value come from?

Depending on the data type, provenance may include:

```text
Canonical Value
      ↓
Transformation / Definition
      ↓
Source Observation
      ↓
Provider
      ↓
Retrieval
```

Not every value requires identical provenance machinery.

However, important canonical historical values should not become disconnected from their origin.

---

# 12. Initial Build Workflow

A newly cloned StockBallDB repository should eventually be able to reproduce the database through an explicit sequence.

Conceptually:

```text
Clone repository
      ↓
Create environment
      ↓
Configure credentials
      ↓
Create PostgreSQL database
      ↓
Apply migrations
      ↓
Acquire required source data
      ↓
Normalize
      ↓
Build canonical historical data
      ↓
Calculate deterministic derived data
      ↓
Validate
      ↓
Report coverage and validation status
```

The exact implementation will evolve as each phase is built.

Reproduction should not require undocumented manual database manipulation.

---

# 13. Update Workflow

StockBallDB must support the fact that financial history continues to grow.

After the initial historical build, the normal update process should conceptually be:

```text
Determine latest trusted coverage
      ↓
Determine required new period
      ↓
Acquire new source data
      ↓
Preserve source information
      ↓
Normalize
      ↓
Derive
      ↓
Validate
      ↓
Insert / update PostgreSQL
      ↓
Update coverage information
```

Updates should normally process only the required range rather than rebuilding the entire historical database unnecessarily.

However, the architecture should still allow a complete rebuild when required.

---

# 14. Historical Corrections

External providers may revise historical data.

Therefore StockBallDB must distinguish between:

```text
New Data
```

and:

```text
Changed Historical Data
```

The update process should eventually provide a mechanism to detect meaningful historical changes where practical.

Historical corrections must not silently alter trusted data without traceability.

The exact correction strategy may vary by source and will be implemented when the relevant acquisition pipelines are built.

---

# 15. Coverage

StockBallDB should know what data it actually possesses.

Coverage should eventually be inspectable by dimensions such as:

* asset;
* dataset;
* start date;
* end date;
* expected observations;
* actual observations;
* missing observations;
* validation state.

The absence of data should be distinguishable from:

* provider failure;
* pipeline failure;
* genuine historical non-existence;
* intentionally unsupported coverage.

---

# 16. Failure Philosophy

StockBallDB should fail loudly when trust cannot be established.

Prefer:

```text
Incomplete data detected
Pipeline stopped
Reason recorded
```

over:

```text
Pipeline completed
Unknown data silently missing
```

Failures should provide enough information to identify:

* which stage failed;
* which dataset or asset was affected;
* what condition caused the failure;
* what action is required.

A partially successful pipeline must not be reported as completely successful.

---

# 17. Logging

Major workflow stages should produce concise operational logs.

Examples:

```text
StockBallDB starting
Acquisition started
Records received
Normalization completed
Derivation completed
Validation passed
Database write completed
Coverage updated
Pipeline completed
```

Warnings and failures should be clearly distinguishable from normal informational messages.

Logging exists to make the pipeline understandable, not to produce unnecessary noise.

---

# 18. Reproducibility

A core requirement of StockBallDB is that another environment should eventually be able to reproduce the database from:

```text
Repository
+
Configuration
+
Approved external sources
```

Reproduction should not depend on:

* undocumented manual steps;
* one specific computer;
* Cursor;
* DBeaver;
* an existing personal database;
* hidden local files other than credentials/configuration.

The repository should contain the executable knowledge required to rebuild StockBallDB.

---

# 19. Migration Workflow

Database structure changes must be handled through Alembic migrations.

Conceptually:

```text
Schema Definition Changes
        ↓
Alembic Migration
        ↓
Review
        ↓
Apply Migration
        ↓
Updated Database
```

Manual structural changes made through DBeaver or another database client should not become the authoritative schema history.

The migration history is the executable record of how the StockBallDB schema evolved.

---

# 20. Development Phases

StockBallDB should be built incrementally.

Each phase should:

1. have a clearly defined scope;
2. implement only the required functionality;
3. verify that functionality;
4. update documentation where necessary;
5. stop before beginning the next phase.

A reasonable high-level progression is:

```text
Phase 0
Project Foundation

Phase 1
trading_days — schema, generate, validate (NYSE spine from 1957)

Phase 2A
daily_market_data — 14 Tiingo ETFs (observed OHLCV + corp actions)

Phase 2B
daily_market_data derived fields (locked bases; populate return_1d / gap_pct / …)

Phase 2C
market_outcomes — retrospective forward labels from daily_market_data

Phase 2D
asset_regimes — point-in-time asset state from daily_market_data

Phase 2E
macro_conditions — FRED/ALFRED macro context (pmi deferred)

Phase 2F
scheduled_events — occurrence calendar (fomc, cpi, employment_situation, election)

Phase 2G
calendar_context — holiday/session/week/transitions + retrospective event context

Phase 3+
Further Source Acquisition + Canonical Dataset Pipelines

Later
Derived Data + Validation + Coverage

Later
Update / Rebuild Orchestration

Later
StockBallDB Inspector
```

Exact later-phase boundaries may change as implementation teaches us more.

Do not prematurely lock detailed implementation plans for phases that have not yet been designed.

---

# 21. StockBallDB Inspector

A future StockBallDB interface may provide operational visibility into the database.

Possible views include:

* Control Center;
* Data Explorer;
* Day Inspector;
* Coverage Explorer;
* Provenance Explorer;
* Validation Center.

The Inspector is an interface **to StockBallDB**, not a research or trading application.

It may answer questions such as:

> What data exists?

> What happened on this historical date?

> Where did this value come from?

> Is this dataset complete?

> When was this data last updated?

> Did validation pass?

It should not answer:

> Should I buy?

> What will happen tomorrow?

> Which strategy should I trade?

Those belong outside StockBallDB.

---

# 22. Boundary With Future Research Systems

StockBallDB ends at trusted historical data.

The conceptual boundary is:

```text
External Sources
      ↓
StockBallDB
      ↓
Trusted Historical Dataset
=============================
      BOUNDARY
=============================
Future Research / Experiment System
      ↓
Experiments
      ↓
Models
      ↓
Predictions
      ↓
Strategies
      ↓
Decision Support / Trading
```

Future systems may depend heavily on StockBallDB.

StockBallDB must not depend on them.

Research discoveries must not retroactively alter the historical database simply because they improve an experimental result.

---

# 23. Guiding Rule

When deciding whether something belongs in StockBallDB, ask:

> **Is this required to acquire, preserve, normalize, derive, validate, explain, update, or inspect trustworthy historical data?**

If yes, it may belong in StockBallDB.

If its purpose is primarily to:

* test a hypothesis;
* discover an edge;
* predict future movement;
* rank opportunities;
* construct a strategy;
* generate a trade decision;

it belongs outside StockBallDB.

---

# 24. Current Principle

Build only what the current phase requires.

Keep the pipeline:

**simple → explicit → deterministic → validated → reproducible → auditable.**

StockBallDB should become boring infrastructure that future research can trust.
