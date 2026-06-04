from langgraph.graph import MessagesState

from backend.schemas.stock import StockAnalysis


class StockResearchState(MessagesState):
    # Input
    ticker: str
    company_name: str
    sector: str | None
    industry: str | None
    exchange: str

    # Research progress
    price_data_fetched: bool
    fundamentals_fetched: bool
    news_fetched: bool
    research_complete: bool

    # Raw data (before synthesis)
    raw_price_data: dict
    raw_fundamentals: dict
    raw_news: list[dict]

    # Output
    analysis: StockAnalysis | None

    # Session
    follow_up_count: int
    session_id: str
    error_message: str | None
