import json

from src.config import get_settings
from src.models.schemas import PlannerOutput
from src.tools.llm import call_ollama, parse_json_response

settings = get_settings()

DEFAULT_TASKS = [
    "Collect company news",
    "Collect company financials",
    "Analyze stock performance",
    "Retrieve supporting evidence",
    "Assess risks and opportunities",
    "Generate verified report",
]


async def run_planner(ticker: str, query: str) -> PlannerOutput:
    if not settings.enable_ollama:
        return PlannerOutput(ticker=ticker.upper(), intent=query, tasks=DEFAULT_TASKS)

    prompt = (
        f"Create an investigation plan for stock ticker {ticker.upper()} and user query: {query}. "
        "Return JSON with keys: ticker, intent, tasks (array of strings)."
    )
    content = await call_ollama(prompt, system="You are a financial investigation planner. Respond with JSON only.")
    data = parse_json_response(content)
    return PlannerOutput(
        ticker=ticker.upper(),
        intent=data.get("intent", query),
        tasks=data.get("tasks", DEFAULT_TASKS),
    )
