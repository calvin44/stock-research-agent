import yfinance as yf
from langchain_core.tools import tool

from backend.agent.tools.types import FundamentalsResult, PriceDataResult, StockIdentityResult
from backend.utils import (
    fmt_percentage,
    humanize_number,
    safe_float,
    validate_ticker_info,
)


def fetch_yfinance(ticker: str) -> dict:
    """Fetch raw yfinance info dict for a given ticker."""
    stock = yf.Ticker(ticker)
    return stock.info


@tool
def get_stock_info(ticker: str) -> StockIdentityResult:
    """Get basic company information and validate ticker exists."""
    try:
        info = fetch_yfinance(ticker)

        validate_ticker_info(info, ticker)

        company_name = info.get("longName")
        exchange = info.get("exchange")

        # safe guard type using assertion
        assert company_name is not None
        assert exchange is not None

        return {
            "ticker": ticker.upper(),
            "company_name": company_name,
            "sector": info.get("sector"),
            "industry": info.get("industry"),
            "exchange": exchange,
        }
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"Failed to fetch data for {ticker}: {str(e)}")


@tool
def get_price_data(ticker: str) -> PriceDataResult:
    """Get price data from yfinance"""
    try:
        info = fetch_yfinance(ticker)

        validate_ticker_info(info, ticker)

        prev_close = safe_float(info.get("previousClose"))
        current_price = safe_float(info.get("currentPrice"))

        if prev_close is None or current_price is None or prev_close == 0:
            day_change_pct = None
        else:
            day_change_pct = ((current_price - prev_close) / prev_close) * 100

        # safe guard type using assertion
        assert current_price is not None

        week_52_high = safe_float(info.get("fiftyTwoWeekHigh"))
        assert week_52_high is not None

        week_52_low = safe_float(info.get("fiftyTwoWeekLow"))
        assert week_52_low is not None

        return {
            "current_price": current_price,
            "currency": info.get("currency", ""),
            "day_change_pct": fmt_percentage(day_change_pct),
            "week_52_high": week_52_high,
            "week_52_low": week_52_low,
            "avg_volume": info.get("averageVolume"),
        }

    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"Failed to fetch data for {ticker}: {str(e)}")


@tool
def get_fundamentals(ticker: str) -> FundamentalsResult:
    """Get fundamental metrics from yfinance"""
    try:
        info = fetch_yfinance(ticker)

        validate_ticker_info(info, ticker)

        raw = info.get("recommendationKey")
        analyst_rating = str(raw).replace("_", " ").title() if raw else None

        # safe guard type using type assertion
        market_cap = humanize_number(info.get("marketCap"))
        assert market_cap is not None

        revenue_ttm = humanize_number(info.get("totalRevenue"))
        assert revenue_ttm is not None

        return {
            "market_cap": market_cap,
            "pe_ratio": fmt_percentage(safe_float(info.get("trailingPE"))),
            "forward_pe": fmt_percentage(safe_float(info.get("forwardPE"))),
            "revenue_ttm": revenue_ttm,
            "profit_margin": fmt_percentage(safe_float(info.get("profitMargins"))),
            "debt_to_equity": safe_float(info.get("debtToEquity")),
            "dividend_yield": safe_float(info.get("dividendYield")),
            "analyst_rating": analyst_rating,
        }
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"Failed to fetch data for {ticker}: {str(e)}")
