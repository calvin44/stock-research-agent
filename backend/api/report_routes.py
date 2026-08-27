"""
Report management endpoints.
Handles PDF upload, indexing status polling, and document listing.
"""

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from backend.rag.indexer import index_document
from backend.rag.registry import (
    DocumentRecord,
    IndexStatus,
    get_all_records,
    get_record,
)

router = APIRouter(prefix="/reports", tags=["reports"])


class UploadResponse(BaseModel):
    doc_id: str
    filename: str
    status: str
    message: str


class DocumentResponse(BaseModel):
    doc_id: str
    filename: str
    company: str
    report_type: str
    fiscal_year: str
    status: str
    total_chunks: int
    error: str
    created_at: str
    updated_at: str


def _to_response(record: DocumentRecord) -> DocumentResponse:
    """Convert a DocumentRecord to a DocumentResponse."""
    return DocumentResponse(
        doc_id=record.doc_id,
        filename=record.filename,
        company=record.company,
        report_type=record.report_type,
        fiscal_year=record.fiscal_year,
        status=record.status,
        total_chunks=record.total_chunks,
        error=record.error,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


@router.post("/upload", response_model=UploadResponse)
async def upload_report(
    file: UploadFile = File(...),
    company: str = Form(...),
    report_type: str = Form(...),
    fiscal_year: str = Form(...),
) -> UploadResponse:
    """
    Upload a financial report PDF for indexing.

    Returns immediately with doc_id and status=processing.
    Poll GET /reports/{doc_id}/status to check when indexing completes.

    Args:
        file:        PDF file to index
        company:     Company ticker (e.g. "UNTR", "AAPL")
        report_type: Type of report (e.g. "10-K", "10-Q", "Business Progress Report")
        fiscal_year: Fiscal year or period (e.g. "2023", "Q1 2026")
    """
    # validate file type
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported.",
        )

    # validate form fields
    if not company.strip():
        raise HTTPException(status_code=400, detail="company is required.")
    if not report_type.strip():
        raise HTTPException(status_code=400, detail="report_type is required.")
    if not fiscal_year.strip():
        raise HTTPException(status_code=400, detail="fiscal_year is required.")

    file_bytes = await file.read()

    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    # kick off indexing in background — returns immediately
    # user polls /reports/{doc_id}/status to track progress
    doc_id = await index_document(
        file_bytes=file_bytes,
        filename=file.filename,
        company=company.strip(),
        report_type=report_type.strip(),
        fiscal_year=fiscal_year.strip(),
    )

    return UploadResponse(
        doc_id=doc_id,
        filename=file.filename,
        status=IndexStatus.PROCESSING,
        message="Document received. Indexing in progress — poll /reports/{doc_id}/status to track.",
    )


@router.get("/{doc_id}/status", response_model=DocumentResponse)
def get_status(doc_id: str) -> DocumentResponse:
    """
    Get the current indexing status of an uploaded document.
    Poll this endpoint after upload until status=indexed.

    Status values:
      pending    — received, not yet started
      processing — indexing in progress
      indexed    — ready to query
      failed     — indexing failed, see error field
    """
    record = get_record(doc_id)
    if record is None:
        raise HTTPException(
            status_code=404,
            detail=f"Document {doc_id} not found.",
        )
    return _to_response(record)


@router.get("/", response_model=list[DocumentResponse])
def list_reports() -> list[DocumentResponse]:
    """
    List all uploaded documents and their indexing status.
    Returns newest first.
    """
    return [_to_response(r) for r in get_all_records()]
