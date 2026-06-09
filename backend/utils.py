import math
from typing import Any


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


def fmt_market_cap(market_cap: int | float | None) -> str | None:
    if market_cap is None:
        return None

    value = safe_float(market_cap)
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
