"""
Indexing pipeline: PDF bytes → chunks → Qdrant (dense + sparse).

Flow:
  1. PyPDF extracts text per page
  2. RecursiveCharacterTextSplitter chunks the text
  3. OpenAI dense embeddings + FastEmbed BM25 sparse embeddings
  4. Both stored atomically in Qdrant per chunk
  5. Registry updated: PROCESSING → INDEXED (or FAILED)
"""

import hashlib
import os
import tempfile

from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_qdrant import FastEmbedSparse, QdrantVectorStore, RetrievalMode
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader
from qdrant_client import QdrantClient
from qdrant_client.http.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    SparseIndexParams,
    SparseVectorParams,
    VectorParams,
)

from backend.config import settings
from backend.rag.registry import IndexStatus, create_record, get_record_by_hash, update_status

COLLECTION_NAME = "financial_reports"
CHUNK_SIZE = 800
CHUNK_OVERLAP = 100

# module-level singletons — initialized once, reused across calls
_qdrant_client: QdrantClient | None = None
_vectorstore: QdrantVectorStore | None = None


def _get_qdrant_url() -> str:
    """Read QDRANT_URL from environment. Raises clearly if not set."""
    url = settings.qdrant_url
    if not url:
        raise RuntimeError("QDRANT_URL environment variable is not set. Add it to your .env file.")
    return url


def get_vectorstore() -> QdrantVectorStore:
    """
    Lazy-initialize Qdrant client and vectorstore.
    Creates the financial_reports collection if it doesn't exist.
    Called on first use — safe to call repeatedly.
    """
    global _qdrant_client, _vectorstore

    if _vectorstore is not None:
        return _vectorstore

    _qdrant_client = QdrantClient(url=_get_qdrant_url())

    # create collection if it doesn't exist
    existing = [c.name for c in _qdrant_client.get_collections().collections]
    if COLLECTION_NAME not in existing:
        _qdrant_client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config={
                # dense vector — 1536 dims matches text-embedding-3-small
                "dense": VectorParams(size=1536, distance=Distance.COSINE)
            },
            sparse_vectors_config={
                # sparse vector — BM25 keyword index
                "sparse": SparseVectorParams(index=SparseIndexParams(on_disk=False))
            },
        )

    _vectorstore = QdrantVectorStore(
        client=_qdrant_client,
        collection_name=COLLECTION_NAME,
        embedding=OpenAIEmbeddings(model="text-embedding-3-small"),
        sparse_embedding=FastEmbedSparse(model_name="Qdrant/bm25"),
        retrieval_mode=RetrievalMode.HYBRID,
        vector_name="dense",
        sparse_vector_name="sparse",
    )

    return _vectorstore


async def index_document(
    file_bytes: bytes,
    filename: str,
    company: str,
    report_type: str,
    fiscal_year: str,
) -> str:
    # FIRST THING — compute hash from raw file bytes
    content_hash = hashlib.sha256(file_bytes).hexdigest()

    # check if identical file already indexed
    existing = get_record_by_hash(content_hash)
    if existing:
        # verify chunks actually exist in Qdrant
        # if collection was deleted or chunks are missing - re-index
        vs = get_vectorstore()
        results = vs.similarity_search(
            "test",
            k=1,
            filter=Filter(
                must=[
                    FieldCondition(key="metadata.doc_id", match=MatchValue(value=existing.doc_id))
                ]
            ),
        )
        if results:
            return existing.doc_id  # chunks exist - true duplicate, skip

    # only reaches here if file is new
    record = create_record(
        filename=filename,
        company=company,
        report_type=report_type,
        fiscal_year=fiscal_year,
        content_hash=content_hash,  # ← stored in registry
    )
    doc_id = record.doc_id

    # immediately mark as processing so frontend knows work has started
    update_status(doc_id, IndexStatus.PROCESSING)

    try:
        # ── Stage 1: Load ────────────────────────────────────────────
        # write bytes to temp file — pypdf needs a file path or file object
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name

        try:
            reader = PdfReader(tmp_path)
            pages = [
                Document(
                    page_content=page.extract_text() or "",
                    metadata={
                        "doc_id": doc_id,
                        "source": filename,
                        "company": company,
                        "report_type": report_type,
                        "fiscal_year": fiscal_year,
                        "page": i,
                    },
                )
                for i, page in enumerate(reader.pages)
                if page.extract_text()  # skip empty or image-only pages
            ]
        finally:
            # always clean up temp file even if extraction fails
            os.unlink(tmp_path)

        if not pages:
            update_status(
                doc_id,
                IndexStatus.FAILED,
                error="No extractable text found. PDF may be scanned or image-only.",
            )
            return doc_id

        # ── Stage 2: Chunk ───────────────────────────────────────────
        # token-based splitting — accurate for embedding model limits
        # 800 tokens preserves paragraph-level reasoning for financial text
        # 100 token overlap catches context split across chunk boundaries
        splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
            encoding_name="cl100k_base",
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
        )
        chunks = splitter.split_documents(pages)

        if not chunks:
            update_status(
                doc_id,
                IndexStatus.FAILED,
                error="Document produced no chunks after splitting.",
            )
            return doc_id

        # ── Stage 3: Embed + Store ───────────────────────────────────
        # add_documents handles both dense and sparse embeddings atomically:
        # - calls OpenAI API for dense vectors (billed per token)
        # - calls FastEmbed BM25 locally for sparse vectors (free)
        # - stores both + payload (text + metadata) in Qdrant
        vectorstore = get_vectorstore()
        vectorstore.add_documents(chunks)

        # ── Stage 4: Update Registry ─────────────────────────────────
        update_status(
            doc_id,
            IndexStatus.INDEXED,
            total_chunks=len(chunks),
        )

    except Exception as e:
        update_status(
            doc_id,
            IndexStatus.FAILED,
            error=str(e),
        )

    return doc_id
