import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import quote_plus

import feedparser
import httpx
import yfinance as yf

from src.models.schemas import NewsSignal

NEGATIVE_KEYWORDS = (
    "decline", "drop", "fall", "loss", "miss", "cut", "layoff", "lawsuit",
    "investigation", "recall", "warning", "risk", "restrict", "downgrade",
    "bearish", "selloff", "concern", "worried", "overvalued", "probe",
)
POSITIVE_KEYWORDS = (
    "surge", "rise", "gain", "beat", "record", "growth", "upgrade", "bullish",
    "partnership", "expand", "strong", "profit", "demand", "outperform", "raises guidance",
)


def _classify_sentiment(text: str) -> str:
    lower = text.lower()
    neg = sum(1 for word in NEGATIVE_KEYWORDS if word in lower)
    pos = sum(1 for word in POSITIVE_KEYWORDS if word in lower)
    if neg > pos:
        return "negative"
    if pos > neg:
        return "positive"
    return "neutral"


def _parse_date(value) -> str | None:
    if not value:
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=timezone.utc).strftime("%Y-%m-%d")
    if isinstance(value, str):
        if re.match(r"\d{4}-\d{2}-\d{2}", value):
            return value[:10]
        return parsedate_to_datetime(value).strftime("%Y-%m-%d")
    return None


def _to_signal(title: str, summary: str, source: str, date: str | None) -> NewsSignal:
    combined = f"{title} {summary}"
    sentiment = _classify_sentiment(combined)
    return NewsSignal(
        title=title.strip(),
        summary=summary.strip()[:500],
        sentiment=sentiment,
        source=source,
        date=date,
    )


def fetch_yfinance_news(ticker: str, limit: int = 8) -> list[NewsSignal]:
    articles = yf.Ticker(ticker).news or []
    signals: list[NewsSignal] = []
    for article in articles[:limit]:
        content = article.get("content") or article
        title = content.get("title") or article.get("title") or "Untitled"
        summary = content.get("summary") or content.get("description") or title
        provider = content.get("provider") or {}
        source = provider.get("displayName") if isinstance(provider, dict) else "Yahoo Finance"
        pub_date = content.get("pubDate") or content.get("displayTime") or article.get("providerPublishTime")
        signals.append(_to_signal(title, summary, source or "Yahoo Finance", _parse_date(pub_date)))
    return signals


def fetch_google_news_rss(ticker: str, limit: int = 8, query: str | None = None) -> list[NewsSignal]:
    search = query or f"{ticker} stock"
    url = f"https://news.google.com/rss/search?q={quote_plus(search)}&hl=en-IN&gl=IN&ceid=IN:en"
    response = httpx.get(url, timeout=15.0, follow_redirects=True)
    response.raise_for_status()
    feed = feedparser.parse(response.text)
    signals: list[NewsSignal] = []
    for entry in feed.entries[:limit]:
        title = entry.get("title", "Untitled")
        summary = re.sub(r"<[^>]+>", "", entry.get("summary", title))
        source = entry.get("source", {}).get("title", "Google News")
        signals.append(_to_signal(title, summary, source, _parse_date(entry.get("published"))))
    return signals


def fetch_live_news(ticker: str, limit: int = 10, news_query: str | None = None) -> tuple[list[NewsSignal], list[NewsSignal]]:
    combined: list[NewsSignal] = []
    seen: set[str] = set()
    for signal in fetch_yfinance_news(ticker, limit=limit) + fetch_google_news_rss(ticker, limit=limit, query=news_query):
        key = signal.title.lower().strip()
        if key in seen:
            continue
        seen.add(key)
        combined.append(signal)

    positive = [s for s in combined if s.sentiment == "positive"][:5]
    negative = [s for s in combined if s.sentiment == "negative"][:5]
    return positive, negative


def news_to_rag_documents(signals: list[NewsSignal]) -> list[dict[str, str]]:
    return [
        {
            "title": signal.title,
            "source": signal.source,
            "source_type": "live_news",
            "document_date": signal.date or datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "content": f"{signal.title}. {signal.summary} Sentiment: {signal.sentiment}.",
        }
        for signal in signals
    ]
