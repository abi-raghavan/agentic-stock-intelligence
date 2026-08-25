import pytest


@pytest.mark.integration
@pytest.mark.asyncio
async def test_golden_path_report_generation():
    from qdrant_client import QdrantClient

    from src.agents.report import run_report_verify
    from src.models.schemas import ConfidenceLevel, EvidenceItem, ResearchOutput, RiskOutput
    from src.rag.retriever import HybridRetriever

    try:
        QdrantClient(url="http://localhost:6333", timeout=2).get_collections()
    except Exception:
        pytest.skip("Qdrant is not available on localhost:6333")

    retriever = HybridRetriever()
    count = retriever.load_sample_data("sample_data")
    assert count >= 5

    rewritten, items = retriever.retrieve(
        "Should I be worried about NVIDIA export restrictions over the next 30 days?",
        ticker="NVDA",
        limit=5,
    )
    assert "NVDA" in rewritten
    assert len(items) >= 3

    research = ResearchOutput(
        positive_signals=[],
        negative_signals=[],
        fundamental_score=8.5,
        earnings_trend="positive",
        trend="bullish",
        volatility="medium",
    )
    risk = RiskOutput(
        opportunity_score=8.0,
        risk_score=4.5,
        confidence=ConfidenceLevel.MEDIUM,
        key_risks=["Export restrictions"],
        key_opportunities=["AI demand"],
    )
    evidence = [
        EvidenceItem(
            doc_id=item["doc_id"],
            source=item["source"],
            source_type=item["source_type"],
            document_date=item.get("document_date"),
            snippet=item["snippet"],
            bm25_score=item.get("bm25_score"),
            vector_score=item.get("vector_score"),
            fused_score=item.get("fused_score"),
            citation_id=item["citation_id"],
        )
        for item in items
    ]
    report = await run_report_verify("NVDA", "worried?", research, risk, evidence, [])
    assert len(report.top_evidence) >= 3
    assert len(report.sources) >= 3
    assert report.risk_score > 0
