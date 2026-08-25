from __future__ import annotations

from src.models.schemas import ConfidenceLevel, ResearchOutput, RiskCategoryScore, RiskOutput


def synthesize_risk(research: ResearchOutput, evidence_count: int) -> RiskOutput:
    pos = len(research.positive_signals)
    neg = len(research.negative_signals)

    financial_risk = max(2.0, 10 - research.fundamental_score)
    market_risk = {"low": 3.0, "medium": 5.0, "high": 7.5}[research.volatility]
    if research.trend == "bearish":
        market_risk += 1.5
    regulatory_risk = 6.0 if any("export" in s.summary.lower() or "regulatory" in s.title.lower() for s in research.negative_signals) else 3.5
    competitive_risk = 4.0
    news_risk = min(9.0, 3.0 + neg * 1.2)

    categories = [
        RiskCategoryScore(category="Financial Risk", score=round(financial_risk, 1), rationale="Derived from fundamental score and earnings trend."),
        RiskCategoryScore(category="Market Risk", score=round(market_risk, 1), rationale="Based on recent price trend and volatility."),
        RiskCategoryScore(category="Regulatory Risk", score=round(regulatory_risk, 1), rationale="Informed by export control and policy-related news."),
        RiskCategoryScore(category="Competitive Risk", score=round(competitive_risk, 1), rationale="Sector competition and share dynamics."),
        RiskCategoryScore(category="News/Event Risk", score=round(news_risk, 1), rationale="Weighted by negative news signal count."),
    ]

    risk_score = round(sum(c.score for c in categories) / len(categories), 1)
    opportunity_score = round(
        min(
            10.0,
            max(
                1.0,
                (research.fundamental_score * 0.45)
                + (2.0 if research.trend == "bullish" else 0.0)
                + (pos * 0.8)
                - (neg * 0.6)
                + min(evidence_count, 5) * 0.2,
            ),
        ),
        1,
    )

    if evidence_count >= 5 and pos + neg >= 2:
        confidence = ConfidenceLevel.HIGH if evidence_count >= 8 else ConfidenceLevel.MEDIUM
    elif evidence_count >= 3:
        confidence = ConfidenceLevel.MEDIUM
    else:
        confidence = ConfidenceLevel.LOW

    key_risks = [s.title for s in research.negative_signals[:3]]
    key_opportunities = [s.title for s in research.positive_signals[:3]]
    if research.earnings_trend == "positive" and "Strong earnings momentum" not in key_opportunities:
        key_opportunities.append("Strong earnings momentum")

    return RiskOutput(
        opportunity_score=opportunity_score,
        risk_score=risk_score,
        confidence=confidence,
        risk_categories=categories,
        key_risks=key_risks or ["Limited negative catalysts identified in sample window"],
        key_opportunities=key_opportunities or ["Insufficient positive catalysts in sample window"],
    )
