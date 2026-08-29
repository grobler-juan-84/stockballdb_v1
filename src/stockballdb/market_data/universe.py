"""Market data universe: Phase 2A ETFs and Phase 5 close-only context assets."""

PHASE_2A_ETF_SYMBOLS: tuple[str, ...] = (
    "SPY",
    "QQQ",
    "IWM",
    "XLB",
    "XLC",
    "XLE",
    "XLF",
    "XLI",
    "XLK",
    "XLP",
    "XLU",
    "XLV",
    "XLY",
    "XLRE",
)

# Phase 5A locked close-only context (implemented in Phase 5B).
WTI_SYMBOL = "WTI"
CLOSE_ONLY_SYMBOLS: tuple[str, ...] = (WTI_SYMBOL,)

V1_MARKET_SYMBOLS: tuple[str, ...] = PHASE_2A_ETF_SYMBOLS + CLOSE_ONLY_SYMBOLS
V1_MARKET_SYMBOL_COUNT = len(V1_MARKET_SYMBOLS)
EXPECTED_ETF_COUNT = len(PHASE_2A_ETF_SYMBOLS)

# StockBallDB-owned classification (not provider metadata). Lowercase vocabulary.
ASSET_TYPE_BY_SYMBOL: dict[str, str] = {
    symbol: "etf" for symbol in PHASE_2A_ETF_SYMBOLS
}
ASSET_TYPE_BY_SYMBOL[WTI_SYMBOL] = "commodity"


def is_close_only_symbol(symbol: str) -> bool:
    """Return True when symbol stores a single daily level in ``close`` only."""
    return symbol.upper() in CLOSE_ONLY_SYMBOLS


def asset_type_for_symbol(symbol: str) -> str:
    """Return canonical asset_type for a symbol, or raise if unknown."""
    try:
        return ASSET_TYPE_BY_SYMBOL[symbol]
    except KeyError as exc:
        raise KeyError(f"no asset_type mapping for symbol={symbol!r}") from exc
