import os

from dotenv import load_dotenv

load_dotenv()
os.environ["DATABASE_URL"] = "postgresql://postgres:postgres@localhost:5432/stock_research_test"
