"""
Retrieval pipeline: query → hybrid search → rerank → formatted citations.

Flow:
  1. Registry safety gate — only query fully indexed doc_ids
  2. Qdrant hybrid search (dense + BM25) with company filter
  3. FastEmbed cross-encoder reranking — top-k from candidates
  4. Format chunks with citations for LLM context
"""

from fastembed.rerank.cross_encoder import TextCrossEncoder
from langsmith import traceable
from qdrant_client.http.models import (
    Condition,
    FieldCondition,
    Filter,
    MatchAny,
    MatchValue,
)

from backend.rag.indexer import get_vectorstore
from backend.rag.registry import get_indexed_doc_ids
from backend.rag.types import ReportChunk

# module-level singleton — initialized once on first retrieval request
# model already baked into Docker image — loads from disk, no download
_reranker: TextCrossEncoder | None = None


def get_reranker() -> TextCrossEncoder:
    """
    Lazy-initialize the cross-encoder reranker.
    Model is baked into the Docker image — loads from disk into RAM.
    No download at runtime.
    """
    global _reranker
    if _reranker is None:
        _reranker = TextCrossEncoder(model_name="Xenova/ms-marco-MiniLM-L-6-v2")
    return _reranker


def _build_filter(
    safe_doc_ids: list[str],
    company: str,
) -> Filter:
    """
    Build Qdrant metadata filter scoped to a specific company.
    Always restricts to fully indexed doc_ids (safety gate).
    Company is required — retrieval is always single-company per session.
    """
    conditions: list[Condition] = [
        FieldCondition(
            key="metadata.doc_id",
            match=MatchAny(any=safe_doc_ids),
        ),
        FieldCondition(
            key="metadata.company",
            match=MatchValue(value=company),
        ),
    ]

    return Filter(must=conditions)


@traceable(name="rag_retrieval")
def retrieve_from_reports(
    query: str,
    company: str,
    top_k_retrieve: int = 20,
    top_k_final: int = 5,
) -> list[ReportChunk]:
    """
    Retrieve relevant chunks from indexed financial reports.

    Scoped to a specific company — one company per session by design.
    Applies registry safety gate — only queries fully indexed documents.
    Uses hybrid search (dense + BM25) with RRF fusion via Qdrant.
    Reranks top candidates with a cross-encoder for precision.

    Args:
        query:          The search query — user question or rewritten query
        company:        Company ticker to scope search (e.g. "UNTR") — required
        top_k_retrieve: Candidates to retrieve before reranking (wide net)
        top_k_final:    Final chunks to return after reranking (narrow)

    Returns:
        List of ReportChunks ordered by reranker score, highest first.
        Empty list if no indexed documents exist.

    Raises:
        ValueError: if company is empty
    """
    if not company.strip():
        raise ValueError(
            "company cannot be empty. Retrieval must be scoped to a specific company ticker."
        )

    # ── Stage 1: Registry safety gate ───────────────────────────────
    safe_doc_ids = get_indexed_doc_ids()
    if not safe_doc_ids:
        return []

    # ── Stage 2: Hybrid search ───────────────────────────────────────
    vectorstore = get_vectorstore()
    qdrant_filter = _build_filter(safe_doc_ids, company)

    candidates = vectorstore.similarity_search(
        query,
        k=top_k_retrieve,
        filter=qdrant_filter,
    )

    if not candidates:
        return []

    # ── Stage 3: Cross-encoder reranking ────────────────────────────
    reranker = get_reranker()
    chunk_texts = [doc.page_content for doc in candidates]
    scores = list(reranker.rerank(query, chunk_texts))

    scored = sorted(
        zip(scores, candidates),
        key=lambda x: x[0],
        reverse=True,
    )

    # ── Stage 4: Convert to typed ReportChunk ───────────────────────
    # type: ignore here is intentional — LangChain types metadata as dict[str, Any]
    # we know the shape because we wrote it in indexer.py
    # single conversion point — all downstream code uses typed ReportChunk
    return [
        ReportChunk(
            content=doc.page_content,
            doc_id=doc.metadata["doc_id"],
            company=doc.metadata["company"],
            report_type=doc.metadata["report_type"],
            fiscal_year=doc.metadata["fiscal_year"],
            page=doc.metadata["page"],
            source=doc.metadata["source"],
        )
        for _, doc in scored[:top_k_final]
    ]


def format_chunks_for_llm(chunks: list[ReportChunk]) -> str:
    """
    Format retrieved chunks as a context string with citations.
    Each chunk is prefixed with a citation identifying source, type, year, page.
    Returns a not-found message if chunks is empty.
    """
    if not chunks:
        return "No relevant information found in uploaded financial reports."

    sections = []
    for chunk in chunks:
        citation = f"[{chunk.company} {chunk.report_type} {chunk.fiscal_year}, page {chunk.page}]"
        sections.append(f"{citation}\n{chunk.content}")

    return "\n\n".join(sections)
