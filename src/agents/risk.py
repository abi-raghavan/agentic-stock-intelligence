
from src.models.schemas import ResearchOutput, RiskOutput
from src.scoring.risk import synthesize_risk


async def run_risk(research: ResearchOutput, evidence_count: int) -> RiskOutput:
    return synthesize_risk(research, evidence_count)
