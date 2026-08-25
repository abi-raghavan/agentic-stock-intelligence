import pytest

from src.graph.workflow import StockIntelligenceGraph
from src.rag.retriever import HybridRetriever


@pytest.mark.asyncio
async def test_graph_produces_report_with_bm25_only():
    retriever = HybridRetriever()
    count = retriever.load_bm25_only("sample_data")
    assert count >= 5

    graph = StockIntelligenceGraph(retriever)
    state = await graph.run(
        run_id="test-run",
        ticker="NVDA",
        query="Should I be worried about NVIDIA export restrictions over the next 30 days?",
    )

    assert state["report"].title == "NVDA Intelligence Report"
    assert len(state["rag"].evidence) >= 3
    assert len(state["report"].sources) >= 3
    assert state["report"].opportunity_score > 0
    assert state["report"].risk_score > 0
