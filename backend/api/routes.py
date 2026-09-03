"""
HTTP endpoints for stock research and chat.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.agent.agent import run_research
from backend.agent.chat import continue_chat
from backend.schemas.stock import StockAnalysis

router = APIRouter()


class ChatRequest(BaseModel):
    session_id: str
    message: str


class ChatResponse(BaseModel):
    session_id: str
    response: str


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/research/{ticker}", response_model=StockAnalysis)
def get_research(ticker: str):
    """One-shot structured research — returns full StockAnalysis JSON."""
    try:
        return run_research(ticker)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        print(f"Unexpected error for ticker {ticker}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Send a message in a research session.
    The agent maintains full conversation history via PostgresSaver.
    Generate a session_id (UUID) on the frontend and pass it with every message.
    """
    try:
        response = continue_chat(
            session_id=request.session_id,
            message=request.message,
        )
        return ChatResponse(
            session_id=request.session_id,
            response=response,
        )
    except Exception as e:
        print(f"Chat error for session {request.session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error") from e
