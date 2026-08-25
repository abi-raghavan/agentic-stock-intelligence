from src.rag.retriever import reciprocal_rank_fusion, rewrite_query


def test_rewrite_query_adds_ticker_and_risk_terms():
    rewritten = rewrite_query("Should I be worried?", "NVDA")
    assert "NVDA" in rewritten
    assert "risk" in rewritten.lower() or "regulatory" in rewritten.lower()


def test_rrf_fuses_rankings():
    bm25 = [
        {"doc_id": "a", "bm25_score": 3.0, "snippet": "a"},
        {"doc_id": "b", "bm25_score": 2.0, "snippet": "b"},
    ]
    vector = [
        {"doc_id": "b", "vector_score": 0.9, "snippet": "b"},
        {"doc_id": "c", "vector_score": 0.8, "snippet": "c"},
    ]
    fused = reciprocal_rank_fusion([bm25, vector], score_key="bm25_score")
    ids = [item["doc_id"] for item in fused]
    assert set(ids) == {"a", "b", "c"}
    assert fused[0]["fused_score"] >= fused[-1]["fused_score"]
