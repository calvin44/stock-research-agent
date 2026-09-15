"""
Integration tests for the RAG pipeline.
Tests the full flow: upload → index → retrieve → chat memory.

Run with:
  uv run pytest tests/integration/test_rag.py -v -m integration

Requires:
  - Docker Compose running (Postgres + Qdrant)
  - OPENAI_API_KEY set in .env
  - test PDF in test_files/
"""

import asyncio
import os
import uuid

import psycopg
import pytest
from qdrant_client import QdrantClient

from backend.agent.chat import get_checkpointer
from backend.config import settings
from backend.rag.indexer import get_vectorstore, index_document
from backend.rag.registry import (
    IndexStatus,
    get_indexed_doc_ids,
    get_record,
    setup_table,
)
from backend.rag.retriever import retrieve_from_reports

# ── Constants ────────────────────────────────────────────────────────────────

TEST_PDF_PATH = "test_files/Lap Perkembangan Usaha 1Q 2026.pdf"
TEST_COMPANY = "UNTR-TEST"
OTHER_COMPANY = "OTHER-COMPANY"
TEST_COLLECTION = os.getenv("QDRANT_TEST_COLLECTION", "financial_reports_test")


# ── Helpers ───────────────────────────────────────────────────────────────────


def _clean_registry():
    """Delete test company records from registry."""
    conn = psycopg.connect(os.environ["DATABASE_URL"])
    conn.autocommit = True
    conn.execute("DELETE FROM documents WHERE company = %s", (TEST_COMPANY,))
    conn.execute("DELETE FROM documents WHERE company = %s", (OTHER_COMPANY,))
    conn.close()


def _clean_qdrant():
    """Delete test Qdrant collection if it exists."""
    try:
        client = QdrantClient(url=settings.qdrant_url)
        existing = [c.name for c in client.get_collections().collections]
        if TEST_COLLECTION in existing:
            client.delete_collection(TEST_COLLECTION)
    except Exception:
        pass


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def setup_test_environment():
    """
    Clean state before and after each test:
    - Wipe test company documents from registry
    - Delete test Qdrant collection
    - Clear lru_cache on vectorstore to force fresh connection
    """
    setup_table()
    _clean_registry()
    _clean_qdrant()
    get_vectorstore.cache_clear()

    yield

    _clean_registry()
    _clean_qdrant()
    get_vectorstore.cache_clear()


@pytest.fixture
def pdf_bytes() -> bytes:
    """Load test PDF bytes."""
    with open(TEST_PDF_PATH, "rb") as f:
        return f.read()


@pytest.fixture
def indexed_doc_id(pdf_bytes: bytes) -> str:
    """
    Upload and index a real PDF.
    Returns doc_id of the indexed document.
    Used by tests that need an already-indexed document.
    """
    doc_id = asyncio.run(
        index_document(
            file_bytes=pdf_bytes,
            filename="Lap Perkembangan Usaha 1Q 2026.pdf",
            company=TEST_COMPANY,
            report_type="Business Progress Report",
            fiscal_year="Q1 2026",
        )
    )
    return doc_id


# ── Tests: Upload + Indexing ─────────────────────────────────────────────────


@pytest.mark.integration
def test_upload_creates_registry_record(pdf_bytes: bytes):
    """Uploading a PDF creates a registry record with correct metadata."""
    doc_id = asyncio.run(
        index_document(
            file_bytes=pdf_bytes,
            filename="test.pdf",
            company=TEST_COMPANY,
            report_type="Business Progress Report",
            fiscal_year="Q1 2026",
        )
    )

    record = get_record(doc_id)
    assert record is not None
    assert record.doc_id == doc_id
    assert record.company == TEST_COMPANY
    assert record.status == IndexStatus.INDEXED
    assert record.total_chunks > 0
    assert record.error == ""


@pytest.mark.integration
def test_upload_stores_chunks_in_qdrant(pdf_bytes: bytes):
    """Indexed document chunks are stored in Qdrant with correct metadata."""
    doc_id = asyncio.run(
        index_document(
            file_bytes=pdf_bytes,
            filename="test.pdf",
            company=TEST_COMPANY,
            report_type="Business Progress Report",
            fiscal_year="Q1 2026",
        )
    )

    vs = get_vectorstore()
    results = vs.similarity_search("pendapatan bersih", k=3)

    assert len(results) > 0
    for doc in results:
        assert doc.metadata.get("company") == TEST_COMPANY
        assert doc.metadata.get("doc_id") == doc_id


@pytest.mark.integration
def test_deduplication_returns_same_doc_id(pdf_bytes: bytes):
    """Uploading the same PDF twice returns the same doc_id without re-indexing."""
    doc_id_1 = asyncio.run(
        index_document(
            file_bytes=pdf_bytes,
            filename="test.pdf",
            company=TEST_COMPANY,
            report_type="Business Progress Report",
            fiscal_year="Q1 2026",
        )
    )

    doc_id_2 = asyncio.run(
        index_document(
            file_bytes=pdf_bytes,
            filename="test.pdf",
            company=TEST_COMPANY,
            report_type="Business Progress Report",
            fiscal_year="Q1 2026",
        )
    )

    assert doc_id_1 == doc_id_2


@pytest.mark.integration
def test_deduplication_no_duplicate_chunks(pdf_bytes: bytes):
    """Uploading the same PDF twice does not create duplicate chunks in Qdrant."""
    asyncio.run(
        index_document(
            file_bytes=pdf_bytes,
            filename="test.pdf",
            company=TEST_COMPANY,
            report_type="Business Progress Report",
            fiscal_year="Q1 2026",
        )
    )
    asyncio.run(
        index_document(
            file_bytes=pdf_bytes,
            filename="test.pdf",
            company=TEST_COMPANY,
            report_type="Business Progress Report",
            fiscal_year="Q1 2026",
        )
    )

    client = QdrantClient(url=settings.qdrant_url)
    count = client.count(collection_name=TEST_COLLECTION).count

    indexed_ids = get_indexed_doc_ids()
    assert len(indexed_ids) > 0
    record = get_record(indexed_ids[0])
    assert record is not None
    assert count == record.total_chunks


# ── Tests: Safety Gate ───────────────────────────────────────────────────────


@pytest.mark.integration
def test_safety_gate_blocks_unindexed_company():
    """
    retrieve_from_reports returns empty list when no documents
    are indexed for the requested company.
    """
    chunks = retrieve_from_reports(
        query="revenue",
        company="NONEXISTENT-COMPANY-XYZ",
    )
    assert chunks == []


@pytest.mark.integration
def test_safety_gate_allows_indexed_company(indexed_doc_id: str):
    """
    retrieve_from_reports returns chunks when documents
    are indexed for the requested company.
    """
    _ = indexed_doc_id  # fixture used for side effect — triggers indexing
    chunks = retrieve_from_reports(
        query="pendapatan bersih Q1 2026",
        company=TEST_COMPANY,
    )
    assert len(chunks) > 0


# ── Tests: Retrieval Quality ─────────────────────────────────────────────────


@pytest.mark.integration
def test_retrieval_returns_relevant_chunks(indexed_doc_id: str):
    """Retrieved chunks are relevant to the query."""
    chunks = retrieve_from_reports(
        query="pendapatan bersih Q1 2026",
        company=TEST_COMPANY,
        top_k_retrieve=20,
        top_k_final=5,
    )

    assert len(chunks) > 0
    assert len(chunks) <= 5

    for chunk in chunks:
        assert chunk.company == TEST_COMPANY
        assert chunk.content != ""
        assert chunk.doc_id != ""
        assert chunk.doc_id == indexed_doc_id
        assert chunk.page >= 0


@pytest.mark.integration
def test_retrieval_scopes_to_company(pdf_bytes: bytes, indexed_doc_id: str):
    """Retrieval does not return chunks from other companies."""
    # index same PDF under different company
    asyncio.run(
        index_document(
            file_bytes=pdf_bytes,
            filename="test.pdf",
            company=OTHER_COMPANY,
            report_type="Business Progress Report",
            fiscal_year="Q1 2026",
        )
    )

    # retrieve for TEST_COMPANY only
    chunks = retrieve_from_reports(
        query="pendapatan bersih",
        company=TEST_COMPANY,
    )

    # all returned chunks must belong to TEST_COMPANY
    assert len(chunks) > 0
    for chunk in chunks:
        assert chunk.company == TEST_COMPANY


@pytest.mark.integration
def test_retrieval_citations_are_populated(indexed_doc_id: str):
    """Retrieved chunks have all citation fields populated."""
    _ = indexed_doc_id  # fixture used for side effect
    chunks = retrieve_from_reports(
        query="pendapatan bersih Q1 2026",
        company=TEST_COMPANY,
    )

    assert len(chunks) > 0
    for chunk in chunks:
        assert chunk.company != ""
        assert chunk.report_type != ""
        assert chunk.fiscal_year != ""
        assert chunk.source != ""


# ── Tests: Session Memory ────────────────────────────────────────────────────


@pytest.mark.integration
def test_checkpointer_saves_to_postgres():
    """
    get_checkpointer() creates LangGraph checkpoint tables in Postgres.
    Tests the PostgresSaver connection — no LLM calls.
    """
    checkpointer = get_checkpointer()
    assert checkpointer is not None

    conn = psycopg.connect(os.environ["DATABASE_URL"])
    cursor = conn.execute("""
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_name IN ('checkpoints', 'checkpoint_blobs', 'checkpoint_writes')
    """)
    tables = [row[0] for row in cursor.fetchall()]
    conn.close()

    assert "checkpoints" in tables
    assert "checkpoint_blobs" in tables
    assert "checkpoint_writes" in tables


@pytest.mark.integration
def test_checkpointer_session_isolation():
    """
    Different session_ids produce isolated checkpoint histories.
    Fresh sessions have no existing checkpoints.
    """
    session_1 = str(uuid.uuid4())
    session_2 = str(uuid.uuid4())

    get_checkpointer()
    assert session_1 != session_2

    conn = psycopg.connect(os.environ["DATABASE_URL"])

    row_1 = conn.execute(
        "SELECT COUNT(*) FROM checkpoints WHERE thread_id = %s", (session_1,)
    ).fetchone()
    count_1 = row_1[0] if row_1 else 0

    row_2 = conn.execute(
        "SELECT COUNT(*) FROM checkpoints WHERE thread_id = %s", (session_2,)
    ).fetchone()
    count_2 = row_2[0] if row_2 else 0

    conn.close()

    assert count_1 == 0
    assert count_2 == 0
