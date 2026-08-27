"""
Shared type definitions for the RAG pipeline.
Defines typed wrappers around loosely-typed library boundaries.
"""

from dataclasses import dataclass


@dataclass
class ReportChunk:
    """
    Typed representation of a retrieved financial report chunk.
    Flattens LangChain's Document + nested metadata into clean attributes.
    Constructed at the retrieval boundary — all downstream code uses this type.
    """

    content: str
    doc_id: str
    company: str
    report_type: str
    fiscal_year: str
    page: int
    source: str
