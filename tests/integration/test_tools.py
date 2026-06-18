from pytest import mark, raises

from backend.agent.tools.types import FundamentalsResult, PriceDataResult, StockIdentityResult
from backend.agent.tools.yfinance import get_fundamentals, get_price_data, get_stock_info


class TestGetStockInfo:
    @mark.integration
    def test_valid_ticker(self):
        ticker = "AAPL"
        result = get_stock_info.invoke(ticker)

        # Assert ticker
        assert result["ticker"] == ticker

        # Structure assertions
        assert isinstance(result, dict)
        expected_keys = set(StockIdentityResult.__annotations__.keys())
        assert set(result.keys()) == expected_keys

        # Non-null assertion for required fields
        assert result["company_name"] is not None
        assert result["exchange"] is not None

        # Optional type
        sector = result["sector"]
        industry = result["industry"]

        assert isinstance(sector, str) or sector is None
        assert isinstance(industry, str) or sector is None

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
        expected_keys = set(PriceDataResult.__annotations__.keys())
        assert set(result.keys()) == expected_keys

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
        expected_keys = set(FundamentalsResult.__annotations__.keys())
        assert set(result.keys()) == expected_keys

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
