# StockBallDB — Universe

**Version 0.01**  
**Date:** 2026-08-23

> Companion docs: [index](StockBallDB_index.md) · [manifesto](StockBallDB_manifesto.md) · [schema](StockBallDB_schema.md)

## Purpose

Defines the assets and market indicators currently in StockBallDB scope. Version 1 is a starting point, not a permanent boundary. Expansion rules and historical-integrity principles live in the [manifesto](StockBallDB_manifesto.md).

Initial coverage: broad U.S. equities, major U.S. equity sectors, commodities, and the U.S. dollar — small enough to build pipelines and validation first, broad enough for useful market context.

## Initial Universe (17)

### Broad U.S. Equity Market

| Ticker  | Asset                          |
| ------- | ------------------------------ |
| **SPY** | SPDR S&P 500 ETF Trust         |
| **QQQ** | Invesco QQQ Trust — Nasdaq-100 |
| **IWM** | iShares Russell 2000 ETF       |

### U.S. Equity Sectors

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

### Additional Market Context

| Identifier  | Asset / Indicator                 |
| ----------- | --------------------------------- |
| **WTI**     | West Texas Intermediate Crude Oil | **LOCKED** — FRED DCOILWTICO (spot Cushing) |
| **XAU/USD** | Spot Gold (LBMA PM fix target)    | **UNRESOLVED** — source/licensing |
| **DXY**     | U.S. Dollar Index (ICE USDX)      | **UNRESOLVED** — source requires ICE license |

Phase 5A authoritative contract: [StockBallDB_phase5a_market_context_contract.md](StockBallDB_phase5a_market_context_contract.md).

Prefer the underlying asset or index over an ETF proxy when reliable history exists (e.g. spot gold not GLD, WTI not USO, DXY not UUP). **Do not substitute** DTWEXBGS for DXY.

## Future Expansion

Illustrative candidates only — not commitments. Each addition needs a plausible research reason and must meet manifesto standards.

* VIX  
* U.S. Treasury yields; Treasury securities or bond ETFs  
* Credit spreads  
* International / emerging-market equity indices or ETFs  
* Additional commodities, currencies, and currency indices  
* Bitcoin and other major digital assets (where historically appropriate)  
* Broader or longer-history equity indices; individual securities if research requires them  
* Further macro and market indicators  

> **Start focused. Build reliably. Expand deliberately.**
