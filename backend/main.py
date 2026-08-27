from backend.config import settings  # noqa: F401, I001
from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.api.report_routes import router as reports_router
from backend.api.routes import router
from backend.rag.indexer import get_vectorstore
from backend.rag.registry import setup_table
from backend.rag.retrieval import get_reranker


@asynccontextmanager
async def lifespan(_: FastAPI):
    """
    Pre-warm all resources before accepting requests.
    - setup_table: creates Postgres documents table if not exists
    - get_vectorstore: establishes Qdrant connection + collection
    - get_reranker: loads reranker model from disk into RAM
    """
    setup_table()
    get_vectorstore()
    get_reranker()
    yield


app = FastAPI(title="Stock Research Agent", lifespan=lifespan)

app.include_router(router)
app.include_router(reports_router)
