from dotenv import load_dotenv

load_dotenv()
from fastapi import FastAPI

from backend.api.routes import router

app = FastAPI(title="Stock Research Agent")
app.include_router(router)
