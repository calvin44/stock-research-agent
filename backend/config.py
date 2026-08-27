# backend/config.py
import os

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    openai_api_key: str
    tavily_api_key: str
    qdrant_url: str = "http://localhost:6333"
    database_url: str
    langchain_tracing_v2: bool = False
    langchain_api_key: str = ""
    langchain_project: str = "stock-research-agent"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()  # type: ignore[call-arg]

# explicitly populate os.environ so libraries that read from it directly
# (OpenAI, LangChain, Tavily) can find the keys
os.environ["OPENAI_API_KEY"] = settings.openai_api_key
os.environ["TAVILY_API_KEY"] = settings.tavily_api_key
os.environ["QDRANT_URL"] = settings.qdrant_url
os.environ["DATABASE_URL"] = settings.database_url
if settings.langchain_api_key:
    os.environ["LANGCHAIN_API_KEY"] = settings.langchain_api_key
    os.environ["LANGCHAIN_TRACING_V2"] = str(settings.langchain_tracing_v2).lower()
    os.environ["LANGCHAIN_PROJECT"] = settings.langchain_project
