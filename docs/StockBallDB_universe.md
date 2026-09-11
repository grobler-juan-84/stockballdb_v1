# StockBallDB — Universe

> Companion docs: [index](StockBallDB_index.md) · [manifesto](StockBallDB_manifesto.md) · [schema](StockBallDB_schema.md) · [sources](StockBallDB_sources.md)

## Purpose

Defines the assets and market indicators in StockBallDB V1 scope. Expansion rules and historical-integrity principles live in the [manifesto](StockBallDB_manifesto.md).

Coverage goal: broad U.S. equities, major U.S. equity sectors, selected commodities / FX context — small enough to keep pipelines trustworthy, broad enough for useful market context.

## Implemented market symbols (V1)

**Currently ingested into `daily_market_data`:** **14 ETFs + WTI** (15 symbols).

### Broad U.S. Equity Market (ETF)

| Ticker  | Asset                          |
| ------- | ------------------------------ |
| **SPY** | SPDR S&P 500 ETF Trust         |
| **QQQ** | Invesco QQQ Trust — Nasdaq-100 |
| **IWM** | iShares Russell 2000 ETF       |

### U.S. Equity Sectors (ETF)

| Ticker   | Sector                 |
| -------- | ---------------------- |
| **XLB**  | Materials              |
| **XLC**  | Communication Services |
| **XLE**  | Energy                 |
| **XLF**  | Financials             |
| **XLI**  | Industrials            |
| **XLK**  | Technology             |
| **XLP**  | Consumer Staples       |
| **XLU**  | Utilities              |
| **XLV**  | Health Care            |
| **XLY**  | Consumer Discretionary |
| **XLRE** | Real Estate            |

### Additional market context

| Identifier  | Status | Notes |
| ----------- | ------ | ----- |
| **WTI**     | **IMPLEMENTED** | West Texas Intermediate spot (FRED `DCOILWTICO`, Cushing). Stored as close-only rows in `daily_market_data`. |
| **XAU/USD** | **UNRESOLVED** | Definition target: LBMA PM gold fix. **Not ingested.** Blocked on licensed source access. Do not substitute GLD or GC futures as canonical XAU/USD. |
| **DXY**     | **UNRESOLVED** | Definition target: ICE U.S. Dollar Index (USDX). **Not ingested.** Requires ICE license. **Do not substitute** Fed trade-weighted indexes (`DTWEXBGS` / `DTWEXAFEGS`) or UUP ETF as DXY. |

Prefer the underlying asset or index over an ETF proxy when reliable history exists (e.g. spot gold not GLD, WTI not USO, DXY not UUP).

Market-context rows share `daily_market_data` with ETFs — there is **no** separate context table. See [schema](StockBallDB_schema.md) and [sources](StockBallDB_sources.md).

## Other V1 datasets (not “symbols”)

| Dataset | Scope |
| ------- | ----- |
| Macro conditions | Locked FRED/ALFRED series in `macro_conditions` (`pmi` unresolved / omitted) |
| Scheduled events | `fomc`, `cpi`, `employment_situation`, `election` |
| Trading calendar | NYSE sessions via pinned `pandas_market_calendars` from 1957 |

## Future expansion

Illustrative candidates only — not commitments. Each addition needs a plausible research reason and must meet manifesto standards.

* VIX
* Additional yields / credit / international equity context
* Additional commodities, currencies
* Broader or longer-history equity indices; individual securities if research requires them

> **Start focused. Build reliably. Expand deliberately.**
