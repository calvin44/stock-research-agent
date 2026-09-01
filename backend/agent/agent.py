from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain.messages import HumanMessage

from backend.agent.prompts import SYSTEM_PROMPT
from backend.agent.tools import ALL_TOOLS
from backend.schemas.stock import StockAnalysis, StockAnalysisLLMOutput

MODEL_NAME = "gpt-4o-mini"

_model = None
_agent = None


def _get_agent():
    """Lazy-initialize the agent — reads OPENAI_API_KEY at call time, not import time."""
    global _model, _agent
    if _agent is None:
        _model = init_chat_model(model=MODEL_NAME, temperature=0.3)
        _agent = create_agent(
            model=_model,
            tools=ALL_TOOLS,
            system_prompt=SYSTEM_PROMPT,
            response_format=StockAnalysisLLMOutput,
        )
    return _agent


def run_research(ticker: str) -> StockAnalysis:
    """Run the stock research agent and return a complete StockAnalysis."""
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
