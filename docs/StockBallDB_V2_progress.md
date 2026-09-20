# StockBallDB — V2 Progress

**Purpose:** Living, concise status record for StockBallDB V2.  
**Companion docs:** [index](StockBallDB_index.md) · [V2 scope](StockBallDB_V2_scope.md) · [V2 decisions](StockBallDB_V2_decisions.md) · [V2 architecture](StockBallDB_V2_architecture.md) · [V2 roadmap](StockBallDB_V2_roadmap.md) · [future / deferred](StockBallDB_future.md) · [V1 status](StockBallDB_V1_status.md)

---

## Current status

| Item | State |
| ---- | ----- |
| Overall | V2 implementation started |
| Architecture / roadmap | **Locked** |
| **P1 `stockballdb.app` Catalog + Status** | **Complete** |
| Next phase | **P2 — FastAPI localhost read transport** |
| FastAPI / React / Electron | Not started |

---

## P1 summary

* Added `src/stockballdb/app/` with Catalog (`list_instruments`, `list_data_domains`, `get_fields`) and Status (`get_status`, `run_validate_v1`, `get_fingerprint`).
* Wraps V1 universe, Explorer registry/definitions, health, validate_v1, fingerprint; transport-agnostic dataclasses; read engine via Explorer helpers.
* Tests: `tests/test_app_catalog_status.py`; full suite **230 passed, 3 skipped**.

---

## Next

1. **Start Phase 2** — FastAPI on `127.0.0.1` wrapping Catalog + Status + readiness/errors.
2. Do not begin React until P2 gate is met.

---

## Notes

* V1 Streamlit Explorer unchanged.
* No schema/data changes in P1.
* Portable universe, Explore queries, Day, Maintenance deferred per roadmap.
