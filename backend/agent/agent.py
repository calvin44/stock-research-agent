"""
LangGraph agent — core research and chat orchestration.
Supports two modes:
  - Stateless (run_research): one-shot structured analysis, no memory
  - Stateful (_get_agent with checkpointer): session-based chat with memory
"""

from functools import lru_cache

from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain.messages import HumanMessage
from langgraph.checkpoint.base import BaseCheckpointSaver

from backend.agent.prompts import SYSTEM_PROMPT
from backend.agent.tools import ALL_TOOLS
from backend.schemas.stock import StockAnalysis, StockAnalysisLLMOutput

MODEL_NAME = "gpt-4o-mini"


@lru_cache(maxsize=1)
def _get_model():
    """Initialize LLM — runs once, cached forever."""
    return init_chat_model(model=MODEL_NAME, temperature=0.3)


@lru_cache(maxsize=1)
def _get_stateless_agent():
    """
    Stateless agent for one-shot research.
    Uses response_format → returns structured StockAnalysisLLMOutput.
    No checkpointer → no memory between calls.
    """
    return create_agent(
        model=_get_model(),
        tools=ALL_TOOLS,
        system_prompt=SYSTEM_PROMPT,
        response_format=StockAnalysisLLMOutput,
    )


def _get_agent(checkpointer: BaseCheckpointSaver | None = None):
    """
    Return the appropriate agent instance.

    checkpointer=None  → stateless agent (lru_cache)
    checkpointer=saver → stateful agent with memory (new instance each time)
    """
    if checkpointer is None:
        return _get_stateless_agent()

    # stateful agent — checkpointer is unhashable so can't use lru_cache
    # create_agent is cheap compared to model init, acceptable to call each time
    return create_agent(
        model=_get_model(),
        tools=ALL_TOOLS,
        system_prompt=SYSTEM_PROMPT,
        checkpointer=checkpointer,
    )


def run_research(ticker: str) -> StockAnalysis:
    """Run one-shot stock research — stateless, returns structured StockAnalysis."""
    max_retries = 2
    last_error = None

    for _ in range(max_retries + 1):
        try:
            result = _get_agent().invoke(
                {
                    "messages": [
                        HumanMessage(
                            content=f"Help me do a comprehensive research on the ticker {ticker}"
                        )
                    ]
                },
                config={"recursion_limit": 15},
            )
            llm_output = result["structured_response"]
            return StockAnalysis(**llm_output.model_dump())
        except Exception as e:
            last_error = e
            continue

    raise ValueError(
        f"Failed to generate research for {ticker} after {max_retries + 1} attempts: {last_error}"
    )
