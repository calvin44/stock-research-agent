FROM python:3.13-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
RUN uv run python -c "from fastembed.rerank.cross_encoder import TextCrossEncoder; TextCrossEncoder(model_name='Xenova/ms-marco-MiniLM-L-6-v2')"
COPY backend/ ./backend/
EXPOSE 8000
CMD ["uv", "run", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]