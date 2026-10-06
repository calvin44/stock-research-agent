from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.agent.chat import get_checkpointer
from backend.api.report_routes import router as reports_router
from backend.api.routes import router
from backend.config import settings  # noqa: F401
from backend.rag.indexer import get_vectorstore
from backend.rag.registry import setup_table
from backend.rag.retriever import get_reranker
from backend.store.research_store import setup_tables as setup_research_tables


@asynccontextmanager
async def lifespan(_: FastAPI):
    setup_table()
    setup_research_tables()
    get_vectorstore()
    get_reranker()
    get_checkpointer()
    yield


app = FastAPI(title="Stock Research Agent", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(reports_router)
