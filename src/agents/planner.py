from src.models.schemas import PlannerOutput
from src.tools.llm import call_llm, llm_available, parse_json_response

DEFAULT_TASKS = [
    "Collect company news",
    "Collect company financials",
    "Analyze stock performance",
    "Retrieve supporting evidence",
    "Assess risks and opportunities",
    "Generate verified report",
]


def _default_focus(ticker: str, query: str) -> list[str]:
    return [
        f"{ticker} {query}",
        f"{ticker} risks earnings valuation news",
        f"{ticker} growth outlook catalysts",
    ]


async def run_planner(ticker: str, query: str) -> PlannerOutput:
    ticker = ticker.upper()
    if not llm_available():
        return PlannerOutput(
            ticker=ticker,
            intent=query,
            tasks=DEFAULT_TASKS,
            focus_queries=_default_focus(ticker, query),
            llm_used=False,
        )

    prompt = (
        f"Create a short investigation plan for equity ticker {ticker}.\n"
        f"User question: {query}\n\n"
        "Return JSON with keys:\n"
        "- intent (string, restated research goal)\n"
        "- tasks (array of 4-6 short investigation steps)\n"
        "- focus_queries (array of 2-3 search queries for news/RAG, include ticker)\n"
    )
    content = await call_llm(
        prompt,
        system="You are a financial investigation planner. Respond with JSON only. Be concise.",
        json_mode=True,
        max_tokens=512,
    )
    data = parse_json_response(content)
    tasks = data.get("tasks") or DEFAULT_TASKS
    if not isinstance(tasks, list) or not tasks:
        tasks = DEFAULT_TASKS
    focus = data.get("focus_queries") or _default_focus(ticker, query)
    if not isinstance(focus, list) or not focus:
        focus = _default_focus(ticker, query)

    return PlannerOutput(
        ticker=ticker,
        intent=str(data.get("intent") or query),
        tasks=[str(t) for t in tasks][:6],
        focus_queries=[str(q) for q in focus][:3],
        llm_used=bool(content),
    )
