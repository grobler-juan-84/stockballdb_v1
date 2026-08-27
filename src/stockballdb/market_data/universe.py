"""Phase 2A Tiingo-sourced ETF universe and asset-type mapping."""

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

# StockBallDB-owned classification (not provider metadata). Lowercase vocabulary.
ASSET_TYPE_BY_SYMBOL: dict[str, str] = {
    symbol: "etf" for symbol in PHASE_2A_ETF_SYMBOLS
}


def asset_type_for_symbol(symbol: str) -> str:
    """Return canonical asset_type for a symbol, or raise if unknown."""
    try:
        return ASSET_TYPE_BY_SYMBOL[symbol]
    except KeyError as exc:
        raise KeyError(f"no asset_type mapping for symbol={symbol!r}") from exc
