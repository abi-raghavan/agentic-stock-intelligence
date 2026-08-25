from dataclasses import dataclass

import yfinance as yf

from src.logging_config import get_logger
from src.tools.snapshots import has_snapshot

logger = get_logger(__name__)

US_ALIASES: dict[str, str] = {
    "nvidia": "NVDA",
    "apple": "AAPL",
    "microsoft": "MSFT",
    "tesla": "TSLA",
    "amazon": "AMZN",
    "alphabet": "GOOGL",
    "google": "GOOGL",
    "meta": "META",
    "facebook": "META",
    "netflix": "NFLX",
}

INDIAN_ALIASES: dict[str, str] = {
    "tata motors": "TMPV.NS",
    "tatamotors": "TMPV.NS",
    "tata motors passenger": "TMPV.NS",
    "tata motors commercial": "TMCV.NS",
    "reliance": "RELIANCE.NS",
    "reliance industries": "RELIANCE.NS",
    "tcs": "TCS.NS",
    "infosys": "INFY.NS",
    "infy": "INFY.NS",
    "hdfc bank": "HDFCBANK.NS",
    "icici bank": "ICICIBANK.NS",
    "wipro": "WIPRO.NS",
    "bharti airtel": "BHARTIARTL.NS",
    "airtel": "BHARTIARTL.NS",
    "maruti": "MARUTI.NS",
    "maruti suzuki": "MARUTI.NS",
    "itc": "ITC.NS",
}

DISPLAY_NAMES: dict[str, str] = {
    "NVDA": "NVIDIA",
    "AAPL": "Apple",
    "MSFT": "Microsoft",
    "TSLA": "Tesla",
    "AMZN": "Amazon",
    "GOOGL": "Alphabet",
    "META": "Meta Platforms",
    "NFLX": "Netflix",
    "TMPV.NS": "Tata Motors Passenger Vehicles",
    "TMCV.NS": "Tata Motors Commercial Vehicles",
    "RELIANCE.NS": "Reliance Industries",
    "TCS.NS": "Tata Consultancy Services",
    "INFY.NS": "Infosys",
    "HDFCBANK.NS": "HDFC Bank",
    "ICICIBANK.NS": "ICICI Bank",
    "WIPRO.NS": "Wipro",
    "BHARTIARTL.NS": "Bharti Airtel",
    "MARUTI.NS": "Maruti Suzuki",
    "ITC.NS": "ITC",
}


@dataclass
class ResolvedSymbol:
    input_text: str
    yfinance_symbol: str
    display_name: str
    market: str
    news_query: str


def _normalize_key(text: str) -> str:
    return " ".join(text.strip().lower().replace("&", "and").split())


def _is_indian_symbol(symbol: str) -> bool:
    return symbol.upper().endswith(".NS") or symbol.upper().endswith(".BO")


def _display_for(symbol: str) -> str:
    upper = symbol.upper()
    if upper in DISPLAY_NAMES:
        return DISPLAY_NAMES[upper]
    return upper.replace(".NS", "").replace(".BO", "").replace(".", " ").title()


def _has_market_data(symbol: str) -> bool:
    # Symbol probes are advisory: a throttled lookup must not fail resolution
    # outright, since alias and snapshot matching can still succeed.
    try:
        hist = yf.download(symbol, period="5d", progress=False)
    except Exception as exc:
        logger.warning("symbol_probe_failed", symbol=symbol, error=str(exc))
        return False
    return hist is not None and not hist.empty


def _search_yfinance(query: str) -> ResolvedSymbol | None:
    try:
        results = yf.Search(query, max_results=10)
    except Exception as exc:
        logger.warning("symbol_search_failed", query=query, error=str(exc))
        return None

    for quote in results.quotes or []:
        if quote.get("quoteType") != "EQUITY":
            continue
        exchange = quote.get("exchange", "")
        if exchange not in ("NSI", "BSE", "NMS", "NYQ", "NGM"):
            continue
        symbol = quote.get("symbol")
        if not symbol:
            continue
        display = quote.get("longname") or quote.get("shortname") or query
        market = "IN" if exchange in ("NSI", "BSE") else "US"
        news_query = f"{display} stock India NSE" if market == "IN" else f"{display} stock"
        return ResolvedSymbol(query, symbol.upper(), display, market, news_query)
    return None


def resolve_symbol(raw_input: str) -> ResolvedSymbol:
    text = raw_input.strip()
    key = _normalize_key(text)

    if key in INDIAN_ALIASES:
        symbol = INDIAN_ALIASES[key]
        display = DISPLAY_NAMES.get(symbol, text.title())
        return ResolvedSymbol(text, symbol, display, "IN", f"{display} stock India NSE")

    if key in US_ALIASES:
        symbol = US_ALIASES[key]
        display = DISPLAY_NAMES.get(symbol, text.title())
        return ResolvedSymbol(text, symbol, display, "US", f"{display} stock")

    upper = text.upper().replace(" ", "")

    if _is_indian_symbol(upper):
        display = _display_for(upper)
        return ResolvedSymbol(text, upper, display, "IN", f"{display} stock India NSE")

    if _has_market_data(upper):
        market = "IN" if _is_indian_symbol(upper) else "US"
        display = _display_for(upper)
        news = f"{display} stock India NSE" if market == "IN" else f"{display} stock"
        return ResolvedSymbol(text, upper, display, market, news)

    for suffix in (".NS", ".BO"):
        candidate = f"{upper.replace('.NS', '').replace('.BO', '')}{suffix}"
        if _has_market_data(candidate):
            display = _display_for(candidate)
            return ResolvedSymbol(text, candidate, display, "IN", f"{display} stock India NSE")

    searched = _search_yfinance(text)
    if searched:
        return searched

    if has_snapshot(upper):
        display = _display_for(upper)
        market = "IN" if _is_indian_symbol(upper) else "US"
        news = f"{display} stock India NSE" if market == "IN" else f"{display} stock"
        return ResolvedSymbol(text, upper, display, market, news)

    raise ValueError(f"Could not resolve symbol: {text}")
