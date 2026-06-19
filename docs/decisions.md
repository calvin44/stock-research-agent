# Design Decisions

This document records key architectural decisions made during development, 
along with the reasoning behind them. The goal is to help future readers 
(including future me) understand *why* the code looks the way it does, 
not just *what* it does.

---

## 1. TypedDict for tool returns, Pydantic for LLM output

**Decision:** Tool functions (yfinance, Tavily) return plain dicts typed 
with `TypedDict`. The final LLM-generated `StockAnalysis` uses a Pydantic 
`BaseModel`.

**Why:**
- Tool data is sanitized manually before construction (`safe_float`, 
  `safe_int`, `validate_ticker_info`) — the trust boundary is already 
  handled before the dict is built.
- LangChain's `@tool` decorator erases return type information after 
  `.invoke()` regardless of whether we use `dict`, `TypedDict`, or 
  Pydantic — so Pydantic's main runtime advantage doesn't survive 
  the LangChain boundary anyway.
- LLM-generated output is the genuinely *untrusted* boundary in this 
  system. Pydantic's validation earns its overhead there — it catches 
  hallucinated fields or wrong types before they reach the frontend.

**Trade-off accepted:** Two type systems coexist in the codebase. This 
is a deliberate choice based on where data risk is highest, not an 
oversight.

---

## 2. Plain dict → Pydantic → TypedDict (the evolution)

Early in development, `get_stock_info` returned a Pydantic `BaseModel`. 
This was reverted to a plain `dict` after observing that:
- the return type is erased after `.invoke()` anyway (IDE autocomplete 
  doesn't survive the LangChain tool boundary)
- Pydantic validation added overhead without a corresponding benefit 
  at this layer

Later, `TypedDict` was introduced (instead of staying with plain `dict`) 
specifically to:
- give integration tests a single source of truth for expected keys 
  (`set(SomeTypedDict.__annotations__.keys())`)
- document the tool's contract for future readers without paying 
  Pydantic's runtime cost

---

## 3. Unit tests vs integration tests

**Decision:** Pure functions (`safe_float`, `humanize_number`, etc.) are 
unit tested with no API calls. Tool functions are integration tested 
with real API calls, marked with `@pytest.mark.integration`.

**Why:**
- Unit tests for `utils.py` are fast, free, and deterministic — safe to 
  run on every change.
- Integration tests call real yfinance/Tavily APIs — slower, can incur 
  API costs, and are non-deterministic. They're separated so they can 
  be run selectively (`pytest -m integration`) rather than on every 
  save.

---

## 4. `validate_ticker_info` uses key count, not field presence

**Decision:** Ticker validity is checked via `len(info) <= 10` rather 
than checking for a specific field like `longName`.

**Why:**
- Empirically verified: yfinance returns ~1 key for an invalid ticker 
  and 180+ keys for a valid one. Checking total key count is more 
  robust to yfinance renaming or restructuring individual fields.

**Known limitation:** This is a heuristic, not a guarantee. If yfinance 
changes their "empty response" shape significantly, this threshold may 
need revisiting.