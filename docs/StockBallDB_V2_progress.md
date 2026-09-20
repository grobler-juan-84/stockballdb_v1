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
| Overall | V2 planning — foundation, backend façade, and React/communication architecture locked |
| Scope | **Locked** |
| Foundation / portability / universe | **Locked** |
| Backend / application façade | **Locked** |
| Forward-facing UI | **Locked — React** (Streamlit retained as V1) |
| React ↔ Python transport | **Locked — localhost-only HTTP JSON over `stockballdb.app`** |
| Desktop packaging (Electron/Tauri/etc.) | **Not locked** |
| Implementation | **Not started** (no `app`, transport, or React tree yet) |
| V2 certification | Not applicable yet |

**Immediate next major planning or implementation task:** Begin implementing `stockballdb.app` (read façade first) and/or thin localhost transport contracts — or choose desktop packaging when needed. Do not implement React UI before basic façade/transport contracts exist unless scaffolding only.

---

## Roadmap

| # | Milestone | Status |
| - | --------- | ------ |
| 1 | Lock V2 scope and establish V2 documentation | **Complete** |
| 2 | Choose V2 application architecture | **Complete** for foundation + backend + React/communication; packaging still open |
| 3 | Design backend / application layer | **Complete** (design/docs) |
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

* Locked V2 scope and working documentation model.
* Locked foundation architecture (PostgreSQL, local-first, portability, PIT, universe/GitHub direction, preserve V1).
* Inspected V1 architecture; designed backend façade (`stockballdb.app`).
* Locked React as V2/V3 forward-facing UI; Streamlit remains V1 Explorer.
* Locked localhost-only HTTP JSON transport over the façade; documented frontend tiers, contracts, maintenance flow, and open packaging choices.

---

## In progress

* None (communication architecture documentation complete for this step).

---

## Next

1. Implement `stockballdb.app` read services (wrap existing explorer query stack).
2. Add thin localhost transport over those services (framework choice open; FastAPI likely).
3. Scaffold React application client + Explorer feature against read contracts.
4. Desktop packaging (Electron vs Tauri) when needed — still open.
5. Universe file format / GitHub sync and Backup format remain later designs.

---

## Decided (pointers)

See [StockBallDB_V2_decisions.md](StockBallDB_V2_decisions.md) and [StockBallDB_V2_architecture.md](StockBallDB_V2_architecture.md).

Notable frontend/communication locks:

* React is the V2 forward-facing UI — Locked
* V2 React continues into V3/StockBallAPP — Locked
* React only via application/transport boundary — Locked
* Localhost-only HTTP JSON transport over façade — Locked
* React frontend tier / dependency direction — Locked

---

## Notes

* V1 certified baseline unchanged: [StockBallDB_V1_status.md](StockBallDB_V1_status.md).
* V1 Streamlit Explorer remains: [StockBallDB_explorer.md](StockBallDB_explorer.md).
* No React, FastAPI, or `stockballdb.app` code created in this planning step.
