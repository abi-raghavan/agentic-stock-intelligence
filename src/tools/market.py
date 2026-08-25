import yfinance as yf

from src.config import get_settings
from src.models.schemas import NewsSignal
from src.tools.news import fetch_live_news

settings = get_settings()


def _flatten_hist(hist):
    if hasattr(hist.columns, "levels") and len(hist.columns.levels) > 1:
        hist = hist.copy()
        hist.columns = hist.columns.get_level_values(0)
    return hist


def fetch_market_data(ticker: str) -> dict:
    hist = _flatten_hist(yf.download(ticker, period="1mo", progress=False))
    if hist.empty:
        raise ValueError(f"No market data for {ticker}")

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
    }


def fetch_news_signals(ticker: str, news_query: str | None = None) -> tuple[list[NewsSignal], list[NewsSignal]]:
    if not settings.enable_live_data:
        return [], []
    positive, negative = fetch_live_news(ticker, news_query=news_query)
    if not positive and not negative:
        raise ValueError(f"No news found for {ticker}")
    return positive, negative


def fetch_fundamentals(ticker: str) -> dict:
    info = yf.Ticker(ticker).info or {}
    if not info:
        raise ValueError(f"No fundamentals for {ticker}")

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
    }
