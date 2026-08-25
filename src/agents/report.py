
from src.models.schemas import CitedClaim, ConfidenceLevel, EvidenceItem, ReportOutput, ResearchOutput, RiskOutput
from src.rag.citations import build_sources_list, verify_claims


def _confidence(research: ResearchOutput, risk: RiskOutput) -> ConfidenceLevel:
    # Cached or missing inputs cannot support a high-confidence conclusion.
    if research.degraded_sources and risk.confidence == ConfidenceLevel.HIGH:
        return ConfidenceLevel.MEDIUM
    return risk.confidence


def _outlook(research: ResearchOutput, risk: RiskOutput) -> str:
    if risk.opportunity_score - risk.risk_score >= 2:
        return "Moderately Bullish"
    if risk.risk_score - risk.opportunity_score >= 2:
        return "Moderately Bearish"
    return "Neutral to Cautiously Optimistic"


async def run_report_verify(
    ticker: str,
    query: str,
    research: ResearchOutput,
    risk: RiskOutput,
    evidence: list[EvidenceItem],
    market_chart: list[dict],
    display_name: str | None = None,
) -> ReportOutput:
    bullish = [s.title for s in research.positive_signals] + risk.key_opportunities[:3]
    bearish = [s.title for s in research.negative_signals] + risk.key_risks[:3]

    claims = [
        CitedClaim(
            claim=f"Fundamental score is {research.fundamental_score}/10, earnings trend {research.earnings_trend}.",
            citation_ids=[evidence[0].citation_id] if evidence else [],
        ),
        CitedClaim(
            claim=f"Market trend is {research.trend} with {research.volatility} volatility.",
            citation_ids=[e.citation_id for e in evidence[:2]],
        ),
    ]

    verified_claims = verify_claims(claims, {e.citation_id for e in evidence})
    verification_passed = all(c.verified for c in verified_claims if c.citation_ids)

    label = display_name or ticker.upper()
    summary = (
        f"Analysis of {label} ({ticker.upper()}): {query} "
        f"Opportunity {risk.opportunity_score}/10, risk {risk.risk_score}/10. "
        f"Trend {research.trend}, volatility {research.volatility}. "
        f"{len(evidence)} evidence documents cited."
    )
    if research.degraded_sources:
        summary += f" Data provenance caveat: {', '.join(research.degraded_sources)}."

    return ReportOutput(
        title=f"{label} Intelligence Report",
        outlook=_outlook(research, risk),
        executive_summary=summary,
        bullish_signals=list(dict.fromkeys(bullish))[:5],
        bearish_signals=list(dict.fromkeys(bearish))[:5],
        opportunity_score=risk.opportunity_score,
        risk_score=risk.risk_score,
        confidence=_confidence(research, risk),
        top_evidence=evidence[:5],
        recommended_actions=[
            "Review cited evidence before any investment decision.",
            "Monitor upcoming earnings and sector news.",
            "Size exposure to match current volatility.",
        ],
        sources=build_sources_list(evidence),
        claims=verified_claims,
        verification_passed=verification_passed,
        market_chart=market_chart,
    )
