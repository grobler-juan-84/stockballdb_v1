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
| Overall | V2 planning architecture largely locked; implementation not started |
| Scope | **Locked** |
| Foundation / portability / universe | **Locked** |
| Backend / application façade | **Locked** (`stockballdb.app`) |
| Forward-facing UI | **Locked — React** (Streamlit = V1) |
| Transport | **Locked — localhost FastAPI JSON over façade** |
| Desktop shell | **Locked — Electron** |
| PostgreSQL runtime | **Locked — independent local service** |
| Installer / Python bundling tools | **Not locked** |
| Implementation | **Not started** |
| V2 certification | Not applicable yet |

**Immediate next task:** Begin implementing `stockballdb.app` read façade + FastAPI transport contracts, then React client scaffolding. Electron can follow once local API works. AI Studio prototype (when in repo) is UI reference only.

---

## Roadmap

| # | Milestone | Status |
| - | --------- | ------ |
| 1 | Lock V2 scope and establish V2 documentation | **Complete** |
| 2 | Choose V2 application architecture | **Complete** (foundation + backend + React/HTTP + Electron/FastAPI runtime) |
| 3 | Design backend / application layer | **Complete** (design/docs) |
| 4 | Build read / query layer | Not started |
| 5 | Build Data Explorer V2 | Not started |
| 6 | Build Day Inspector | Not started |
| 7 | Build Database Overview | Not started |
| 8 | Connect Maintenance operations | Not started |
| 9 | Solve local PostgreSQL setup and portability | Not started |
| 10 | Desktop packaging | Architecture locked; implementation not started |
| 11 | Safety and destructive-operation UX | Not started |
| 12 | V2 testing and certification | Not started |
| 13 | Documentation cleanup / finalization | Not started |
| 14 | Declare V2 baseline | Not started |

---

## Completed

* Locked V2 scope and documentation model.
* Locked foundation architecture (PostgreSQL, local-first, portability, PIT, universe/GitHub direction, preserve V1).
* Designed `stockballdb.app` façade; locked React + localhost HTTP communication.
* Locked desktop runtime: Electron shell; FastAPI transport; Electron owns Python child; PostgreSQL independent; maintenance integrity on shutdown; app-update ≠ DB-update; runtime continues to V3.

---

## In progress

* None (desktop/runtime architecture documentation complete for this step).

---

## Next

1. Implement `stockballdb.app` read services.
2. Implement FastAPI transport over those services (`127.0.0.1`).
3. Scaffold React application client + features (AI Studio prototype as layout/interaction reference when available).
4. Add Electron shell after API+React work independently.
5. Later: universe format, backup format, Python bundling/installer tooling.

---

## Decided (pointers)

See [StockBallDB_V2_decisions.md](StockBallDB_V2_decisions.md) and [StockBallDB_V2_architecture.md](StockBallDB_V2_architecture.md) §19.

Desktop/runtime locks:

* Electron desktop shell — Locked
* FastAPI localhost HTTP framework — Locked
* Electron owns Python backend child — Locked
* PostgreSQL independent local service — Locked
* Maintenance integrity over casual quit — Locked
* Application update ≠ database update — Locked
* V2 desktop runtime continues into V3 — Locked

---

## Notes

* V1 baseline: [StockBallDB_V1_status.md](StockBallDB_V1_status.md).
* V1 Streamlit Explorer retained: [StockBallDB_explorer.md](StockBallDB_explorer.md).
* No Electron/React/FastAPI/`app` code created in this planning step.
* Browser-only local mode remains valid for development.
