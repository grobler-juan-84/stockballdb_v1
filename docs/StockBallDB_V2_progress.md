# StockBallDB — V2 Progress

**Purpose:** Living, concise status record for StockBallDB V2.  
**Companion docs:** [index](StockBallDB_index.md) · [V2 scope](StockBallDB_V2_scope.md) · [V2 decisions](StockBallDB_V2_decisions.md) · [V2 architecture](StockBallDB_V2_architecture.md) · [future / deferred](StockBallDB_future.md) · [V1 status](StockBallDB_V1_status.md)

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
| Overall | V2 planning — foundation + backend/application architecture locked |
| Scope | **Locked** — [StockBallDB_V2_scope.md](StockBallDB_V2_scope.md) |
| Documentation model | **Chosen** — Canonical + historical + V2 working |
| Foundation / portability / universe architecture | **Locked** |
| Backend / application architecture | **Locked** — [StockBallDB_V2_architecture.md](StockBallDB_V2_architecture.md) |
| UI / packaging | **Not locked** |
| Implementation | **Not started** (`stockballdb.app` not created yet) |
| V2 certification | Not applicable yet |

**Immediate next major planning task:** Choose V2 **UI / packaging** architecture (Streamlit vs other; desktop packaging), or begin implementing the locked application façade if UI choice is deferred deliberately.

---

## Roadmap

| # | Milestone | Status |
| - | --------- | ------ |
| 1 | Lock V2 scope and establish V2 documentation | **Complete** |
| 2 | Choose V2 application architecture | **Partial** — foundation + backend/app façade locked; UI/packaging still open |
| 3 | Design backend / application layer | **Complete** (design/docs only) |
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
* Established V2 working documentation and index routing.
* Locked foundation architecture decisions (PostgreSQL, local-first, portability, PIT, portable universe, GitHub SoT, etc.).
* Inspected V1 codebase (architecture map used as evidence; report in chat, not a committed artifact).
* Designed and documented V2 backend/application architecture: thin in-process façade, Layer A/B/C, read vs maintenance safety, universe service boundary, maintenance adapters, package sketch.

---

## In progress

* None (architecture design documentation complete for this step).

---

## Next

1. Choose V2 UI / packaging approach (still open), **or** start implementing `stockballdb.app` read façade against existing explorer query stack.
2. Before universe sync implementation: choose universe file format after deeper format design (transport/auth still open).
3. Do not implement Fresh Build / Backup / GitHub sync until those designs are ready.

---

## Decided (pointers)

Full entries: [StockBallDB_V2_decisions.md](StockBallDB_V2_decisions.md); detail: [StockBallDB_V2_architecture.md](StockBallDB_V2_architecture.md).

Foundation locks plus:

* Thin in-process application façade — Locked
* Layer A / B / C responsibility model — Locked
* Read vs maintenance safety boundary — Locked
* Reuse Explorer query stack as V2 read foundation — Locked
* Maintenance via adapters over existing orchestrators — Locked
* Narrow universe service in the application layer — Locked
* Façade service module boundaries — Locked

---

## Notes

* V1 remains the certified baseline: [StockBallDB_V1_status.md](StockBallDB_V1_status.md).
* Deferred research ideas: [StockBallDB_future.md](StockBallDB_future.md).
* Existing V1 Explorer remains documented in [StockBallDB_explorer.md](StockBallDB_explorer.md); V2 application packages are not created yet.
* Fresh Build, backup/restore, and GitHub universe sync remain **planned**, not implemented.
