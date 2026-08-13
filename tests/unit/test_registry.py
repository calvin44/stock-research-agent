"""Unit tests for the document registry."""

import os

import pytest

from backend.rag.registry import (
    IndexStatus,
    create_record,
    get_indexed_doc_ids,
    get_record,
    setup_table,
    update_status,
)


@pytest.fixture(autouse=True)
def setup():
    """
    Use a temporary SQLite-compatible test DB via psycopg.
    Since we're testing against real Postgres, DATABASE_URL must be set.
    """
    assert os.getenv("DATABASE_URL"), "DATABASE_URL must be set to run registry tests"
    setup_table()


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
    assert record.error == ""


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
    # create one indexed and one pending
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
    # pending stays as PENDING

    safe_ids = get_indexed_doc_ids()
    assert indexed.doc_id in safe_ids
    assert pending.doc_id not in safe_ids


def test_get_record_returns_none_for_unknown_id():
    result = get_record("nonexistent-doc-id-12345")
    assert result is None
