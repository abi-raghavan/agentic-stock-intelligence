
from typing import Any, TypedDict

from src.models.schemas import PlannerOutput, RAGOutput, ReportOutput, ResearchOutput, RiskOutput


class GraphState(TypedDict, total=False):
    run_id: str
    ticker: str
    display_name: str
    market: str
    news_query: str
    query: str
    planner: PlannerOutput
    research: ResearchOutput
    rag: RAGOutput
    risk: RiskOutput
    report: ReportOutput
    events: list[dict[str, Any]]
    retry_rag: bool
    market_chart: list[dict[str, Any]]
