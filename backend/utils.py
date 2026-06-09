import math
from typing import Any


def fmt_pct(x: float | None) -> float | None:
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
