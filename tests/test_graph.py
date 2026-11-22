import pytest

from src.graph.workflow import StockIntelligenceGraph
from src.models.schemas import ResearchOutput
from src.rag.retriever import HybridRetriever


async def _fake_research(ticker, display_name=None, news_query=None, planner=None):
    research = ResearchOutput(
        positive_signals=[],
        negative_signals=[],
        fundamental_score=8.0,
        earnings_trend="positive",
        trend="bullish",
        volatility="medium",
    )
    return research, [{"date": "2025-01-01", "close": 100.0}]


@pytest.mark.asyncio
async def test_graph_produces_report_with_bm25_only(monkeypatch):
    monkeypatch.setattr("src.graph.workflow.run_research", _fake_research)

    retriever = HybridRetriever()
    count = retriever.load_bm25_only("sample_data")
    assert count >= 5

    graph = StockIntelligenceGraph(retriever)
    state = await graph.run(
        run_id="test-run",
        ticker="NVDA",
        query="Should I be worried about NVIDIA export restrictions over the next 30 days?",
    )

    assert "NVDA" in state["report"].title
    assert len(state["rag"].evidence) >= 3
    assert state["report"].opportunity_score > 0
    assert state["report"].risk_score > 0
