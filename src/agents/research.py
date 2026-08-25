from __future__ import annotations

from src.models.schemas import ResearchOutput
from src.tools.market import fetch_fundamentals, fetch_market_data, fetch_news_signals


async def run_research(
    ticker: str,
    display_name: str | None = None,
    news_query: str | None = None,
) -> tuple[ResearchOutput, list[dict]]:
    positive, negative = fetch_news_signals(ticker, news_query=news_query)
    fundamentals = fetch_fundamentals(ticker)
    market = fetch_market_data(ticker)
    research = ResearchOutput(
        positive_signals=positive,
        negative_signals=negative,
        fundamental_score=float(fundamentals["fundamental_score"]),
        earnings_trend=fundamentals["earnings_trend"],
        trend=market["trend"],
        volatility=market["volatility"],
        price_change_pct=market.get("price_change_pct"),
        volume_trend=market.get("volume_trend"),
    )
    return research, market.get("chart", [])
