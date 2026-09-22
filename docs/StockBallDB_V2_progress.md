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
| **P2 FastAPI localhost read transport** | **Complete** |
| Next phase | **P3 — React foundation + vertical slice** |
| React / Electron | Not started |

---

## P2 summary

* Added `src/stockballdb/api/` as a thin FastAPI adapter over P1 only (no V1/SQL internals).
* Entry point: `python -m stockballdb.api` (uvicorn, default bind `127.0.0.1:8765`).
* Endpoints: `GET /ready`, `GET /api/catalog/instruments`, `GET /api/catalog/domains`, `GET /api/catalog/domains/{domain_key}/fields`, `GET /api/status`.
* Pydantic HTTP DTOs + structured error envelope; CORS limited to local Vite/React origins; readiness does not require PostgreSQL.
* Tests: `tests/test_api_transport.py`; full suite **241 passed, 3 skipped**.
* Dependencies: `fastapi`, `uvicorn[standard]`; `httpx2` for TestClient (dev/test).

---

## P1 summary

* Added `src/stockballdb/app/` with Catalog (`list_instruments`, `list_data_domains`, `get_fields`) and Status (`get_status`, `run_validate_v1`, `get_fingerprint`).
* Wraps V1 universe, Explorer registry/definitions, health, validate_v1, fingerprint; transport-agnostic dataclasses; read engine via Explorer helpers.
* Tests: `tests/test_app_catalog_status.py`.

---

## Next

1. **Start Phase 3** — React foundation + TypeScript client + readiness/instruments/status vertical slice.
2. Do not begin Electron until the React+API path is proven.

---

## Notes

* V1 Streamlit Explorer unchanged.
* No schema/data changes in P1 or P2.
* Explore/Day/Maintenance HTTP routes deferred per roadmap.
* Status unavailable dependency returns HTTP 200 with `available: false` (P1 semantics); raised `AppUnavailableError` maps to HTTP 503.
