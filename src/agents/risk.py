from src.models.schemas import ResearchOutput, RiskOutput
from src.scoring.risk import synthesize_risk
from src.tools.llm import call_llm, llm_available, parse_json_response


async def run_risk(research: ResearchOutput, evidence_count: int) -> RiskOutput:
    risk = synthesize_risk(research, evidence_count)
    if not llm_available():
        return risk

    prompt = (
        "Refine key risks and opportunities for an equity risk synthesis.\n"
        f"Opportunity score={risk.opportunity_score}, risk score={risk.risk_score}.\n"
        f"Trend={research.trend}, volatility={research.volatility}, "
        f"fundamentals={research.fundamental_score}, earnings={research.earnings_trend}.\n"
        f"Positive headlines: {[s.title for s in research.positive_signals[:4]]}\n"
        f"Negative headlines: {[s.title for s in research.negative_signals[:4]]}\n"
        f"Current key_risks: {risk.key_risks}\n"
        f"Current key_opportunities: {risk.key_opportunities}\n\n"
        "Return JSON with keys key_risks and key_opportunities (each an array of up to 4 short strings). "
        "Do not invent numbers; keep wording concise and evidence-tied."
    )
    content = await call_llm(
        prompt,
        system="You are a risk synthesis assistant. Respond with JSON only.",
        json_mode=True,
        max_tokens=400,
    )
    data = parse_json_response(content)
    if isinstance(data.get("key_risks"), list) and data["key_risks"]:
        risk.key_risks = [str(x) for x in data["key_risks"]][:4]
    if isinstance(data.get("key_opportunities"), list) and data["key_opportunities"]:
        risk.key_opportunities = [str(x) for x in data["key_opportunities"]][:4]
    return risk
