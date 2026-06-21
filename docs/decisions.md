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

## 5. Excluding `generated_at` from LLM-generated output

**Problem:** The original `StockAnalysis` schema included `generated_at: datetime` 
as a field the LLM was expected to populate via `response_format`. In practice, 
the LLM fabricated suspiciously round timestamps (e.g. `12:00:00`, sometimes 
with dates years in the past) instead of producing the actual current time — 
it has no reliable way to know the real wall-clock time at generation.

**Fix:** Split the schema into two classes:
- `StockAnalysisLLMOutput` — the schema actually passed to `response_format`, 
  containing only fields the LLM can legitimately produce from tool data.
- `StockAnalysis(StockAnalysisLLMOutput)` — adds `generated_at` with 
  `Field(default_factory=lambda: datetime.now(UTC))`, set programmatically 
  after the agent call completes, never exposed to the LLM.

**Key learning:** `response_format` requires the LLM to populate every field 
in the given schema — `Field(default_factory=...)` has no effect on LLM-facing 
schemas, since the LLM doesn't know or respect Pydantic defaults. Defaults 
only work when *Python code* instantiates the model without explicitly 
passing that field. Any field that shouldn't be LLM-controlled must be 
excluded from the schema entirely, not just given a default.

---

## 6. Fixing `data_sources` hallucination via explicit, mechanical prompting

**Problem:** Despite `SYSTEM_PROMPT` already saying "never fabricate data," 
the LLM consistently invented plausible-sounding financial news brand names 
in `data_sources` (e.g. "CNBC", "Yahoo Finance", "Statista") that never 
appeared in any actual tool result. This is a pattern-matching failure: the 
LLM associates "financial analysis" with well-known publisher names rather 
than grounding strictly in the URLs it was actually given.

**Fix:** Added an explicit, mechanical instruction to `SYSTEM_PROMPT`:

> For `data_sources` specifically: only include URLs that appeared literally 
> in your tool call results. Do NOT include the names of well-known financial 
> websites (e.g. "Yahoo Finance", "CNBC", "Bloomberg") unless their exact URL 
> was returned by a tool call. If a tool result's content is from an 
> unfamiliar or unclear source, use the URL as-is rather than guessing the 
> publisher's name.

**Result:** Verified by inspecting raw `ToolMessage` content alongside the 
final `data_sources` output — after the fix, every entry was a real, 
traceable URL matching an actual tool result, rather than a generic brand 
name.

**Key learning:** Vague instructions ("don't fabricate," "use real sources") 
are insufficient against learned associations in the model. Concrete, 
mechanical, falsifiable instructions (e.g. "copy URLs verbatim, don't 
substitute a publisher name") are far more effective at interrupting 
hallucination patterns — and the fix should be verified empirically by 
tracing output back to actual tool call results, not just by re-reading the 
prompt and assuming it will work.