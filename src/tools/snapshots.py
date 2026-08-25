"""Offline fallback for live market data.

Refresh with scripts/refresh_snapshots.py from a non-datacenter connection.
"""

import json
from functools import lru_cache
from pathlib import Path

from src.config import get_settings
from src.models.schemas import NewsSignal

settings = get_settings()
SNAPSHOT_FILE = "market_snapshots.json"


@lru_cache
def _load() -> dict:
    path = Path(settings.sample_data_dir) / SNAPSHOT_FILE
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def snapshot_date() -> str | None:
    return _load().get("as_of")


def _for(ticker: str) -> dict:
    return _load().get("snapshots", {}).get(ticker.upper(), {})


def has_snapshot(ticker: str) -> bool:
    return bool(_for(ticker))


def snapshot_market(ticker: str) -> dict | None:
    entry = _for(ticker)
    chart = entry.get("chart")
    if not chart:
        return None

    first_close = chart[0]["close"]
    last_close = chart[-1]["close"]
    pct = ((last_close - first_close) / first_close) * 100 if first_close else 0.0
    closes = [point["close"] for point in chart]
    daily = [
        (closes[i] - closes[i - 1]) / closes[i - 1]
        for i in range(1, len(closes))
        if closes[i - 1]
    ]
    mean = sum(daily) / len(daily) if daily else 0.0
    variance = sum((value - mean) ** 2 for value in daily) / len(daily) if daily else 0.0
    vol = variance**0.5

    return {
        "trend": "bullish" if pct > 2 else "bearish" if pct < -2 else "neutral",
        "volatility": "high" if vol > 0.03 else "low" if vol < 0.015 else "medium",
        "price_change_pct": round(pct, 2),
        "volume_trend": entry.get("volume_trend", "normal"),
        "chart": chart,
    }


def snapshot_fundamentals(ticker: str) -> dict | None:
    return _for(ticker).get("fundamentals") or None


def snapshot_news(ticker: str) -> list[NewsSignal]:
    return [NewsSignal(**item) for item in _for(ticker).get("news", [])]
