import pytest

import src.tools.market as market
import src.tools.news as news
from src.agents.report import run_report_verify
from src.agents.research import run_research
from src.models.schemas import ConfidenceLevel, ResearchOutput, RiskOutput


def _rate_limited(*args, **kwargs):
    raise RuntimeError("Too Many Requests. Rate limited. Try after a while.")


@pytest.fixture
def throttled(monkeypatch):
    """Simulate Yahoo Finance and Google News rejecting a datacenter IP."""
    monkeypatch.setattr(market.yf, "download", _rate_limited)
    monkeypatch.setattr(market.yf, "Ticker", _rate_limited)
    monkeypatch.setattr(news.yf, "Ticker", _rate_limited)
    monkeypatch.setattr(news, "fetch_google_news_rss", _rate_limited)


@pytest.mark.asyncio
async def test_research_falls_back_to_snapshot(throttled):
    research, chart = await run_research("TMPV.NS", news_query="Tata Motors")

    assert chart, "cached snapshot should still provide a price series"
    assert research.trend in {"bullish", "bearish", "neutral"}
    assert any("cached" in note for note in research.degraded_sources)


@pytest.mark.asyncio
async def test_unknown_ticker_without_snapshot_raises(throttled):
    with pytest.raises(ValueError, match="No price history available"):
        await run_research("NOSUCHTICKER.NS")


@pytest.mark.asyncio
async def test_cached_data_caps_confidence():
    research = ResearchOutput(
        positive_signals=[],
        negative_signals=[],
        fundamental_score=8.0,
        earnings_trend="positive",
        trend="bullish",
        volatility="medium",
        degraded_sources=["market data cached 2026-08-25"],
    )
    risk = RiskOutput(
        opportunity_score=9.0,
        risk_score=2.0,
        confidence=ConfidenceLevel.HIGH,
        key_risks=["Regulatory risk"],
        key_opportunities=["EV demand"],
    )
    report = await run_report_verify("TMPV.NS", "outlook?", research, risk, [], [])

    assert report.confidence == ConfidenceLevel.MEDIUM
    assert "cached" in report.executive_summary
