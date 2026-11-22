from src.models.schemas import CitedClaim, EvidenceItem
from src.tools.llm import call_llm, llm_available, parse_json_response


def format_citation(evidence: EvidenceItem) -> str:
    date_part = f" ({evidence.document_date})" if evidence.document_date else ""
    return f"[{evidence.citation_id}] {evidence.source}{date_part}"


def build_sources_list(evidence: list[EvidenceItem]) -> list[str]:
    return [format_citation(item) for item in evidence]


def verify_claims(claims: list[CitedClaim], evidence_ids: set[str]) -> list[CitedClaim]:
    """Structural check: citation IDs must exist in retrieved evidence."""
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


async def grounded_verify_claims(
    claims: list[CitedClaim],
    evidence: list[EvidenceItem],
) -> list[CitedClaim]:
    """
    Two-stage groundedness:
    1) citation IDs must exist
    2) free LLM checks whether cited snippets support each claim
    Falls back to ID-only verification when no LLM is configured.
    """
    evidence_by_id = {e.citation_id: e for e in evidence}
    structural = verify_claims(claims, set(evidence_by_id))

    if not llm_available() or not structural:
        return structural

    evidence_block = "\n".join(f"[{e.citation_id}] {e.snippet}" for e in evidence[:8])
    claims_block = "\n".join(
        f"- claim: {c.claim} | citations: {','.join(c.citation_ids) or 'none'}" for c in structural
    )
    prompt = (
        "You are a groundedness checker for equity research claims.\n"
        "For each claim, decide if the cited evidence snippets support it.\n"
        "A claim is grounded only if (a) it has citation IDs and (b) those snippets support the claim.\n"
        "Return JSON: {\"results\": [{\"claim\": \"...\", \"citation_ids\": [\"E1\"], \"verified\": true/false}]}\n\n"
        f"Evidence:\n{evidence_block}\n\nClaims:\n{claims_block}"
    )
    content = await call_llm(
        prompt,
        system="Respond with JSON only. Be strict: unsupported or weakly supported claims are verified=false.",
        json_mode=True,
        max_tokens=700,
    )
    data = parse_json_response(content)
    results = data.get("results")
    if not isinstance(results, list) or not results:
        return structural

    by_claim = {str(r.get("claim", "")).strip().lower(): r for r in results if isinstance(r, dict)}
    grounded: list[CitedClaim] = []
    for claim in structural:
        match = by_claim.get(claim.claim.strip().lower())
        if not match:
            grounded.append(claim)
            continue
        ids = match.get("citation_ids") or claim.citation_ids
        if not isinstance(ids, list):
            ids = claim.citation_ids
        valid_ids = [cid for cid in ids if cid in evidence_by_id]
        llm_ok = bool(match.get("verified")) and bool(valid_ids)
        grounded.append(
            CitedClaim(
                claim=claim.claim,
                citation_ids=valid_ids,
                verified=llm_ok,
            )
        )
    return grounded


def evidence_from_dict(items: list[dict]) -> list[EvidenceItem]:
    return [EvidenceItem(**item) for item in items]
