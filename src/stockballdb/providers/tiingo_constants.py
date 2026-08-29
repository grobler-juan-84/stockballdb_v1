"""Tiingo constants shared across provider and tests."""

TIINGO_DAILY_PRICES_URL = "https://api.tiingo.com/tiingo/daily/{ticker}/prices"
DEFAULT_START_DATE = "1957-01-01"

TIINGO_PRICE_FIELDS = frozenset(
    {
        "date",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "adjOpen",
        "adjHigh",
        "adjLow",
        "adjClose",
        "adjVolume",
        "divCash",
        "splitFactor",
    }
)
