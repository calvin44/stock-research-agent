from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field


class PriceSnapshot(BaseModel):
    current_price: float
    currency: str
    day_change_pct: float | None
    week_52_high: float
    week_52_low: float
    avg_volume: int | None


class Fundamentals(BaseModel):
    market_cap: str  # human readable e.g. "1.2T"
    pe_ratio: float | None
    forward_pe: float | None
    revenue_ttm: str  # trailing 12 months
    profit_margin: float | None
    debt_to_equity: float | None
    dividend_yield: float | None
    analyst_rating: str | None


class NewsItem(BaseModel):
    headline: str
    summary: str
    sentiment: Literal["positive", "neutral", "negative"]
    date: str
    source_url: str


class RiskFactor(BaseModel):
    factor: str
    severity: Literal["high", "medium", "low"]
    explanation: str


class StockAnalysisLLMOutput(BaseModel):
    """Fields the LLM is responsible for producing"""

    # Identity
    ticker: str
    company_name: str
    sector: str | None
    industry: str | None
    exchange: str

    # Data
    price_snapshot: PriceSnapshot
    fundamentals: Fundamentals
    recent_news: list[NewsItem]

    # AI Analysis
    business_summary: str  # 2-3 sentences what company does
    bull_case: list[str]  # reasons stock could go up
    bear_case: list[str]  # reasons stock could go down
    risk_factors: list[RiskFactor]
    key_catalysts: list[str]  # upcoming events to watch
    competitive_position: str  # how it stands vs competitors

    # Meta
    disclaimer: str  # always include — not financial advice
    data_sources: list[str]


class StockAnalysis(StockAnalysisLLMOutput):
    """The final object - adds generated_at programatically"""

    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
