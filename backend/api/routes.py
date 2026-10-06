"""
HTTP endpoints for stock research and chat.
"""

from fastapi import APIRouter, HTTPException
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel

from backend.agent.agent import run_research
from backend.agent.chat import continue_chat
from backend.schemas.stock import StockAnalysis
from backend.store.research_store import (
    claim_seed,
    get_analysis,
    get_analysis_updated_at,
    release_seed,
    save_analysis,
)

router = APIRouter()


class ChatRequest(BaseModel):
    session_id: str
    message: str
    ticker: str = ""


class ChatResponse(BaseModel):
    session_id: str
    response: str


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/research/{ticker}", response_model=StockAnalysis)
def get_research(ticker: str):
    """Return the stored analysis for a ticker, or 404 if none has been run yet."""
    analysis = get_analysis(ticker)
    if analysis is None:
        raise HTTPException(status_code=404, detail=f"No analysis stored for {ticker}")
    return analysis


@router.post("/research/{ticker}", response_model=StockAnalysis)
def run_and_store_research(ticker: str):
    """Run fresh research for a ticker, store it, and return it."""
    try:
        analysis = run_research(ticker)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        print(f"Unexpected error for ticker {ticker}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error") from e
    save_analysis(analysis)
    return analysis


class SeedRequest(BaseModel):
    session_id: str
    ticker: str
    message: str


class SeedResponse(BaseModel):
    sent: bool
    response: str = ""


UPDATE_MARKER = "[Analysis updated] "


@router.post("/chat/seed", response_model=SeedResponse)
def seed_chat(request: SeedRequest) -> SeedResponse:
    """
    Send the analysis seed to a chat session once per analysis version.
    Repeat calls with the same analysis are no-ops; a newer analysis re-seeds.
    """
    analysis_updated_at = get_analysis_updated_at(request.ticker)
    if analysis_updated_at is None:
        return SeedResponse(sent=False)

    claim = claim_seed(request.session_id, request.ticker, analysis_updated_at)
    if claim is None:
        return SeedResponse(sent=False)

    message = request.message if claim else UPDATE_MARKER + request.message
    try:
        response = continue_chat(
            session_id=request.session_id,
            message=message,
            ticker=request.ticker,
        )
    except Exception as e:
        release_seed(request.session_id)
        print(f"Seed error for session {request.session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error") from e
    return SeedResponse(sent=True, response=response)


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    try:
        response = continue_chat(
            session_id=request.session_id,
            message=request.message,
            ticker=request.ticker,
        )
        return ChatResponse(
            session_id=request.session_id,
            response=response,
        )
    except Exception as e:
        print(f"Chat error for session {request.session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get("/chat/history/{session_id}")
def get_chat_history(session_id: str):
    """Return message history for a session from PostgresSaver."""
    try:
        from backend.agent.chat import get_checkpointer

        checkpointer = get_checkpointer()
        config: RunnableConfig = {"configurable": {"thread_id": session_id}}
        state = checkpointer.get(config)
        if not state:
            return []
        messages = state.get("channel_values", {}).get("messages", [])
        result = []
        skip_next_ai = False

        for msg in messages:
            role = type(msg).__name__

            if role == "HumanMessage":
                content = msg.content
                # strip ticker prefix before showing to user
                if content.startswith("[Stock being discussed:"):
                    content = content.split("] ", 1)[-1]
                if content.startswith(UPDATE_MARKER):
                    content = content[len(UPDATE_MARKER) :]
                # skip seed messages (checked after prefix strips)
                if content.startswith("I've just completed"):
                    skip_next_ai = True
                    continue
                result.append({"role": "user", "content": content})
                skip_next_ai = False

            elif role == "AIMessage" and not getattr(msg, "tool_calls", None):
                if skip_next_ai:
                    skip_next_ai = False
                    continue
                result.append({"role": "assistant", "content": msg.content})

        return result
    except Exception:
        return []


@router.delete("/chat/history/{session_id}")
def delete_chat_history(session_id: str):
    """Delete checkpoint history for a session from Postgres."""
    try:
        import psycopg

        from backend.config import settings

        conn = psycopg.connect(settings.database_url)
        conn.autocommit = True
        conn.execute("DELETE FROM checkpoints WHERE thread_id = %s", (session_id,))
        conn.execute("DELETE FROM checkpoint_blobs WHERE thread_id = %s", (session_id,))
        conn.execute("DELETE FROM checkpoint_writes WHERE thread_id = %s", (session_id,))
        conn.execute("DELETE FROM chat_session_seeds WHERE session_id = %s", (session_id,))
        conn.close()
        return {"status": "deleted"}
    except Exception:
        return {"status": "error"}


@router.get("/price-history/{ticker}")
def get_price_history(ticker: str):
    """Return 30-day closing price history for charting."""
    import yfinance as yf

    try:
        hist = yf.Ticker(ticker).history(period="1mo")
        return [
            {"date": str(date.date()), "close": round(float(close), 2)}
            for date, close in zip(hist.index, hist["Close"])
        ]
    except Exception:
        return []
