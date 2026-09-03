# pyright: reportArgumentType=false
"""
Chat interface with session memory.
Wraps the LangGraph agent with PostgresSaver checkpointer
for persistent conversation history per session.
"""

from langchain.messages import HumanMessage
from langgraph.checkpoint.postgres import PostgresSaver  # type: ignore[import-untyped]
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from backend.agent.agent import _get_agent
from backend.config import settings

_pool: ConnectionPool | None = None
_checkpointer: PostgresSaver | None = None


def get_checkpointer() -> PostgresSaver:
    """
    Lazy-initialize PostgresSaver using a persistent connection pool.
    Creates LangGraph checkpoint tables on first call — idempotent.
    """
    global _pool, _checkpointer
    if _checkpointer is None:
        _pool = ConnectionPool(
            conninfo=settings.database_url,
            max_size=5,
            kwargs={
                "autocommit": True,
                "row_factory": dict_row,
            },
        )
        _checkpointer = PostgresSaver(_pool)
        _checkpointer.setup()
    return _checkpointer


def continue_chat(
    session_id: str,
    message: str,
) -> str:
    """
    Continue an existing chat session with a follow-up message.
    Reads conversation history from Postgres via PostgresSaver.
    Agent has full context of all previous turns in the session.

    Args:
        session_id: UUID identifying the conversation thread
        message:    User's follow-up question

    Returns:
        Agent's response as plain text with citations if applicable
    """
    config = {
        "configurable": {"thread_id": session_id},
        "recursion_limit": 15,
    }

    result = _get_agent(checkpointer=get_checkpointer()).invoke(
        {"messages": [HumanMessage(content=message)]},
        config=config,
    )

    messages = result.get("messages", [])
    for msg in reversed(messages):
        if hasattr(msg, "content") and not hasattr(msg, "tool_calls"):
            return str(msg.content)

    return "I was unable to generate a response. Please try again."
