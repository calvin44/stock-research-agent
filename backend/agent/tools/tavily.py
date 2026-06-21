from datetime import datetime

from langchain_core.tools import tool
from langchain_tavily import TavilySearch

from backend.agent.prompts import COMPETITIVE_QUERY, EARNINGS_QUERY, STOCK_NEWS_QUERY
from backend.agent.tools.types import SearchResult

# load_dotenv()
# Note: load_dotenv() should be called in main.py entry point


def search_tavily(query: str, max_results: int = 3) -> list[SearchResult]:
    """Search web using Tavily API"""
    search = TavilySearch(max_results=max_results)
    results = search.invoke(query)

    if "error" in results:
        raise ValueError(str(results["error"]))

    return [
        {
            "title": item["title"],
            "content": item["content"][:1000],
            "url": item["url"],
        }
        for item in results.get("results", [])
    ]


@tool
def search_stock_news(company_name: str, ticker: str) -> list[SearchResult]:
    """Search stock news using Tavily API"""
    try:
        query = STOCK_NEWS_QUERY.format(
            company_name=company_name, ticker=ticker, year=datetime.now().year
        )
        return search_tavily(query)
    except ValueError as e:
        raise ValueError(f"News search failed for {ticker}: {e}")
    except Exception as e:
        raise ValueError(f"Unexpected error searching news for {ticker}: {e}")


@tool
def search_competitive_landscape(company_name: str, industry: str) -> list[SearchResult]:
    """Search competitive landscape using Tavily API"""
    try:
        query = COMPETITIVE_QUERY.format(
            company_name=company_name, industry=industry, year=datetime.now().year
        )
        return search_tavily(query)
    except ValueError as e:
        raise ValueError(f"Competitive landscape search failed for {company_name}: {e}")
    except Exception as e:
        raise ValueError(
            f"Unexpected error searching competitive landscape for {company_name}: {e}"
        )


@tool
def search_earnings_guidance(ticker: str, company_name: str) -> list[SearchResult]:
    """Search for recent earnings and forward guidance for a stock"""
    try:
        query = EARNINGS_QUERY.format(
            ticker=ticker, company_name=company_name, year=datetime.now().year
        )
        return search_tavily(query)
    except ValueError as e:
        raise ValueError(f"Earning guidance search failed for {ticker}: {e}")
    except Exception as e:
        raise ValueError(f"Unexpected error searching earning guidance for {ticker}: {e}")
