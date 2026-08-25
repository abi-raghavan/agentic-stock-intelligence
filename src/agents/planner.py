from __future__ import annotations

from src.models.schemas import PlannerOutput
from src.tools.llm import call_ollama, parse_json_response


async def run_planner(ticker: str, query: str) -> PlannerOutput:
    fallback = PlannerOutput(
        ticker=ticker.upper(),
        intent=query,
        tasks=[
            "Collect company news",
            "Collect company financials",
            "Analyze stock performance",
            "Retrieve supporting evidence",
            "Assess risks and opportunities",
            "Generate verified report",
        ],
    )
    prompt = (
        f"Create an investigation plan for stock ticker {ticker.upper()} and user query: {query}. "
        "Return JSON with keys: ticker, intent, tasks (array of strings)."
    )
    content = await call_ollama(prompt, system="You are a financial investigation planner. Respond with JSON only.")
    parsed = parse_json_response(content, {})
    data = {**fallback.model_dump(), **parsed}
    data["ticker"] = ticker.upper()
    if not data.get("intent"):
        data["intent"] = query
    if not data.get("tasks"):
        data["tasks"] = fallback.tasks
    return PlannerOutput(**data)
