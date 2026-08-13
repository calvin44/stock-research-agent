from dotenv import load_dotenv
from fastapi import FastAPI

from backend.api.routes import router
from backend.rag.registry import setup_table

load_dotenv()  # must run before setup_table reads DATABASE_URL

app = FastAPI(title="Stock Research Agent")

setup_table()  # creates documents table if not exists

app.include_router(router)
