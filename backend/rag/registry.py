"""
Document Registry — source of truth for uploaded document status.
Tracks every document from upload through indexing to queryable state.
Postgres-backed: survives restarts, queryable via SQL.
"""

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

import psycopg
from psycopg.rows import namedtuple_row

from backend.config import settings


class IndexStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    INDEXED = "indexed"
    FAILED = "failed"


@dataclass
class DocumentRecord:
    doc_id: str
    filename: str
    company: str
    report_type: str
    fiscal_year: str
    status: IndexStatus = IndexStatus.PENDING
    total_chunks: int = 0
    content_hash: str = ""
    error: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


def _get_database_url() -> str:
    """Read DATABASE_URL from environment. Raises clearly if not set."""
    url = settings.database_url
    if not url:
        raise RuntimeError(
            "DATABASE_URL environment variable is not set. Add it to your .env file."
        )
    return url


def get_connection() -> psycopg.Connection:
    """
    Open a new Postgres connection with namedtuple row factory.
    Rows are accessible by column name (row.doc_id) not index (row[0]).
    Use as a context manager: `with get_connection() as conn`.
    """
    return psycopg.connect(_get_database_url(), row_factory=namedtuple_row)


def setup_table() -> None:
    """
    Create the documents table if it doesn't exist.
    Called once on startup — idempotent, safe to call repeatedly.
    """
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                doc_id       TEXT PRIMARY KEY,
                filename     TEXT NOT NULL,
                company      TEXT NOT NULL,
                report_type  TEXT NOT NULL,
                fiscal_year  TEXT NOT NULL,
                status       TEXT NOT NULL DEFAULT 'pending',
                total_chunks INTEGER NOT NULL DEFAULT 0,
                content_hash TEXT NOT NULL DEFAULT '',
                error        TEXT NOT NULL DEFAULT '',
                created_at   TEXT NOT NULL,
                updated_at   TEXT NOT NULL
            )
        """)
        conn.commit()


def _row_to_record(row: Any) -> DocumentRecord:
    """Convert a database row to a DocumentRecord."""
    return DocumentRecord(
        doc_id=row.doc_id,
        filename=row.filename,
        company=row.company,
        report_type=row.report_type,
        fiscal_year=row.fiscal_year,
        status=IndexStatus(row.status),
        total_chunks=row.total_chunks,
        content_hash=row.content_hash,
        error=row.error,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def create_record(
    filename: str,
    company: str,
    report_type: str,
    fiscal_year: str,
    content_hash: str = "",
) -> DocumentRecord:
    """Create a new document record with PENDING status."""
    doc_id = str(uuid.uuid4())
    now = datetime.now(UTC).isoformat()

    record = DocumentRecord(
        doc_id=doc_id,
        filename=filename,
        company=company,
        report_type=report_type,
        fiscal_year=fiscal_year,
        content_hash=content_hash,
        created_at=now,
        updated_at=now,
    )

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO documents
            (doc_id, filename, company, report_type, fiscal_year,
             status, total_chunks, content_hash, error, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                record.doc_id,
                record.filename,
                record.company,
                record.report_type,
                record.fiscal_year,
                record.status.value,
                record.total_chunks,
                record.content_hash,
                record.error,
                record.created_at,
                record.updated_at,
            ),
        )
        conn.commit()

    return record


def update_status(
    doc_id: str,
    status: IndexStatus,
    total_chunks: int = 0,
    error: str = "",
) -> None:
    """Update document status — called by indexer as processing progresses."""
    now = datetime.now(UTC).isoformat()

    with get_connection() as conn:
        conn.execute(
            """
            UPDATE documents
            SET status = %s,
                total_chunks = %s,
                error = %s,
                updated_at = %s
            WHERE doc_id = %s
            """,
            (status.value, total_chunks, error, now, doc_id),
        )
        conn.commit()


def get_indexed_doc_ids() -> list[str]:
    """Return doc_ids for fully indexed documents — used as retrieval safety gate."""
    with get_connection() as conn:
        rows = conn.execute("SELECT doc_id FROM documents WHERE status = 'indexed'").fetchall()
    return [row.doc_id for row in rows]  # type: ignore


def get_record(doc_id: str) -> DocumentRecord | None:
    """Fetch one document record by doc_id. Returns None if not found."""
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM documents WHERE doc_id = %s", (doc_id,)).fetchone()
    return _row_to_record(row) if row else None


def get_record_by_hash(content_hash: str) -> DocumentRecord | None:
    """
    Check if a document with this content hash is already indexed.
    Used for deduplication — prevents re-indexing identical files.
    """
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT * FROM documents
            WHERE content_hash = %s AND status = 'indexed'
            """,
            (content_hash,),
        ).fetchone()
    return _row_to_record(row) if row else None


def get_all_records() -> list[DocumentRecord]:
    """Return all document records ordered by creation date, newest first."""
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM documents ORDER BY created_at DESC").fetchall()
    return [_row_to_record(row) for row in rows]
