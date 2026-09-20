# StockBallDB — V2 Progress

**Purpose:** Living, concise status record for StockBallDB V2.  
**Companion docs:** [index](StockBallDB_index.md) · [V2 scope](StockBallDB_V2_scope.md) · [V2 decisions](StockBallDB_V2_decisions.md) · [future / deferred](StockBallDB_future.md) · [V1 status](StockBallDB_V1_status.md)

Use this document to answer quickly:

* where V2 currently stands;
* what has been decided;
* what has been completed;
* what is in progress;
* what comes next.

This is not a diary. Prefer short milestone / status entries.

---

## Current status

| Item | State |
| ---- | ----- |
| Overall | V2 planning — foundation architecture locked |
| Scope | **Locked** — [StockBallDB_V2_scope.md](StockBallDB_V2_scope.md) |
| Documentation model | **Chosen** — Canonical + historical + V2 working |
| Foundation / portability / universe architecture | **Locked** — [StockBallDB_V2_decisions.md](StockBallDB_V2_decisions.md) |
| UI / packaging / app-layer architecture | **Not locked** |
| Implementation | **Not started** |
| V2 certification | Not applicable yet (`StockBallDB_V2_status.md` exists only after certification) |

**Immediate next major planning task:** Choose V2 **application** architecture (UI framework, packaging, and local app/service shape). Foundation decisions above are already locked and must not be reopened casually.

---

## Roadmap

| # | Milestone | Status |
| - | --------- | ------ |
| 1 | Lock V2 scope and establish V2 documentation | **Complete** |
| 2 | Choose V2 application architecture | **Partial** — foundation/portability/universe locked; UI/packaging/app-layer still open |
| 3 | Design backend / application layer | Not started |
| 4 | Build read / query layer | Not started |
| 5 | Build Data Explorer V2 | Not started |
| 6 | Build Day Inspector | Not started |
| 7 | Build Database Overview | Not started |
| 8 | Connect Maintenance operations | Not started |
| 9 | Solve local PostgreSQL setup and portability | Not started |
| 10 | Desktop packaging | Not started |
| 11 | Safety and destructive-operation UX | Not started |
| 12 | V2 testing and certification | Not started |
| 13 | Documentation cleanup / finalization | Not started |
| 14 | Declare V2 baseline | Not started |

---

## Completed

* Locked V2 scope boundary (inspection / management vs research / experiment).
* Established V2 working documentation: scope, decisions, progress, and deferred-future parking document.
* Updated the documentation index to route Canonical / historical / V2 working authorities.
* Locked foundation architecture decisions: PostgreSQL retained; local-first; portability via Fresh Build / Update / Backup-Restore / Exact Rebuild; PIT preserved; portable version-controlled universe; GitHub as universe SoT; universe-sync vs DB-update separation; preserve V1.

---

## In progress

* None (planning documentation update only).

---

## Next

1. Choose V2 application architecture (UI / packaging / local app shape) and record locked decisions in [StockBallDB_V2_decisions.md](StockBallDB_V2_decisions.md).
2. Before implementing universe sync: inspect existing V1 universe implementation (format and how symbols enter pipelines) — format/API/auth remain undecided.
3. Only after application architecture is locked: design backend / application layer.

Do not mark UI architecture or implementation work complete until it is actually done.

---

## Decided (pointers)

Full entries live in [StockBallDB_V2_decisions.md](StockBallDB_V2_decisions.md):

* V2 is an evolution of V1 — Locked
* V2 scope boundary — Locked
* Documentation model — Locked
* PostgreSQL remains the canonical database — Locked
* V2 is local-first — Locked
* Portability means reconstructability and transferability — Locked
* Preserve StockBallDB point-in-time principles — Locked
* Universe definition is portable and version-controlled — Locked
* GitHub is the planned shared source of truth for the universe — Locked
* Universe synchronization and database updating are conceptually separate — Locked
* Preserve V1 rather than rewrite it — Locked

---

## Notes

* V1 remains the certified baseline: [StockBallDB_V1_status.md](StockBallDB_V1_status.md).
* Deferred research / experiment ideas: [StockBallDB_future.md](StockBallDB_future.md).
* Existing V1 Explorer remains documented in [StockBallDB_explorer.md](StockBallDB_explorer.md); V2 application work has not replaced it.
* Fresh Build, backup/restore, and GitHub universe sync are **planned properties**, not implemented features.
