# Stock Research Agent

[![Tests](https://github.com/calvin44/stock-research-agent/actions/workflows/test.yml/badge.svg)](https://github.com/calvin44/stock-research-agent/actions/workflows/test.yml)

An AI-powered stock research API built with FastAPI and LangGraph. Given a ticker symbol, it autonomously fetches real-time price data, fundamentals, news, and competitive analysis, then synthesizes a structured research report — without ever giving buy/sell recommendations.

## Demo

```
GET /research/AAPL
```

Returns a complete structured analysis covering price snapshot, fundamentals, recent news with sentiment, bull/bear case, risk factors, and cited sources.

## Architecture

| Layer | Technology |
|---|---|
| API | FastAPI |
| Agent orchestration | LangGraph (`create_agent`) |
| LLM | OpenAI `gpt-4o-mini` |
| Market data | yfinance |
| Web search | Tavily |
| Validation | Pydantic |
| Testing | pytest |
| Package management | uv |

**Request flow:**

```
Client → FastAPI route → run_research() → LangGraph agent
       → [6 tools: yfinance x3, Tavily x3] → LLM synthesis
       → Pydantic-validated StockAnalysis → JSON response
```

## Key Engineering Decisions

See [docs/decisions.md](docs/decisions.md) for detailed reasoning behind architectural choices, including:

- Why `TypedDict` is used for tool return types, but `Pydantic` for the final LLM output
- How LLM hallucination (fabricated data sources, fabricated timestamps, silently omitted fields) was diagnosed and fixed through iterative prompt engineering
- The unit vs. integration testing strategy, and what is and isn't mocked

## Setup

```bash
# Clone the repo
git clone <your-repo-url>
cd stock-research-agent

# Install dependencies
uv sync

# Set up environment variables
cp .env.example .env
# then edit .env and add your OPENAI_API_KEY and TAVILY_API_KEY
```

## Running

```bash
uvicorn backend.main:app --reload
```

The API will be available at `http://localhost:8000`.

## API Usage

### Get stock research

```bash
curl http://localhost:8000/research/AAPL
```

**Response:**

```json
{
  "ticker": "AAPL",
  "company_name": "Apple Inc.",
  "sector": "Technology",
  "industry": "Consumer Electronics",
  "exchange": "NMS",
  "price_snapshot": {
    "current_price": 298.01,
    "currency": "USD",
    "day_change_pct": 0.7,
    "week_52_high": 317.4,
    "week_52_low": 198.96,
    "avg_volume": 47300354
  },
  "fundamentals": {
    "market_cap": "4.38T",
    "pe_ratio": 36.12,
    "analyst_rating": "Buy"
  },
  "recent_news": [
    {
      "headline": "...",
      "sentiment": "neutral",
      "source_url": "https://..."
    }
  ],
  "bull_case": ["..."],
  "bear_case": ["..."],
  "risk_factors": [{"factor": "...", "severity": "high", "explanation": "..."}],
  "disclaimer": "This analysis is for informational purposes only and does not constitute financial advice.",
  "data_sources": ["https://..."],
  "generated_at": "2026-06-23T22:56:15.040429Z"
}
```

*(Response truncated for readability — see full schema in `backend/schemas/stock.py`.)*

Interactive API documentation is available at `/docs` once the server is running.

## Testing

```bash
# Run all tests
pytest tests/

# Run only fast unit tests (no API calls)
pytest tests/unit/

# Run integration tests (makes real LLM/yfinance/Tavily calls)
pytest tests/integration/ -m integration
```

**Coverage:**

- 21 unit tests — pure utility functions (`safe_float`, `humanize_number`, `validate_ticker_info`, etc.), no network calls
- 13 integration tests — real API calls against yfinance, Tavily, and the full LangGraph agent, including regression tests for previously-fixed hallucination bugs

## Disclaimer

This tool is for informational and research purposes only and does not constitute financial advice. It does not provide buy, sell, or hold recommendations. Always consult a licensed financial advisor before making investment decisions.

## Future Enhancements

- **Session/state tracking** — a `StockResearchState` schema and `AgentMiddleware` design were prototyped to support multi-turn follow-up questions and progress tracking, but deferred since the current single-shot research flow doesn't require them yet.
- **Frontend** — a Next.js interface for browsing research results visually.
- **CI/CD** — GitHub Actions workflow to run the test suite automatically on push.
- **Comparison mode** — research and compare multiple tickers side by side.