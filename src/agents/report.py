from __future__ import annotations

from src.config import get_settings
from src.models.schemas import CitedClaim, ConfidenceLevel, EvidenceItem, ReportOutput, ResearchOutput, RiskOutput
from src.rag.citations import build_sources_list, verify_claims

settings = get_settings()


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
    bullish = [s.title for s in research.positive_signals] + [
        opp for opp in risk.key_opportunities if opp not in [s.title for s in research.positive_signals]
    ]
    bearish = [s.title for s in research.negative_signals] + [
        r for r in risk.key_risks if r not in [s.title for s in research.negative_signals]
    ]

    claims = [
        CitedClaim(
            claim=f"Fundamental quality score is {research.fundamental_score}/10 with {research.earnings_trend} earnings trend.",
            citation_ids=[evidence[0].citation_id] if evidence else [],
        ),
        CitedClaim(
            claim=f"Market trend appears {research.trend} with {research.volatility} volatility.",
            citation_ids=[e.citation_id for e in evidence[:2]],
        ),
    ]
    if research.negative_signals:
        claims.append(
            CitedClaim(
                claim=research.negative_signals[0].summary,
                citation_ids=[e.citation_id for e in evidence if "regulatory" in e.snippet.lower() or "export" in e.snippet.lower()][:1]
                or ([evidence[0].citation_id] if evidence else []),
            )
        )

    evidence_ids = {e.citation_id for e in evidence}
    verified_claims = verify_claims(claims, evidence_ids)
    verification_passed = all(claim.verified for claim in verified_claims if claim.citation_ids)

    label = display_name or ticker.upper()
    summary_parts = [
        f"This intelligence brief analyzes {label} ({ticker.upper()}) in response to: {query}",
        f"Opportunity score {risk.opportunity_score}/10 vs risk score {risk.risk_score}/10.",
        f"Market trend is {research.trend}; volatility is {research.volatility}.",
    ]
    if evidence:
        summary_parts.append(f"Analysis grounded in {len(evidence)} retrieved evidence documents.")
    if settings.enable_live_data:
        summary_parts.append("Live market, news, and fundamentals data were used where available.")

    recommended_actions = [
        "Review cited export control and regulatory evidence before sizing exposure.",
        "Monitor next earnings release and data center revenue commentary.",
        "Set risk limits aligned with current volatility regime.",
    ]
    if risk.confidence == ConfidenceLevel.LOW:
        recommended_actions.insert(0, "Treat conclusions as preliminary; rerun analysis with expanded corpus.")

    return ReportOutput(
        title=f"{label} Intelligence Report",
        outlook=_outlook(research, risk),
        executive_summary=" ".join(summary_parts),
        bullish_signals=bullish[:5],
        bearish_signals=bearish[:5],
        opportunity_score=risk.opportunity_score,
        risk_score=risk.risk_score,
        confidence=risk.confidence,
        top_evidence=evidence[:5],
        recommended_actions=recommended_actions,
        sources=build_sources_list(evidence),
        claims=verified_claims,
        verification_passed=verification_passed,
        market_chart=market_chart,
    )
