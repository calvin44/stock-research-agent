from typing import TypedDict


class StockIdentityResult(TypedDict):
    ticker: str
    company_name: str
    sector: str | None
    industry: str | None
    exchange: str


class PriceDataResult(TypedDict):
    current_price: float
    currency: str
    day_change_pct: float | None
    week_52_high: float
    week_52_low: float
    avg_volume: int | None


class FundamentalsResult(TypedDict):
    market_cap: str
    pe_ratio: float | None
    forward_pe: float | None
    revenue_ttm: str
    profit_margin: float | None
    debt_to_equity: float | None
    dividend_yield: float | None
    analyst_rating: str | None
