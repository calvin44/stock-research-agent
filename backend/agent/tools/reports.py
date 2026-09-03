"""
RAG tool for the LangGraph agent.
Searches indexed financial report PDFs for specific information.
The agent calls this when the user asks about data from uploaded reports.
"""

from langchain_core.tools import tool

from backend.rag.registry import IndexStatus, get_all_records
from backend.rag.retriever import format_chunks_for_llm, retrieve_from_reports


@tool
def search_financial_reports(query: str, company: str) -> str:
    """
    Search uploaded financial report PDFs for specific information.

    Use this tool when the user asks about:
    - Specific financial figures not available via web search
    - Management commentary and forward guidance
    - Risk factors and legal disclosures
    - Historical comparisons across multiple reporting periods

    Do NOT use this tool for current stock price or recent news.

    IMPORTANT: If this tool returns a NO REPORTS AVAILABLE message,
    do NOT call it again. Proceed immediately with the final analysis.

    Args:
        query:   Specific information to search for in the reports
        company: Company ticker (e.g. "AAPL", "UNTR")

    Returns:
        Relevant excerpts with citations, or a NO REPORTS AVAILABLE message.
    """
    # check if any indexed reports exist for this company
    company_records = [
        r
        for r in get_all_records()
        if r.company.upper() == company.upper() and r.status == IndexStatus.INDEXED
    ]

    if not company_records:
        return (
            f"NO REPORTS AVAILABLE: No financial reports have been uploaded "
            f"for {company}. DO NOT call this tool again for {company}. "
            f"Proceed immediately to generate the final analysis using "
            f"data from the other tools already called."
        )

    chunks = retrieve_from_reports(
        query=query,
        company=company,
    )
    return format_chunks_for_llm(chunks)
