from __future__ import annotations

from src.models.schemas import EvidenceItem, RAGOutput
from src.rag.retriever import HybridRetriever


async def run_rag(retriever: HybridRetriever, query: str, ticker: str) -> RAGOutput:
    rewritten, items = retriever.retrieve(query=query, ticker=ticker, limit=8)
    evidence = [EvidenceItem(**item) for item in items]
    return RAGOutput(evidence=evidence, rewritten_query=rewritten)
