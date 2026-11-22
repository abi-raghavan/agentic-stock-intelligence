from src.models.schemas import EvidenceItem, PlannerOutput, RAGOutput
from src.rag.retriever import HybridRetriever


def _compose_rag_query(query: str, planner: PlannerOutput | None) -> str:
    if not planner:
        return query
    parts = [planner.intent or query]
    parts.extend(planner.focus_queries[:2])
    parts.extend(planner.tasks[:2])
    # Deduplicate while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for part in parts:
        key = part.strip().lower()
        if key and key not in seen:
            seen.add(key)
            unique.append(part.strip())
    return " | ".join(unique) if unique else query


async def run_rag(
    retriever: HybridRetriever,
    query: str,
    ticker: str,
    planner: PlannerOutput | None = None,
) -> RAGOutput:
    composed = _compose_rag_query(query, planner)
    rewritten, items = retriever.retrieve(query=composed, ticker=ticker, limit=8)
    evidence = [EvidenceItem(**item) for item in items]
    return RAGOutput(evidence=evidence, rewritten_query=rewritten)
