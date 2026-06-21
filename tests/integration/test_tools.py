from pytest import mark, raises

from backend.agent.tools.tavily import (
    search_competitive_landscape,
    search_earnings_guidance,
    search_stock_news,
)
from backend.agent.tools.types import (
    FundamentalsResult,
    PriceDataResult,
    SearchResult,
    StockIdentityResult,
)
from backend.agent.tools.yfinance import get_fundamentals, get_price_data, get_stock_info


def assert_valid_search_result(result: list[SearchResult]) -> None:
    # Structure assertion
    assert isinstance(result, list)
    assert len(result) > 0
    assert len(result) <= 3

    # Assert list content
    for item in result:
        assert isinstance(item, dict)
        expected_keys = set(SearchResult.__annotations__.keys())
        assert set(item.keys()) == expected_keys
        assert isinstance(item["title"], str)
        assert isinstance(item["content"], str)
        assert isinstance(item["url"], str)


# --- yfinance tools ---


class TestGetStockInfo:
    @mark.integration
    def test_valid_ticker(self):
        ticker = "AAPL"
        result = get_stock_info.invoke(ticker)

        # Assert ticker
        assert result["ticker"] == ticker

        # Structure assertions
        assert isinstance(result, dict)
        assert set(result.keys()) == set(StockIdentityResult.__annotations__.keys())

        # Non-null assertion for required fields
        assert result["company_name"] is not None
        assert result["exchange"] is not None

        # Optional type
        sector = result["sector"]
        industry = result["industry"]

        assert isinstance(sector, str) or sector is None
        assert isinstance(industry, str) or industry is None

    @mark.integration
    def test_invalid_ticker(self):
        ticker = "INVALID_TICKER"
        with raises(ValueError) as exp_info:
            get_stock_info.invoke(ticker)
        assert ticker in str(exp_info.value)


class TestGetPriceData:
    @mark.integration
    def test_valid_ticker(self):
        result = get_price_data.invoke("AAPL")

        # Structure assertions
        assert isinstance(result, dict)
        assert set(result.keys()) == set(PriceDataResult.__annotations__.keys())

        # Value type assertion
        assert isinstance(result["current_price"], float)
        assert isinstance(result["currency"], str)
        assert isinstance(result["week_52_high"], float)
        assert isinstance(result["week_52_low"], float)

        # Optional type assertion
        day_chance_pct = result["day_change_pct"]
        avg_volume = result["avg_volume"]

        assert isinstance(day_chance_pct, float) or day_chance_pct is None
        assert isinstance(avg_volume, int) or avg_volume is None

    @mark.integration
    def test_invalid_ticker(self):
        ticker = "INVALID_TICKER"
        with raises(ValueError) as exp_info:
            get_price_data.invoke(ticker)
        assert ticker in str(exp_info.value)


class TestGetFundamentals:
    @mark.integration
    def test_valid_ticker(self):
        result = get_fundamentals.invoke("AAPL")

        # Structure assertion
        assert isinstance(result, dict)
        assert set(result.keys()) == set(FundamentalsResult.__annotations__.keys())

        # Value type assertion
        assert isinstance(result["market_cap"], str)
        assert isinstance(result["revenue_ttm"], str)

        # Optional type assertion
        pe_ratio = result["pe_ratio"]
        forward_pe = result["forward_pe"]
        profit_margin = result["profit_margin"]
        debt_to_equity = result["debt_to_equity"]
        dividend_yield = result["dividend_yield"]
        analyst_rating = result["analyst_rating"]

        assert isinstance(pe_ratio, float) or pe_ratio is None
        assert isinstance(forward_pe, float) or forward_pe is None
        assert isinstance(profit_margin, float) or profit_margin is None
        assert isinstance(debt_to_equity, float) or debt_to_equity is None
        assert isinstance(dividend_yield, float) or dividend_yield is None
        assert isinstance(analyst_rating, str) or analyst_rating is None

    @mark.integration
    def test_invalid_ticker(self):
        ticker = "INVALID_TICKER"
        with raises(ValueError) as exp_info:
            get_fundamentals.invoke(ticker)
        assert ticker in str(exp_info.value)


# --- tavily tools ---


class TestSearchStockNews:
    company_name = "Apple Inc"
    ticker = "AAPL"

    @mark.integration
    def test_valid_search(self):
        result = search_stock_news.invoke(
            {"company_name": self.company_name, "ticker": self.ticker}
        )
        assert_valid_search_result(result)


class TestSearchCompetitiveLandscape:
    company_name = "Apple Inc"
    industry = "Consumer Electronics"

    @mark.integration
    def test_valid_search(self):
        result = search_competitive_landscape.invoke(
            {"company_name": self.company_name, "industry": self.industry}
        )
        assert_valid_search_result(result)


class TestSearchEarningsGuidance:
    company_name = "Apple Inc"
    ticker = "AAPL"

    @mark.integration
    def test_valid_search(self):
        result = search_earnings_guidance.invoke(
            {"company_name": self.company_name, "ticker": self.ticker}
        )
        assert_valid_search_result(result)
