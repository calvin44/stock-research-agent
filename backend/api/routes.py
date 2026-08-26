from fastapi import APIRouter, HTTPException

from backend.agent.agent import run_research
from backend.schemas.stock import StockAnalysis

router = APIRouter()


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/research/{ticker}", response_model=StockAnalysis)
def get_research(ticker: str):
    try:
        return run_research(ticker)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        print(f"Unexpected error for ticker {ticker}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error") from e
