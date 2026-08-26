"""
Retrieval pipeline: query → hybrid search → rerank → formatted citations.

Flow:
  1. Registry safety gate — only query fully indexed doc_ids
  2. Qdrant hybrid search (dense + BM25) with optional company filter
  3. FastEmbed cross-encoder reranking — top-k from candidates
  4. Format chunks with citations for LLM context
"""

from fastembed.rerank.cross_encoder import TextCrossEncoder
from langchain_core.documents import Document
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

# module-level singleton — None until first retrieval request
_reranker: TextCrossEncoder | None = None


def get_reranker() -> TextCrossEncoder:
    """
    Lazy-initialize the cross-encoder reranker.
    Downloads ~22MB ONNX model on first use, cached locally after.
    No PyTorch dependency — fastembed uses ONNX runtime.
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
) -> list[Document]:
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
        List of Documents ordered by reranker score, highest first.
        Empty list if no indexed documents exist.

    Raises:
        ValueError: if company is empty
    """
    if not company.strip():
        raise ValueError(
            "company cannot be empty. Retrieval must be scoped to a specific company ticker."
        )

    # ── Stage 1: Registry safety gate ───────────────────────────────
    # only query doc_ids that are fully indexed
    # prevents returning partial results from in-progress or failed indexing
    safe_doc_ids = get_indexed_doc_ids()
    if not safe_doc_ids:
        return []

    # ── Stage 2: Hybrid search ───────────────────────────────────────
    # Qdrant runs dense + BM25 simultaneously, fuses via RRF internally
    # filter scopes to safe doc_ids AND specific company
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
    # reranker reads query + chunk TOGETHER — more precise than embedding similarity
    # scores each (query, chunk_text) pair jointly
    # promotes chunks that directly answer the query over tangentially related ones
    reranker = get_reranker()
    chunk_texts = [doc.page_content for doc in candidates]
    scores = list(reranker.rerank(query, chunk_texts))

    # zip scores with Documents, sort descending, return top_k_final
    scored = sorted(
        zip(scores, candidates),
        key=lambda x: x[0],
        reverse=True,
    )
    return [doc for _, doc in scored[:top_k_final]]


def format_chunks_for_llm(chunks: list[Document]) -> str:
    """
    Format retrieved chunks as a context string with citations.

    Each chunk is prefixed with a citation identifying the source document,
    report type, fiscal year, and page number. The LLM uses these citations
    when attributing specific figures or claims in its response.

    Returns a not-found message if chunks is empty — the LLM should
    acknowledge this rather than hallucinating an answer.
    """
    if not chunks:
        return "No relevant information found in uploaded financial reports."

    sections = []
    for doc in chunks:
        meta = doc.metadata
        citation = (
            f"[{meta.get('company', 'Unknown')} "
            f"{meta.get('report_type', 'Report')} "
            f"{meta.get('fiscal_year', '')}, "
            f"page {meta.get('page', '?')}]"
        )
        sections.append(f"{citation}\n{doc.page_content}")

    return "\n\n".join(sections)
