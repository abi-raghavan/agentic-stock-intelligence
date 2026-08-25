import re
from dataclasses import dataclass

import yfinance as yf

from src.logging_config import get_logger
from src.tools.snapshots import has_snapshot

logger = get_logger(__name__)

_TICKER_RE = re.compile(r"^[A-Z0-9][A-Z0-9.\-]*$")

# NSE is the primary Indian venue, so it wins over BSE when a company is dual listed.
EXCHANGE_PRIORITY = {"NSI": 0, "NMS": 0, "NYQ": 0, "NGM": 0, "BSE": 1}

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
    # Ambiguous short forms that Yahoo maps to unrelated US listings.
    "sbi": "SBIN.NS",
    "state bank of india": "SBIN.NS",
    "lic": "LICI.NS",
    "l and t": "LT.NS",
    "larsen and toubro": "LT.NS",
    "hdfc": "HDFCBANK.NS",
    "icici": "ICICIBANK.NS",
    "axis bank": "AXISBANK.NS",
    "kotak": "KOTAKBANK.NS",
    "kotak bank": "KOTAKBANK.NS",
    "kotak mahindra bank": "KOTAKBANK.NS",
    # Renamed listings that no longer resolve under their old brand.
    "zomato": "ETERNAL.NS",
    "eternal": "ETERNAL.NS",
    "paytm": "PAYTM.NS",
    "adani enterprises": "ADANIENT.NS",
    "adani ports": "ADANIPORTS.NS",
    "asian paints": "ASIANPAINT.NS",
    "bajaj finance": "BAJFINANCE.NS",
    "sun pharma": "SUNPHARMA.NS",
    "tata steel": "TATASTEEL.NS",
    "titan": "TITAN.NS",
    "nestle india": "NESTLEIND.NS",
    "hindustan unilever": "HINDUNILVR.NS",
    "mahindra": "M&M.NS",
    "mahindra and mahindra": "M&M.NS",
}

INDEX_ALIASES: dict[str, str] = {
    "nifty": "^NSEI",
    "nifty 50": "^NSEI",
    "sensex": "^BSESN",
    "bank nifty": "^NSEBANK",
}

# Dropped before alias matching so "Tata Motors Ltd" and "Apple Inc" still match.
CORPORATE_SUFFIXES = ("ltd", "limited", "inc", "incorporated", "corp", "corporation", "plc", "company", "co")

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
    "SBIN.NS": "State Bank of India",
    "LICI.NS": "Life Insurance Corporation of India",
    "LT.NS": "Larsen & Toubro",
    "AXISBANK.NS": "Axis Bank",
    "KOTAKBANK.NS": "Kotak Mahindra Bank",
    "ETERNAL.NS": "Eternal (formerly Zomato)",
    "PAYTM.NS": "Paytm",
    "ADANIENT.NS": "Adani Enterprises",
    "ADANIPORTS.NS": "Adani Ports",
    "ASIANPAINT.NS": "Asian Paints",
    "BAJFINANCE.NS": "Bajaj Finance",
    "SUNPHARMA.NS": "Sun Pharma",
    "TATASTEEL.NS": "Tata Steel",
    "TITAN.NS": "Titan Company",
    "NESTLEIND.NS": "Nestle India",
    "HINDUNILVR.NS": "Hindustan Unilever",
    "M&M.NS": "Mahindra & Mahindra",
    "^NSEI": "Nifty 50",
    "^BSESN": "BSE Sensex",
    "^NSEBANK": "Bank Nifty",
}


@dataclass
class ResolvedSymbol:
    input_text: str
    yfinance_symbol: str
    display_name: str
    market: str
    news_query: str


def _normalize_key(text: str) -> str:
    return " ".join(text.strip().lower().replace("&", " and ").split())


def _strip_corporate_suffix(key: str) -> str:
    words = key.split()
    while len(words) > 1 and words[-1].strip(".") in CORPORATE_SUFFIXES:
        words.pop()
    return " ".join(words)


def _looks_like_ticker(text: str) -> bool:
    """A bare probe is only safe for ticker-shaped input.

    Probing a company name lets Yahoo fuzzy-match an unrelated listing, which is
    how "L&T" used to resolve to Lumen Technologies.
    """
    candidate = text.strip().upper()
    return bool(candidate) and " " not in candidate and len(candidate) <= 12 and _TICKER_RE.match(candidate) is not None


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

    candidates = []
    for rank, quote in enumerate(results.quotes or []):
        if quote.get("quoteType") != "EQUITY":
            continue
        exchange = quote.get("exchange", "")
        if exchange not in EXCHANGE_PRIORITY:
            continue
        symbol = quote.get("symbol")
        if not symbol:
            continue
        candidates.append((EXCHANGE_PRIORITY[exchange], rank, symbol.upper(), quote, exchange))

    if not candidates:
        return None

    _, _, symbol, quote, exchange = min(candidates)
    display = quote.get("longname") or quote.get("shortname") or query
    market = "IN" if exchange in ("NSI", "BSE") else "US"
    news_query = f"{display} stock India NSE" if market == "IN" else f"{display} stock"
    return ResolvedSymbol(query, symbol, display, market, news_query)


def _indian(text: str, symbol: str, display: str) -> ResolvedSymbol:
    return ResolvedSymbol(text, symbol, display, "IN", f"{display} stock India NSE")


def resolve_symbol(raw_input: str) -> ResolvedSymbol:
    text = raw_input.strip()
    key = _strip_corporate_suffix(_normalize_key(text))

    if key in INDIAN_ALIASES:
        symbol = INDIAN_ALIASES[key]
        return _indian(text, symbol, DISPLAY_NAMES.get(symbol, text.title()))

    if key in US_ALIASES:
        symbol = US_ALIASES[key]
        display = DISPLAY_NAMES.get(symbol, text.title())
        return ResolvedSymbol(text, symbol, display, "US", f"{display} stock")

    if key in INDEX_ALIASES:
        symbol = INDEX_ALIASES[key]
        return _indian(text, symbol, DISPLAY_NAMES.get(symbol, text.title()))

    upper = text.upper().replace(" ", "")

    if _is_indian_symbol(upper):
        return _indian(text, upper, _display_for(upper))

    # Company names go straight to search; only ticker-shaped input is probed,
    # so a name cannot fuzzy-match an unrelated listing.
    if _looks_like_ticker(text):
        if _has_market_data(upper):
            market = "IN" if _is_indian_symbol(upper) else "US"
            display = _display_for(upper)
            news = f"{display} stock India NSE" if market == "IN" else f"{display} stock"
            return ResolvedSymbol(text, upper, display, market, news)

        for suffix in (".NS", ".BO"):
            candidate = f"{upper.replace('.NS', '').replace('.BO', '')}{suffix}"
            if _has_market_data(candidate):
                return _indian(text, candidate, _display_for(candidate))

    searched = _search_yfinance(text)
    if searched:
        return searched

    if has_snapshot(upper):
        display = _display_for(upper)
        market = "IN" if _is_indian_symbol(upper) else "US"
        news = f"{display} stock India NSE" if market == "IN" else f"{display} stock"
        return ResolvedSymbol(text, upper, display, market, news)

    raise ValueError(f"Could not resolve symbol: {text}")
