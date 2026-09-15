import os

# override DATABASE_URL to test database before any imports
os.environ["DATABASE_URL"] = "postgresql://postgres:postgres@localhost:5432/stock_research_test"

# override Qdrant collection for tests — prevents polluting production data
os.environ["QDRANT_TEST_COLLECTION"] = "financial_reports_test"
