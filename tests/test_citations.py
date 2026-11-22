import pytest

from src.models.schemas import CitedClaim, EvidenceItem
from src.rag.citations import build_sources_list, grounded_verify_claims, verify_claims


def test_verify_claims_filters_invalid_citations():
    claims = [CitedClaim(claim="Export risk remains elevated.", citation_ids=["E1", "E9"])]
    verified = verify_claims(claims, {"E1"})
    assert verified[0].verified is True
    assert verified[0].citation_ids == ["E1"]


def test_build_sources_list():
    evidence = [
        EvidenceItem(
            doc_id="1",
            source="SEC Filing",
            source_type="sec_filing",
            document_date="2025-03-15",
            snippet="sample",
            citation_id="E1",
        )
    ]
    sources = build_sources_list(evidence)
    assert sources == ["[E1] SEC Filing (2025-03-15)"]


@pytest.mark.asyncio
async def test_grounded_verify_falls_back_without_llm(monkeypatch):
    monkeypatch.setattr("src.rag.citations.llm_available", lambda: False)
    claims = [CitedClaim(claim="Export risk remains elevated.", citation_ids=["E1", "E9"])]
    evidence = [
        EvidenceItem(
            doc_id="1",
            source="SEC Filing",
            source_type="sec_filing",
            document_date="2025-03-15",
            snippet="Export controls remain a risk.",
            citation_id="E1",
        )
    ]
    verified = await grounded_verify_claims(claims, evidence)
    assert verified[0].verified is True
    assert verified[0].citation_ids == ["E1"]
