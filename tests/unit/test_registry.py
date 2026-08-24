"""Unit tests for the document registry."""

import os

import psycopg
import pytest

from backend.rag.registry import (
    IndexStatus,
    create_record,
    get_indexed_doc_ids,
    get_record,
    get_record_by_hash,
    setup_table,
    update_status,
)


@pytest.fixture(autouse=True)
def clean_documents_table():
    """
    Wipe the documents table before and after each test.
    Ensures tests are isolated and repeatable.
    Uses stock_research_test database (overridden in conftest.py).
    """
    assert os.getenv("DATABASE_URL"), "DATABASE_URL must be set to run registry tests"
    setup_table()

    conn = psycopg.connect(os.getenv("DATABASE_URL"))  # type: ignore
    conn.autocommit = True
    conn.execute("DELETE FROM documents")
    conn.close()

    yield

    conn = psycopg.connect(os.getenv("DATABASE_URL"))  # type: ignore
    conn.autocommit = True
    conn.execute("DELETE FROM documents")
    conn.close()


def test_create_record_sets_pending_status():
    record = create_record(
        filename="apple_10k.pdf",
        company="AAPL",
        report_type="10-K",
        fiscal_year="2023",
    )
    assert record.status == IndexStatus.PENDING
    assert record.doc_id is not None
    assert record.total_chunks == 0
    assert record.content_hash == ""
    assert record.error == ""


def test_create_record_stores_content_hash():
    record = create_record(
        filename="apple_10k.pdf",
        company="AAPL",
        report_type="10-K",
        fiscal_year="2023",
        content_hash="abc123hash",
    )
    fetched = get_record(record.doc_id)
    assert fetched is not None
    assert fetched.content_hash == "abc123hash"


def test_create_record_persists_to_db():
    record = create_record(
        filename="msft_10q.pdf",
        company="MSFT",
        report_type="10-Q",
        fiscal_year="2023",
    )
    fetched = get_record(record.doc_id)
    assert fetched is not None
    assert fetched.doc_id == record.doc_id
    assert fetched.company == "MSFT"
    assert fetched.fiscal_year == "2023"


def test_update_status_to_indexed():
    record = create_record(
        filename="goog_10k.pdf",
        company="GOOG",
        report_type="10-K",
        fiscal_year="2023",
    )
    update_status(record.doc_id, IndexStatus.INDEXED, total_chunks=142)

    fetched = get_record(record.doc_id)
    assert fetched is not None
    assert fetched.status == IndexStatus.INDEXED
    assert fetched.total_chunks == 142


def test_update_status_to_failed_stores_error():
    record = create_record(
        filename="bad_file.pdf",
        company="BAD",
        report_type="10-K",
        fiscal_year="2023",
    )
    update_status(record.doc_id, IndexStatus.FAILED, error="No extractable text found")

    fetched = get_record(record.doc_id)
    assert fetched is not None
    assert fetched.status == IndexStatus.FAILED
    assert fetched.error == "No extractable text found"


def test_get_indexed_doc_ids_returns_only_indexed():
    indexed = create_record(
        filename="indexed.pdf",
        company="AAPL",
        report_type="10-K",
        fiscal_year="2022",
    )
    pending = create_record(
        filename="pending.pdf",
        company="AAPL",
        report_type="10-Q",
        fiscal_year="2022",
    )
    update_status(indexed.doc_id, IndexStatus.INDEXED, total_chunks=50)

    safe_ids = get_indexed_doc_ids()
    assert indexed.doc_id in safe_ids
    assert pending.doc_id not in safe_ids


def test_get_record_returns_none_for_unknown_id():
    result = get_record("nonexistent-doc-id-12345")
    assert result is None


def test_get_record_by_hash_returns_indexed_record():
    """get_record_by_hash only returns records with status=indexed."""
    record = create_record(
        filename="apple_10k.pdf",
        company="AAPL",
        report_type="10-K",
        fiscal_year="2023",
        content_hash="unique_hash_abc123",
    )
    # not indexed yet — should not be found
    result = get_record_by_hash("unique_hash_abc123")
    assert result is None

    # mark as indexed
    update_status(record.doc_id, IndexStatus.INDEXED, total_chunks=100)

    # now should be found
    result = get_record_by_hash("unique_hash_abc123")
    assert result is not None
    assert result.doc_id == record.doc_id
    assert result.content_hash == "unique_hash_abc123"


def test_get_record_by_hash_returns_none_for_unknown_hash():
    """get_record_by_hash returns None when hash doesn't exist."""
    result = get_record_by_hash("nonexistent_hash_xyz")
    assert result is None
