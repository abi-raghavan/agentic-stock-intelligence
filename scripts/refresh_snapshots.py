"""Capture a live market snapshot for use as an offline fallback.

Cloud hosts (Render free tier included) share datacenter IPs that Yahoo Finance
rate limits, so the deployed demo cannot rely on live fetches. Run this from a
residential connection to refresh the committed snapshot.

    python scripts/refresh_snapshots.py
"""

import json
import time
from datetime import datetime, timezone
from pathlib import Path

from src.tools.market import _flatten_hist
from src.tools.news import fetch_google_news_rss

import yfinance as yf

TICKERS = {
    "TMPV.NS": "Tata Motors Passenger Vehicles",
    "TMCV.NS": "Tata Motors Commercial Vehicles",
    "RELIANCE.NS": "Reliance Industries",
    "TCS.NS": "Tata Consultancy Services",
    "INFY.NS": "Infosys",
    "HDFCBANK.NS": "HDFC Bank",
    "NVDA": "NVIDIA",
    "AAPL": "Apple",
    "MSFT": "Microsoft",
}

OUTPUT = Path("sample_data/market_snapshots.json")


def capture(ticker: str, name: str) -> dict | None:
    hist = _flatten_hist(yf.download(ticker, period="1mo", progress=False))
    if hist.empty:
        print(f"  skip {ticker}: no price history")
        return None

    chart = [
        {"date": idx.strftime("%Y-%m-%d"), "close": round(float(row["Close"]), 2)}
        for idx, row in hist.iterrows()
    ]
    volume_trend = "above_average" if hist["Volume"].iloc[-1] > hist["Volume"].mean() else "normal"

    info = yf.Ticker(ticker).info or {}
    fundamentals = {
        "revenueGrowth": info.get("revenueGrowth"),
        "profitMargins": info.get("profitMargins"),
        "earningsGrowth": info.get("earningsGrowth"),
        "recommendationKey": info.get("recommendationKey", "hold"),
    }

    news = [
        signal.model_dump()
        for signal in fetch_google_news_rss(ticker, limit=8, query=f"{name} stock")
    ]

    print(f"  {ticker}: {len(chart)} price points, {len(news)} headlines")
    return {"chart": chart, "volume_trend": volume_trend, "fundamentals": fundamentals, "news": news}


def main() -> None:
    snapshots = {}
    for ticker, name in TICKERS.items():
        print(f"fetching {ticker}...")
        captured = capture(ticker, name)
        if captured:
            snapshots[ticker] = captured
        time.sleep(1.5)

    payload = {
        "as_of": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "snapshots": snapshots,
    }
    OUTPUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"wrote {OUTPUT} with {len(snapshots)} tickers")


if __name__ == "__main__":
    main()
