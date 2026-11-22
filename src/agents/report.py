from src.models.schemas import (
    CitedClaim,
    ConfidenceLevel,
    EvidenceItem,
    ReportOutput,
    ResearchOutput,
    RiskOutput,
)
from src.rag.citations import build_sources_list, grounded_verify_claims
from src.tools.llm import call_llm, llm_available, parse_json_response


def _confidence(research: ResearchOutput, risk: RiskOutput) -> ConfidenceLevel:
    if research.degraded_sources and risk.confidence == ConfidenceLevel.HIGH:
        return ConfidenceLevel.MEDIUM
    return risk.confidence


def _outlook(research: ResearchOutput, risk: RiskOutput) -> str:
    if risk.opportunity_score - risk.risk_score >= 2:
        return "Moderately Bullish"
    if risk.risk_score - risk.opportunity_score >= 2:
        return "Moderately Bearish"
    return "Neutral to Cautiously Optimistic"


def _heuristic_claims(research: ResearchOutput, evidence: list[EvidenceItem]) -> list[CitedClaim]:
    return [
        CitedClaim(
            claim=f"Fundamental score is {research.fundamental_score}/10, earnings trend {research.earnings_trend}.",
            citation_ids=[evidence[0].citation_id] if evidence else [],
        ),
        CitedClaim(
            claim=f"Market trend is {research.trend} with {research.volatility} volatility.",
            citation_ids=[e.citation_id for e in evidence[:2]],
        ),
    ]


def _heuristic_summary(
    label: str,
    ticker: str,
    query: str,
    research: ResearchOutput,
    risk: RiskOutput,
    evidence: list[EvidenceItem],
) -> str:
    summary = (
        f"Analysis of {label} ({ticker.upper()}): {query} "
        f"Opportunity {risk.opportunity_score}/10, risk {risk.risk_score}/10. "
        f"Trend {research.trend}, volatility {research.volatility}. "
        f"{len(evidence)} evidence documents cited."
    )
    if research.degraded_sources:
        summary += f" Data provenance caveat: {', '.join(research.degraded_sources)}."
    return summary


async def _llm_report_draft(
    label: str,
    ticker: str,
    query: str,
    research: ResearchOutput,
    risk: RiskOutput,
    evidence: list[EvidenceItem],
) -> dict:
    evidence_block = "\n".join(
        f"[{e.citation_id}] ({e.source}) {e.snippet[:280]}" for e in evidence[:6]
    )
    pos = "; ".join(s.title for s in research.positive_signals[:4]) or "none"
    neg = "; ".join(s.title for s in research.negative_signals[:4]) or "none"
    prompt = (
        f"Write a grounded equity intelligence report for {label} ({ticker}).\n"
        f"User question: {query}\n"
        f"Scores: opportunity={risk.opportunity_score}/10, risk={risk.risk_score}/10, "
        f"fundamentals={research.fundamental_score}/10, trend={research.trend}, "
        f"volatility={research.volatility}, earnings={research.earnings_trend}.\n"
        f"Bullish headlines: {pos}\n"
        f"Bearish headlines: {neg}\n"
        f"Key risks: {', '.join(risk.key_risks[:3])}\n"
        f"Key opportunities: {', '.join(risk.key_opportunities[:3])}\n"
        f"Evidence (cite only these IDs):\n{evidence_block}\n\n"
        "Return JSON with keys:\n"
        "- executive_summary (2-4 sentences, cite like [E1] inline where used)\n"
        "- outlook (short phrase)\n"
        "- bullish_signals (array of up to 5 strings)\n"
        "- bearish_signals (array of up to 5 strings)\n"
        "- recommended_actions (array of 3 concrete next steps)\n"
        "- claims (array of {claim, citation_ids}) — 2 to 4 factual claims, each with real citation_ids from evidence\n"
    )
    content = await call_llm(
        prompt,
        system=(
            "You are a cautious equity research assistant. Never invent citation IDs. "
            "Only use provided evidence IDs. Respond with JSON only."
        ),
        json_mode=True,
        max_tokens=900,
    )
    return parse_json_response(content)


async def run_report_verify(
    ticker: str,
    query: str,
    research: ResearchOutput,
    risk: RiskOutput,
    evidence: list[EvidenceItem],
    market_chart: list[dict],
    display_name: str | None = None,
) -> ReportOutput:
    label = display_name or ticker.upper()
    bullish = [s.title for s in research.positive_signals] + risk.key_opportunities[:3]
    bearish = [s.title for s in research.negative_signals] + risk.key_risks[:3]
    outlook = _outlook(research, risk)
    summary = _heuristic_summary(label, ticker, query, research, risk, evidence)
    claims = _heuristic_claims(research, evidence)
    actions = [
        "Review cited evidence before any investment decision.",
        "Monitor upcoming earnings and sector news.",
        "Size exposure to match current volatility.",
    ]

    if llm_available():
        draft = await _llm_report_draft(label, ticker, query, research, risk, evidence)
        if draft:
            summary = str(draft.get("executive_summary") or summary)
            outlook = str(draft.get("outlook") or outlook)
            if isinstance(draft.get("bullish_signals"), list) and draft["bullish_signals"]:
                bullish = [str(x) for x in draft["bullish_signals"]][:5]
            if isinstance(draft.get("bearish_signals"), list) and draft["bearish_signals"]:
                bearish = [str(x) for x in draft["bearish_signals"]][:5]
            if isinstance(draft.get("recommended_actions"), list) and draft["recommended_actions"]:
                actions = [str(x) for x in draft["recommended_actions"]][:3]
            raw_claims = draft.get("claims")
            if isinstance(raw_claims, list) and raw_claims:
                parsed: list[CitedClaim] = []
                for item in raw_claims[:4]:
                    if not isinstance(item, dict):
                        continue
                    ids = item.get("citation_ids") or []
                    if not isinstance(ids, list):
                        ids = []
                    parsed.append(
                        CitedClaim(
                            claim=str(item.get("claim", "")).strip(),
                            citation_ids=[str(cid) for cid in ids],
                        )
                    )
                if parsed:
                    claims = parsed

    verified_claims = await grounded_verify_claims(claims, evidence)
    verification_passed = all(c.verified for c in verified_claims if c.citation_ids) if verified_claims else False
    if research.degraded_sources:
        summary = summary.rstrip()
        if "Data provenance caveat" not in summary:
            summary += f" Data provenance caveat: {', '.join(research.degraded_sources)}."

    return ReportOutput(
        title=f"{label} Intelligence Report",
        outlook=outlook,
        executive_summary=summary,
        bullish_signals=list(dict.fromkeys(bullish))[:5],
        bearish_signals=list(dict.fromkeys(bearish))[:5],
        opportunity_score=risk.opportunity_score,
        risk_score=risk.risk_score,
        confidence=_confidence(research, risk),
        top_evidence=evidence[:5],
        recommended_actions=actions,
        sources=build_sources_list(evidence),
        claims=verified_claims,
        verification_passed=verification_passed,
        market_chart=market_chart,
    )
