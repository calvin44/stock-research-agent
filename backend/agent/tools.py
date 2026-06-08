import yfinance as yf
from langchain_core.tools import tool


@tool
def get_stock_info(ticker: str) -> dict:
    """Get basic company information and validate ticker exists."""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        company_name = info.get("longName")
        exchange = info.get("exchange")

        if not info or company_name is None or exchange is None:
            raise ValueError(
                f"Ticker '{ticker}' not found. "
                f"Please verify the ticker symbol is correct. "
                f"Example valid tickers: AAPL, TSLA, 2330.TW"
            )

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
