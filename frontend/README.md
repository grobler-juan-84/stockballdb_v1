# StockBallDB V2 frontend (React + TypeScript)

Minimal P3 vertical slice: Status + Catalog against `stockballdb.api`.

## Prerequisites

- Node.js 20+
- Local FastAPI: `python -m stockballdb.api` (default `http://127.0.0.1:8765`)

## Commands

```bash
cd frontend
npm install
npm run dev      # http://127.0.0.1:5173
npm run test
npm run build
```

## Configuration

API base URL is set via `VITE_API_BASE_URL` (see `.env.development` / `.env.example`).
Components must not hardcode the host; use `src/config.ts` / the application client.

## Structure

- `src/features/` — pages (shell, status, catalog)
- `src/components/` — small presentational helpers
- `src/client/` — FastAPI application client + transport types

OpenAPI/codegen automation is intentionally deferred.
