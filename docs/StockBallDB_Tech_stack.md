# StockBallDB — Tech Stack

**Version:** 0.02
**Status:** Initial Tech Stack
**Last Updated:** 2026-08-24

> Companion docs: [index](StockBallDB_index.md) · [manifesto](StockBallDB_manifesto.md) · [universe](StockBallDB_universe.md) · [schema](StockBallDB_schema.md) · [sources](StockBallDB_sources.md) · [definitions](StockBallDB_definitions.md)

## Purpose

This document defines the **technical stack used to build, populate, validate, maintain, update, and reproduce StockBallDB**.

StockBallDB should use the simplest technology that satisfies its core requirements:

**Correctness → Reproducibility → Coverage → Data quality → Maintainability → Performance**

The technology stack serves the database. It should not introduce unnecessary infrastructure or make StockBallDB dependent on a particular computer, editor, provider, or hosting platform.

---

# 1. Stack Overview

| Layer               | Technology                                | Responsibility                                                    | Status  |
| ------------------- | ----------------------------------------- | ----------------------------------------------------------------- | ------- |
| Database            | **PostgreSQL**                            | Canonical relational database                                     | Locked  |
| Language            | **Python**                                | Acquisition, normalization, derivation, validation, orchestration | Locked  |
| Data processing     | **pandas**                                | Tabular transformation and deterministic calculations             | Locked  |
| Database access     | **SQLAlchemy**                            | Python ↔ PostgreSQL interface                                     | Locked  |
| Migrations          | **Alembic**                               | Version-controlled database schema evolution                      | Locked  |
| SQL                 | **PostgreSQL SQL**                        | Constraints, queries, validation, database operations             | Locked  |
| HTTP                | **requests**                              | REST API acquisition                                              | Locked  |
| Configuration       | **python-dotenv / environment variables** | Local configuration and API credentials                           | Locked  |
| Testing             | **pytest**                                | Automated pipeline and calculation testing                        | Locked  |
| Version control     | **Git**                                   | Repository history and reproducibility                            | Locked  |
| Repository          | **GitHub**                                | Remote project repository                                         | Locked  |
| Development         | **Cursor**                                | Primary development environment                                   | Current |
| Database inspection | **DBeaver**                               | Manual database inspection / debugging                            | Current |
| Hosting             | **Local PostgreSQL**                      | Initial sandbox database                                          | Current |
| Future hosting      | **Supabase / hosted PostgreSQL**          | Potential shared database environment                             | Future  |

---

# 2. PostgreSQL

**Role:** Canonical StockBallDB database architecture
**Status:** Locked

StockBallDB is a PostgreSQL database.

Local PostgreSQL is the current development environment, but **PostgreSQL itself is the architectural decision**.

PostgreSQL owns:

* tables;
* primary and foreign keys;
* constraints;
* indexes;
* relational integrity;
* stored historical records;
* database-level validation;
* queryable canonical data.

The database must remain portable between compatible PostgreSQL environments.

```text
Current

Python
   ↓
Local PostgreSQL


Possible Future

Python
   ↓
Hosted PostgreSQL / Supabase
```

Moving the database should not require redesigning StockBallDB.

---

# 3. Python

**Role:** Primary pipeline and orchestration language
**Status:** Locked

Python owns the operational data pipeline.

Primary responsibilities:

```text
Fetch
Normalize
Align
Derive
Validate
Load
Update
Rebuild
```

The pipeline should maintain clear separation between:

```text
External Provider
       ↓
Fetch
       ↓
Raw Provider Representation
       ↓
Normalize
       ↓
Canonical Representation
       ↓
Derive
       ↓
Validate
       ↓
PostgreSQL
```

Provider-specific assumptions should stop at the acquisition and normalization layers.

StockBallDB calculations must not depend unnecessarily on the provider from which the underlying observation originated.

---

# 4. pandas

**Role:** Tabular data transformation and deterministic calculations
**Status:** Locked

pandas is the primary Python tool for manipulating data during StockBallDB builds and updates.

Appropriate responsibilities include:

* cleaning API responses;
* normalizing fields;
* date alignment;
* rolling calculations;
* returns;
* moving averages;
* drawdowns;
* volatility calculations;
* forward outcomes;
* missing-data handling;
* validation comparisons.

pandas is a **processing tool**, not the database.

Canonical persistent data belongs in PostgreSQL.

---

# 5. SQLAlchemy

**Role:** Python ↔ PostgreSQL interface
**Status:** Locked

SQLAlchemy provides the primary database interface used by Python pipelines.

It should handle:

* database connections;
* transactions;
* inserts;
* updates;
* queries required by pipelines;
* interaction with migration tooling.

SQLAlchemy must not obscure the underlying PostgreSQL design.

StockBallDB remains a PostgreSQL project rather than an ORM-defined database.

Direct SQL remains appropriate where it is clearer or better suited to the operation.

---

# 6. Alembic

**Role:** Database schema migrations
**Status:** Locked

Alembic provides version-controlled evolution of the PostgreSQL schema.

Schema changes should follow:

```text
Design change
     ↓
Alembic migration
     ↓
Commit to Git
     ↓
Apply migration
     ↓
Equivalent schema reproducible elsewhere
```

Manual database changes must not become undocumented dependencies.

A new installation should be capable of reconstructing the correct schema by applying the repository's migrations.

The migrations are the authoritative executable history of the database structure.

---

# 7. HTTP Acquisition

## requests

**Role:** REST API communication
**Status:** Locked

Python's `requests` library is the default HTTP client for data providers exposing REST APIs.

Current API-based sources include:

* Tiingo;
* FRED;
* ALFRED;
* potentially EIA;
* future structured providers.

Provider-specific API logic should remain isolated from StockBallDB's canonical schema.

---

# 8. Historical Integrity

StockBallDB contains datasets with fundamentally different historical behavior.

The technology stack must support the distinction between:

### Fixed or effectively fixed observations

Examples may include:

```text
trading dates
historical OHLCV observations
scheduled historical events
```

### Correctable or revisable observations

Examples include many:

```text
employment statistics
inflation releases
GDP
other macroeconomic releases
```

Where historical research requires knowing **what information was available on a particular date**, the pipeline must support point-in-time or vintage acquisition rather than silently substituting today's revised historical values.

ALFRED is therefore not merely another provider integration; it supports a fundamental historical-integrity requirement.

The database and pipelines should preserve enough provenance and timing information to distinguish:

```text
observation period
release date
value available at the time
later revised value
```

where the dataset requires it.

---

# 9. Configuration and Secrets

Environment-specific configuration must remain outside source code.

API credentials should be supplied through environment variables.

Example:

```text
TIINGO_API_KEY=
FRED_API_KEY=
EIA_API_KEY=
DATABASE_URL=
```

Local development may use:

```text
.env
```

The repository should contain:

```text
.env.example
```

with empty placeholders.

`.env` must be excluded through `.gitignore`.

Credentials must never be:

* committed to Git;
* embedded in Python files;
* embedded in migrations;
* stored in documentation;
* required through undocumented manual configuration.

---

# 10. pytest

**Role:** Automated testing and reproducibility verification
**Status:** Locked

pytest provides automated tests for StockBallDB's deterministic behavior.

Tests should progressively cover:

### Derived calculations

```text
returns
moving averages
drawdowns
volatility
forward outcomes
calendar calculations
regime classifications
```

### Pipeline behavior

```text
normalization
date alignment
missing values
duplicate handling
provider-response handling
update behavior
```

### Historical integrity

Where appropriate:

```text
release-date handling
vintage selection
point-in-time reconstruction
look-ahead prevention
```

### Database behavior

```text
constraints
expected row uniqueness
foreign-key integrity
migration behavior
```

A pipeline completing without an exception does not by itself mean that the resulting data is correct.

---

# 11. Validation Architecture

Validation should exist at several layers.

## Database validation

PostgreSQL handles structural guarantees:

```text
PRIMARY KEY
FOREIGN KEY
UNIQUE
NOT NULL
CHECK
data types
```

## Pipeline validation

Python validates properties such as:

```text
duplicates
sorting
date coverage
missing observations
OHLC consistency
unexpected provider changes
historical continuity
derived calculations
```

## Cross-source validation

Where justified, important datasets may be compared against independent or authoritative sources.

Cross-source checks are primarily for **verification**, not for silently combining conflicting values.

Disagreements should be investigated rather than automatically averaged or overwritten.

---

# 12. Data Provenance

Observed data should remain traceable to its origin.

Where required, StockBallDB should be able to establish:

```text
provider
provider series / ticker
retrieval method
observation date
release / availability date
vintage where applicable
normalization applied
```

Derived fields should be traceable through:

```text
underlying observations
+
StockBallDB definition
+
project version
=
derived value
```

This supports the fundamental requirement:

> **Where did this value come from?**

---

# 13. Git

**Role:** Version control and reproducibility
**Status:** Locked

Git stores the recipe used to produce StockBallDB.

Version-controlled assets include:

```text
Python pipelines
Alembic migrations
SQL
tests
configuration templates
source mappings
field definitions
validation logic
documentation
dependency definitions
```

The database is not the primary source of truth for how StockBallDB is constructed.

**The repository is the recipe. The database is the result.**

---

# 14. GitHub

**Role:** Remote project repository
**Status:** Locked

GitHub provides the remote repository from which StockBallDB should eventually be reproducible.

The target is:

```text
Clone
  ↓
Configure
  ↓
Install
  ↓
Create database
  ↓
Migrate
  ↓
Fetch
  ↓
Normalize
  ↓
Derive
  ↓
Validate
  ↓
Store
  ↓
Ready
```

A database should not depend on undocumented knowledge from the computer on which it was originally created.

---

# 15. DBeaver

**Role:** Database inspection and debugging
**Status:** Current tooling

DBeaver may be used to inspect PostgreSQL during development.

Typical uses include:

* viewing tables;
* checking row counts;
* inspecting data;
* executing exploratory SQL;
* debugging pipeline output;
* verifying migrations.

DBeaver is not part of StockBallDB's architecture.

Nothing required to reproduce the database should depend on actions performed manually through DBeaver.

---

# 16. Cursor

**Role:** Primary development environment
**Status:** Current tooling

Cursor is currently used to develop the project and assist with implementation.

It may be used to create and modify:

* Python;
* SQL;
* Alembic migrations;
* tests;
* configuration;
* documentation.

Cursor is not a runtime dependency.

StockBallDB must remain reproducible without Cursor.

---

# 17. Local Sandbox

The first StockBallDB environment intentionally runs locally.

```text
External Sources
       ↓
Python Pipeline
       ↓
Local PostgreSQL
       ↓
Validation
       ↓
StockBallDB
```

The sandbox exists to determine:

* what data can actually be obtained;
* what historical coverage exists;
* where provider weaknesses occur;
* which definitions work;
* which fields need changing;
* which validation rules are necessary;
* how the final build process should operate.

Schema and pipeline changes during this stage are expected.

They must nevertheless remain documented and reproducible.

---

# 18. Future Hosting

## Supabase / Hosted PostgreSQL

**Status:** Future

StockBallDB does not currently require hosted infrastructure.

Once the database and build pipeline are mature, a hosted PostgreSQL environment may become useful for:

* access from multiple computers;
* remote research;
* future MoneyBallApp access;
* backups;
* centralized storage.

Supabase is a strong candidate because it preserves the PostgreSQL architecture.

However:

> **StockBallDB must not become Supabase-dependent merely because Supabase may host it.**

The local PostgreSQL database should remain reproducible independently.

---

# 19. Dependency Management

Python dependencies must be explicitly recorded and reproducible.

The project should maintain a version-controlled dependency definition.

The exact packaging convention may remain lightweight during the sandbox stage, but another machine must eventually be able to install an equivalent Python environment without guessing which packages are required.

Avoid adding dependencies when Python, PostgreSQL, pandas, or existing project libraries already solve the problem adequately.

---

# 20. Logging

Pipeline execution should produce structured, readable logs.

At minimum, important operations should report:

```text
pipeline started
source being fetched
date range
records received
records normalized
records inserted / updated
validation result
warnings
errors
pipeline completed
```

Logging becomes particularly important for automated updates and full rebuilds.

The logs should make failures diagnosable without requiring inspection of the pipeline source code.

Exact logging implementation may remain simple initially using Python's standard `logging` module.

---

# 21. Idempotent Pipelines

Build and update pipelines should be designed to be safely repeatable where practical.

Running an ingestion step twice should not accidentally create duplicate canonical observations.

Appropriate techniques may include:

```text
primary keys
unique constraints
upserts
transactions
deterministic derivation
explicit date ranges
```

This is particularly important for future automated updates.

---

# 22. Portability

StockBallDB should avoid unnecessary dependence on:

* one computer;
* one operating system;
* Cursor;
* DBeaver;
* Supabase;
* one provider;
* manually created database state;
* undocumented local files.

The target remains:

```text
Different computer
      +
Same repository version
      +
Same definitions
      +
Same source data / vintages
      +
Same cutoff
      ↓
Equivalent StockBallDB
```

---

# 23. What StockBallDB Does Not Need Yet

StockBallDB should not add infrastructure without a demonstrated requirement.

Version 1 does **not** currently require:

```text
Docker
Kubernetes
Airflow
Kafka
Spark
Redis
microservices
real-time streaming
cloud data warehouses
distributed processing
complex orchestration platforms
```

These technologies are not rejected permanently.

They are simply unnecessary for the current size and purpose of StockBallDB.

A technology should be introduced when an actual limitation justifies it.

---

# Current Decisions

## Locked

* **PostgreSQL** — canonical database architecture.
* **Local PostgreSQL** — initial sandbox.
* **Python** — pipeline and orchestration language.
* **pandas** — primary tabular processing library.
* **SQLAlchemy** — Python/PostgreSQL interface.
* **Alembic** — schema migrations.
* **requests** — REST API acquisition.
* **pytest** — automated testing.
* **Git** — version control.
* **GitHub** — remote repository.
* **Environment variables / `.env`** — configuration and credentials.
* **StockBallDB-owned derivation** — deterministic derived fields calculated internally.

## Current Tooling

* **Cursor** — development environment.
* **DBeaver** — database inspection.

## Future / Provisional

* **Supabase / hosted PostgreSQL** — future remote database environment.
* Exact Python version.
* Exact dependency-locking convention.
* CI automation such as GitHub Actions.
* Automated scheduled updates.
* Backup strategy.
* Pipeline execution interface.

## Explicitly Not Required Yet

* Docker
* Airflow
* Kubernetes
* Kafka
* Spark
* Redis
* microservices
* real-time infrastructure

---

# Guiding Rule

> **Use the simplest stack capable of producing a StockBallDB we can trust and reproduce.**

Technology may change.

Providers may change.

Hosting may change.

The reproducibility contract should not.
