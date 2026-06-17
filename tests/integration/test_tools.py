from pytest import mark, raises

from backend.agent.tools.yfinance import get_price_data, get_stock_info


class TestGetStockInfo:
    @mark.integration
    def test_valid_ticker(self):
        ticker = "AAPL"
        result = get_stock_info.invoke(ticker)

        # Assert ticker
        assert result["ticker"] == ticker

        # Structure assertions
        assert isinstance(result, dict)
        assert "company_name" in result
        assert "sector" in result
        assert "industry" in result
        assert "exchange" in result

        # Non-null assertion for required fields
        assert result["company_name"] is not None
        assert result["exchange"] is not None

        # Optional type
        sector = result["sector"]
        assert isinstance(sector, str) or sector is None

        industry = result["industry"]
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
        ticker = "AAPL"
        result = get_price_data.invoke(ticker)

        # Structure assertions
        assert isinstance(result, dict)
        assert "current_price" in result
        assert "currency" in result
        assert "day_change_pct" in result
        assert "week_52_high" in result
        assert "week_52_low" in result
        assert "avg_volume" in result

        # Value type assertion
        assert isinstance(result["current_price"], float)
        assert isinstance(result["currency"], str)

        day_chance_pct = result["day_change_pct"]
        assert isinstance(day_chance_pct, float) or day_chance_pct is None

        assert isinstance(result["week_52_high"], float)
        assert isinstance(result["week_52_low"], float)

        avg_volume = result["avg_volume"]
        assert isinstance(avg_volume, int) or avg_volume is None

    @mark.integration
    def test_invalid_ticker(self):
        ticker = "INVALID_TICKER"
        with raises(ValueError) as exp_info:
            get_price_data.invoke(ticker)
        assert ticker in str(exp_info.value)
