import os

# override DATABASE_URL before Settings() is instantiated
# pydantic-settings reads os.environ first, so this takes precedence over .env
os.environ["DATABASE_URL"] = "postgresql://postgres:postgres@localhost:5432/stock_research_test"
