from __future__ import annotations

from datetime import datetime, timedelta, timezone

from src.config import get_settings
from src.logging_config import get_logger
from src.models.schemas import NewsSignal
from src.tools.news import fetch_live_news

logger = get_logger(__name__)
settings = get_settings()


def _seed_news(ticker: str) -> tuple[list[NewsSignal], list[NewsSignal]]:
    if ticker.upper() != "NVDA":
        return [], []
    positive = [
        NewsSignal(
            title="NVIDIA data center revenue reaches record levels",
            summary="AI accelerator demand continues to drive sequential growth in data center segment.",
            sentiment="positive",
            source="Sample Financial News",
            date="2025-07-15",
        ),
        NewsSignal(
            title="Major cloud providers expand NVIDIA GPU deployments",
            summary="Hyperscalers announce expanded H100/B200 capacity for enterprise AI workloads.",
            sentiment="positive",
            source="Sample Tech Wire",
            date="2025-07-20",
        ),
    ]
    negative = [
        NewsSignal(
            title="Export control updates remain overhang for China sales",
            summary="Regulatory restrictions on advanced GPU exports create uncertainty in key markets.",
            sentiment="negative",
            source="Sample Policy Review",
            date="2025-07-10",
        ),
        NewsSignal(
            title="Valuation concerns after extended rally",
            summary="Analysts note premium multiples relative to semiconductor peers.",
            sentiment="negative",
            source="Sample Market Watch",
            date="2025-07-22",
        ),
    ]
    return positive, negative


def _fallback_chart() -> list[dict]:
    now = datetime.now(timezone.utc)
    return [
        {"date": (now - timedelta(days=i)).strftime("%Y-%m-%d"), "close": round(120 + i * 0.8, 2)}
        for i in range(30, 0, -1)
    ]


def fetch_market_data(ticker: str) -> dict:
    fallback = {
        "trend": "neutral",
        "volatility": "medium",
        "price_change_pct": 0.0,
        "volume_trend": "normal",
        "chart": _fallback_chart(),
        "live": False,
    }
    try:
        import yfinance as yf

        hist = yf.download(ticker, period="1mo", progress=False)
        if hist is None or hist.empty:
            if settings.enable_live_data:
                logger.warning("market_history_empty", ticker=ticker)
            return fallback if not settings.enable_live_data else {**fallback, "live": False}

        # Flatten multi-index columns from yf.download
        if hasattr(hist.columns, "levels") and len(hist.columns.levels) > 1:
            hist = hist.copy()
            hist.columns = hist.columns.get_level_values(0)
        first_close = float(hist["Close"].iloc[0])
        last_close = float(hist["Close"].iloc[-1])
        pct = ((last_close - first_close) / first_close) * 100 if first_close else 0.0
        returns = hist["Close"].pct_change().dropna()
        vol = float(returns.std()) if not returns.empty else 0.02
        trend = "bullish" if pct > 2 else "bearish" if pct < -2 else "neutral"
        volatility = "high" if vol > 0.03 else "low" if vol < 0.015 else "medium"
        chart = [
            {"date": idx.strftime("%Y-%m-%d"), "close": round(float(row["Close"]), 2)}
            for idx, row in hist.iterrows()
        ]
        return {
            "trend": trend,
            "volatility": volatility,
            "price_change_pct": round(pct, 2),
            "volume_trend": "above_average" if hist["Volume"].iloc[-1] > hist["Volume"].mean() else "normal",
            "chart": chart,
            "live": True,
        }
    except Exception as exc:
        logger.warning("market_data_fetch_failed", ticker=ticker, error=str(exc))
        return fallback


def fetch_news_signals(ticker: str, news_query: str | None = None) -> tuple[list[NewsSignal], list[NewsSignal]]:
    if settings.enable_live_data:
        positive, negative = fetch_live_news(ticker, news_query=news_query)
        if positive or negative:
            logger.info("live_news_fetched", ticker=ticker, positive=len(positive), negative=len(negative))
            return positive, negative
        logger.warning("live_news_empty_fallback", ticker=ticker)

    positive, negative = _seed_news(ticker)
    if positive or negative:
        return positive, negative
    return (
        [
            NewsSignal(
                title=f"{ticker.upper()} reports stable quarterly operations",
                summary="Company maintains operational continuity amid sector volatility.",
                sentiment="positive",
                source="Sample Feed",
                date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            )
        ],
        [],
    )


def fetch_fundamentals(ticker: str) -> dict:
    fallback = {
        "fundamental_score": 6.0,
        "earnings_trend": "neutral",
        "revenue_growth": "moderate",
        "guidance": "inline",
        "live": False,
    }
    try:
        import yfinance as yf

        info = yf.Ticker(ticker).info or {}
        if not info:
            return _seed_fundamentals(ticker) if not settings.enable_live_data else fallback

        revenue_growth = info.get("revenueGrowth")
        profit_margin = info.get("profitMargins")
        earnings_growth = info.get("earningsGrowth")
        recommendation = info.get("recommendationKey", "hold")

        score = 6.0
        if revenue_growth is not None:
            score += min(2.0, max(-2.0, float(revenue_growth) * 10))
        if profit_margin is not None:
            score += min(1.5, max(-1.5, float(profit_margin) * 5))
        if earnings_growth is not None:
            score += min(1.0, max(-1.0, float(earnings_growth) * 5))
        score = round(min(10.0, max(1.0, score)), 1)

        if earnings_growth is not None:
            earnings_trend = "positive" if earnings_growth > 0.05 else "negative" if earnings_growth < -0.05 else "neutral"
        else:
            earnings_trend = "neutral"

        revenue_label = "strong" if revenue_growth and revenue_growth > 0.1 else "moderate" if revenue_growth and revenue_growth > 0 else "weak"
        guidance = "above consensus" if recommendation in {"buy", "strong_buy"} else "below consensus" if recommendation in {"sell", "strong_sell"} else "inline"

        return {
            "fundamental_score": score,
            "earnings_trend": earnings_trend,
            "revenue_growth": revenue_label,
            "guidance": guidance,
            "live": True,
        }
    except Exception as exc:
        logger.warning("fundamentals_fetch_failed", ticker=ticker, error=str(exc))
        if not settings.enable_live_data:
            return _seed_fundamentals(ticker)
        return fallback


def _seed_fundamentals(ticker: str) -> dict:
    if ticker.upper() == "NVDA":
        return {
            "fundamental_score": 8.5,
            "earnings_trend": "positive",
            "revenue_growth": "strong",
            "guidance": "above consensus",
            "live": False,
        }
    return {
        "fundamental_score": 6.0,
        "earnings_trend": "neutral",
        "revenue_growth": "moderate",
        "guidance": "inline",
        "live": False,
    }
