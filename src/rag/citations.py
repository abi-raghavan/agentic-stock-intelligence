from __future__ import annotations

from src.models.schemas import CitedClaim, EvidenceItem


def format_citation(evidence: EvidenceItem) -> str:
    date_part = f" ({evidence.document_date})" if evidence.document_date else ""
    return f"[{evidence.citation_id}] {evidence.source}{date_part}"


def build_sources_list(evidence: list[EvidenceItem]) -> list[str]:
    return [format_citation(item) for item in evidence]


def verify_claims(claims: list[CitedClaim], evidence_ids: set[str]) -> list[CitedClaim]:
    verified_claims = []
    for claim in claims:
        valid_ids = [cid for cid in claim.citation_ids if cid in evidence_ids]
        verified_claims.append(
            CitedClaim(
                claim=claim.claim,
                citation_ids=valid_ids,
                verified=bool(valid_ids),
            )
        )
    return verified_claims


def evidence_from_dict(items: list[dict]) -> list[EvidenceItem]:
    return [EvidenceItem(**item) for item in items]
