import pytest

from src.agents.report import run_report_verify
from src.models.schemas import EvidenceItem, ResearchOutput, RiskOutput, ConfidenceLevel


@pytest.mark.asyncio
async def test_report_generation_has_citations():
    research = ResearchOutput(
        positive_signals=[],
        negative_signals=[],
        fundamental_score=8.0,
        earnings_trend="positive",
        trend="bullish",
        volatility="medium",
    )
    risk = RiskOutput(
        opportunity_score=8.0,
        risk_score=4.0,
        confidence=ConfidenceLevel.MEDIUM,
        key_risks=["Regulatory risk"],
        key_opportunities=["AI demand"],
    )
    evidence = [
        EvidenceItem(
            doc_id="doc1",
            source="Sample",
            source_type="news",
            document_date="2025-07-01",
            snippet="Export restrictions may affect China sales.",
            citation_id="E1",
            fused_score=0.02,
        )
    ]
    report = await run_report_verify("NVDA", "worried?", research, risk, evidence, [])
    assert len(report.top_evidence) >= 1
    assert len(report.sources) >= 1
    assert report.opportunity_score == 8.0
