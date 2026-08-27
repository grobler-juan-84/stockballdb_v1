# StockBallDB

**StockBallDB V1.0.0** — seven canonical V1 tables complete:

`trading_days` · `daily_market_data` · `market_outcomes` · `asset_regimes` · `macro_conditions` · `scheduled_events` · `calendar_context`

Historical financial and market-context database. Project philosophy, schema, sources, and definitions live under [`docs/`](docs/StockBallDB_index.md).

## Prerequisites

- Python 3.11+
- Local PostgreSQL (empty target database already created)
- Git
- `pandas_market_calendars==5.4.0` (pinned in `requirements.txt`)

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

Required variables:

```text
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@localhost:5432/stockballdb
TIINGO_API_KEY=...
FRED_API_KEY=...
```

`EIA_API_KEY` is unused in V1. Never commit `.env`.

### 4. Create an empty PostgreSQL database

Create the database named in `DATABASE_URL` (StockBallDB does not create it for you).

### 5. Build and validate V1

```bash
python -m stockballdb.build_v1
python -m stockballdb.validate_v1
```

`build_v1` runs preflight, migrations, all seven canonical builders (plus derive), whole-DB validation, and pytest. It is idempotent and fail-fast; it does not drop or wipe databases.

## Documentation

- Reproduction workflow (authoritative): [docs/StockBallDB_workflow.md](docs/StockBallDB_workflow.md) §12
- Full docs index: [docs/StockBallDB_index.md](docs/StockBallDB_index.md)

Individual table builders (`build_trading_days`, …) remain available for development; prefer `build_v1` for full reproduction.
