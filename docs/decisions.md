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

---

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

---

## 7. Fixing field omission via comprehensive, explicit instructions

**Problem:** Beyond hallucination (fabricating data_sources), the LLM also 
exhibited the opposite failure mode — silently omitting required schema 
fields (`recent_news[].sentiment`, then `business_summary`) when 
`SYSTEM_PROMPT` never explicitly instructed it to produce them. Since 
`response_format` enforces strict Pydantic validation with no built-in 
retry, any omitted required field caused a hard crash 
(`StructuredOutputValidationError`), not a graceful degradation.

**Investigation:** Initially added retry logic to `run_research()`, 
assuming the failures were non-deterministic LLM flakiness. This proved 
ineffective — retrying the same request reproduced the *same* missing 
field every time, revealing the issue was a consistent prompt gap, not 
randomness. An audit of every field in `StockAnalysisLLMOutput` against 
the actual `SYSTEM_PROMPT` text showed three fields with no corresponding 
instruction at all: `business_summary`, `key_catalysts`, `competitive_position`.

**Fix:** Added explicit instructions to `SYSTEM_PROMPT` covering every 
previously-unmentioned field:
- Required `sentiment` classification per news item, with the basis for 
  classification specified (tone of headline/content).
- Required `business_summary`, `competitive_position`, and `key_catalysts`, 
  explicitly stating every schema field is required.

**Verification:** Ran `run_research("AAPL")` 5 times consecutively post-fix; 
all 5 succeeded with complete output (previously, roughly 1-in-3 to 1-in-2 
runs failed).

**Key learning:** When using strict `response_format` with no automatic 
repair, *every* field in the schema needs an explicit, corresponding 
instruction in the prompt — fields are not "self-explanatory" to the model 
just because their name or a Python comment describes their purpose. 
Python-level comments and docstrings on Pydantic models are invisible to 
the LLM; only the field name, type, and constraints (e.g. `Literal` options) 
are passed through `response_format`. A practical audit technique: list 
every schema field side-by-side with the prompt text and confirm each one 
has explicit coverage, rather than waiting for omissions to surface 
through trial and error.

---

## 8. Postgres for document registry and session memory

**Decision:** Use a single Postgres instance for both the document registry
(`documents` table, our schema) and LangGraph session memory (`checkpoints`
tables, LangGraph's schema).

**Why:**
- Document registry needs structured, queryable storage — SQL is the
  right tool (status filtering, hash lookups, ordered listing by date).
- LangGraph's `PostgresSaver` requires Postgres for persistent session
  memory across server restarts.
- One service instead of two — simpler operations, one connection string,
  one backup concern.
- Both concerns are administrative and relational, not vector — Qdrant
  handles vectors, Postgres handles everything else.

**Trade-off accepted:** Postgres runs as a Docker container, not a managed
cloud service. Data lives on the host machine's Docker volume. Acceptable
for local development and single-server deployment. A managed Postgres
addon (e.g. Railway's Postgres service) would be the production upgrade
path if data persistence guarantees become a hard requirement.

---

## 9. Single Qdrant collection with metadata filtering

**Decision:** All financial reports from all companies are stored in one
`financial_reports` collection. Company and fiscal year scoping happens
via metadata filters at query time (`metadata.company`, `metadata.fiscal_year`),
not via separate collections per company.

**Why:**
- Cross-company queries work naturally — "compare UNTR and AAPL margins"
  retrieves from both without joining collections.
- Simpler operations — one collection to create, monitor, and maintain.
- Qdrant metadata filtering is a first-class, performant feature designed
  for exactly this pattern.
- LangChain stores Document metadata nested under a `metadata` key in
  Qdrant's payload — filter keys must use `metadata.doc_id`, `metadata.company`
  etc. (confirmed via Qdrant dashboard inspection).

**Trade-off accepted:** Strict per-user data isolation would require separate
collections per user. Acceptable for current global shared library design
with no user authentication. Revisit when multi-user auth is introduced.

---

## 10. Content hash deduplication before indexing

**Decision:** SHA-256 hash of raw PDF bytes is computed before any registry
or Qdrant operations. If a matching hash exists with `status=indexed` and
chunks are confirmed present in Qdrant, the existing `doc_id` is returned
without re-indexing.

**Why:**
- Prevents duplicate chunks in Qdrant from accidental re-uploads.
- Duplicate chunks waste top-k retrieval slots — if k=5 and 3 slots are
  duplicates, effective unique retrieval drops to 2 chunks.
- Hash computed from raw bytes before any transformation — the only point
  where the complete, unmodified file is available in memory.
- SHA-256 chosen: no known practical collisions, modern standard, negligible
  performance difference vs MD5 for file-sized inputs.
- Qdrant chunk existence verified before returning early — handles the case
  where the collection was deleted while the registry record still says indexed.

**Trade-off accepted:** Deduplication adds one Postgres query and one Qdrant
query per upload. Negligible overhead compared to the indexing pipeline itself.

---

## 11. RecursiveCharacterTextSplitter over alternatives

**Decision:** Use `RecursiveCharacterTextSplitter` at `chunk_size=800` tokens,
`chunk_overlap=100` tokens (tiktoken `cl100k_base` encoding).

**Why:**
- Recursive splitter tries separators in order (`\n\n` → `\n` → ` ` → `""`)
  — always cuts at the most natural available boundary rather than a fixed
  character position.
- 800 tokens preserves paragraph-level reasoning for financial text where
  figures and their explanations often span 3-4 sentences together.
- 100 token overlap catches context split across chunk boundaries — a key
  sentence split at a boundary still appears fully in one adjacent chunk.
- Token-based (not character-based) via tiktoken — accurate for embedding
  model limits and billing.
- `SemanticChunker` and proposition chunking rejected as premature —
  RAGAS evaluation data should justify the extra cost before adopting
  more sophisticated strategies. Imperfect chunking is compensated downstream
  by hybrid search, reranking, and query transformation.

**Trade-off accepted:** Fixed parameters do not adapt per document type.
For unknown user-uploaded documents this is a known limitation. The field
is compensated downstream rather than solved at the chunking layer.

---

## 12. Sequential upload design (not concurrent)

**Decision:** Document uploads are processed sequentially. CPU-bound
operations (PDF extraction, chunking, hashing) are not wrapped in
`asyncio.to_thread()`.

**Why:**
- Single user, local machine — no concurrent upload scenario exists in
  the current scope.
- Sequential processing gives users a clear mental model: "your file is
  processing, please wait."
- Controlled OpenAI API costs — no concurrent embedding spikes from
  simultaneous uploads.
- Simpler code — `asyncio.to_thread()` wrapping adds complexity without
  observable benefit at current scale.

**Trade-off accepted:** CPU-bound operations (PyPDF extraction, text
splitting, SHA-256 hashing) block the event loop during indexing. For a
multi-tenant system with concurrent users, these operations would need
`asyncio.to_thread()` wrapping. Revisit before multi-user deployment.

**Known improvement:** Replace `vectorstore.add_documents()` with
`await vectorstore.aadd_documents()` for the embedding + Qdrant write
step — this is genuinely async and yields the event loop during the
OpenAI API calls. Not done because the sequential upload design makes it
imperceptible, but worth fixing before scaling.s