# StockBallDB

Historical financial and market-context database. Project philosophy, schema, sources, and definitions live under [`docs/`](docs/StockBallDB_index.md).

## Prerequisites

- Python 3.11+
- Local PostgreSQL
- Git

## Setup

### 1. Clone and create a virtual environment

```bash
git clone <repository-url>
cd MoneyBallDB-V1

python -m venv .venv
```

Windows (PowerShell):

```powershell
.\.venv\Scripts\Activate.ps1
```

macOS / Linux:

```bash
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
pip install -e .
```

### 3. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and set `DATABASE_URL` (example):

```text
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@localhost:5432/stockballdb
```

Provider API keys (`TIINGO_API_KEY`, `FRED_API_KEY`, `EIA_API_KEY`) are placeholders for later phases until used.

Never commit `.env`.

### 4. Create a local database

Create an empty PostgreSQL database matching `DATABASE_URL`.

### 5. Verify the connection

```bash
python -m stockballdb.check_db
```

### 6. Apply migrations

```bash
alembic upgrade head
```

### 7. Build the trading calendar

```bash
python -m stockballdb.build_trading_days
```

Generates `trading_days` from 1957 through the latest completed NYSE session (`America/New_York`), upserts idempotently, and validates.

### 8. Build daily market data (Phase 2A ETFs)

Requires `TIINGO_API_KEY` in `.env`.

```bash
python -m stockballdb.build_daily_market_data
```

Fetches the 14 Tiingo ETFs, normalizes raw/adjusted OHLCV plus `divCash`/`splitFactor`, aligns dates to `trading_days`, upserts idempotently, and validates. Observed sync does not overwrite derived columns on conflict.

### 9. Derive daily market fields (Phase 2B)

```bash
python -m stockballdb.derive_daily_market_data
```

Populates `return_1d`, `gap_pct`, `intraday_return`, `range_pct`, and `drawdown_from_high` from canonical observations (adjusted for cross-day economic fields; raw for same-session fields). Idempotent; does not modify observed OHLCV.

### 10. Build market outcomes (Phase 2C)

```bash
python -m stockballdb.build_market_outcomes
```

Derives retrospective forward labels from canonical `daily_market_data` only (no API calls). Incomplete horizons are `NULL`. These values were **not** available on `date`.

### 11. Build asset regimes (Phase 2D)

```bash
python -m stockballdb.build_asset_regimes
```

Derives point-in-time asset-state measures and regimes from `daily_market_data` only (no API calls; no `market_outcomes`). Uses information through date `t` only.

### 12. Build macro conditions (Phase 2E)

```bash
python -m stockballdb.build_macro_conditions
```

Fetches FRED/ALFRED (`FRED_API_KEY`), reconstructs PIT vintages where required, aligns to `trading_days`, forward-fills approved lower-frequency fields, derives yield curve and regimes. `pmi` is deferred from V1.

### 13. Build scheduled events (Phase 2F)

```bash
python -m stockballdb.build_scheduled_events
```

Builds the scheduled-event **occurrence calendar** (`fomc`, `cpi`, `employment_situation`, `election`) from Federal Reserve pages and ALFRED first-print dates. Idempotent full replace. Does not store consensus/surprise or mutate frozen tables. Earnings and unscheduled Fed actions are deferred.

### 14. Build calendar context (Phase 2G)

```bash
python -m stockballdb.build_calendar_context
```

Derives 1:1 `calendar_context` from `trading_days`, pinned NYSE early-close/holiday metadata, and `scheduled_events`. Retrospective `days_since_last_*` only — no forward event distances. Idempotent; does not call Tiingo/FRED.

### 15. Run tests

```bash
pytest
```

## Project documentation

Start at [docs/StockBallDB_index.md](docs/StockBallDB_index.md).
