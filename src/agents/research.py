from src.models.schemas import PlannerOutput, ResearchOutput
from src.tools.market import fetch_fundamentals, fetch_market_data, fetch_news_signals


def _news_query_from_planner(
    ticker: str,
    display_name: str | None,
    news_query: str | None,
    planner: PlannerOutput | None,
) -> str:
    if planner and planner.focus_queries:
        return " ".join(planner.focus_queries[:2])
    if news_query:
        return news_query
    label = display_name or ticker
    return f"{label} stock"


async def run_research(
    ticker: str,
    display_name: str | None = None,
    news_query: str | None = None,
    planner: PlannerOutput | None = None,
) -> tuple[ResearchOutput, list[dict]]:
    resolved_news_query = _news_query_from_planner(ticker, display_name, news_query, planner)
    positive, negative = fetch_news_signals(ticker, news_query=resolved_news_query)
    fundamentals = fetch_fundamentals(ticker)
    market = fetch_market_data(ticker)

    degraded = []
    if not positive and not negative:
        degraded.append("news unavailable")
    if not fundamentals.get("available", True):
        degraded.append("fundamentals unavailable")
    elif fundamentals.get("cached_as_of"):
        degraded.append(f"fundamentals cached {fundamentals['cached_as_of']}")
    if market.get("cached_as_of"):
        degraded.append(f"market data cached {market['cached_as_of']}")

    research = ResearchOutput(
        positive_signals=positive,
        negative_signals=negative,
        fundamental_score=float(fundamentals["fundamental_score"]),
        earnings_trend=fundamentals["earnings_trend"],
        trend=market["trend"],
        volatility=market["volatility"],
        price_change_pct=market.get("price_change_pct"),
        volume_trend=market.get("volume_trend"),
        degraded_sources=degraded,
    )
    return research, market.get("chart", [])
