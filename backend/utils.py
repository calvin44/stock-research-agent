import math
from typing import Any


def validate_ticker_info(info: dict, ticker: str) -> None:
    """
    Validate yfinance info dict contains required fields.
    Raises ValueERror is ticker is invalid or data is missing
    """
    # successful info has 100+ keys
    if not info or len(info) <= 10:
        raise ValueError(
            f"Ticker '{ticker}' not found. "
            f"Please verify the ticker symbol is correct. "
            f"Example valid tickers: AAPL, TSLA, 2330.TW"
        )


def fmt_percentage(x: float | None) -> float | None:
    """Safely round number"""
    return None if x is None else round(x, 2)


def safe_float(x: Any) -> float | None:
    """Safely parse float variable, otherwise return None"""
    try:
        if x is None:
            return None
        x = float(x)
        if math.isnan(x):
            return None
        return x
    except (TypeError, ValueError):
        return None


def humanize_number(value: int | float | None) -> str | None:
    if value is None:
        return None

    value = safe_float(value)
    if value is None:
        return None
    if value >= 1_000_000_000_000:
        return f"{value / 1_000_000_000_000:.2f}T"
    elif value >= 1_000_000_000:
        return f"{value / 1_000_000_000:.2f}B"
    elif value >= 1_000_000:
        return f"{value / 1_000_000:.2f}M"
    else:
        return f"{value:.0f}"
