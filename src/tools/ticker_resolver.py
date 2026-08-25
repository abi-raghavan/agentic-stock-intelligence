from __future__ import annotations

from dataclasses import dataclass

from src.logging_config import get_logger

logger = get_logger(__name__)

INDIAN_ALIASES: dict[str, str] = {
    "tata motors": "TMPV.NS",
    "tatamotors": "TMPV.NS",
    "tata motor": "TMPV.NS",
    "tata motors passenger": "TMPV.NS",
    "tata motors commercial": "TMCV.NS",
    "tmcv": "TMCV.NS",
    "tmpv": "TMPV.NS",
    "reliance": "RELIANCE.NS",
    "reliance industries": "RELIANCE.NS",
    "tcs": "TCS.NS",
    "tata consultancy": "TCS.NS",
    "infosys": "INFY.NS",
    "infy": "INFY.NS",
    "hdfc bank": "HDFCBANK.NS",
    "hdfcbank": "HDFCBANK.NS",
    "icici bank": "ICICIBANK.NS",
    "icicibank": "ICICIBANK.NS",
    "wipro": "WIPRO.NS",
    "bharti airtel": "BHARTIARTL.NS",
    "airtel": "BHARTIARTL.NS",
    "maruti": "MARUTI.NS",
    "maruti suzuki": "MARUTI.NS",
    "sun pharma": "SUNPHARMA.NS",
    "sunpharma": "SUNPHARMA.NS",
    "bajaj finance": "BAJFINANCE.NS",
    "lt": "LT.NS",
    "larsen & toubro": "LT.NS",
    "larsen and toubro": "LT.NS",
    "axis bank": "AXISBANK.NS",
    "sbi": "SBIN.NS",
    "state bank of india": "SBIN.NS",
    "itc": "ITC.NS",
    "asian paints": "ASIANPAINT.NS",
}

DISPLAY_NAMES: dict[str, str] = {
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
    "SUNPHARMA.NS": "Sun Pharma",
    "BAJFINANCE.NS": "Bajaj Finance",
    "LT.NS": "Larsen & Toubro",
    "AXISBANK.NS": "Axis Bank",
    "SBIN.NS": "State Bank of India",
    "ITC.NS": "ITC",
    "ASIANPAINT.NS": "Asian Paints",
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
    upper = symbol.upper()
    return upper.endswith(".NS") or upper.endswith(".BO")


def _display_for(symbol: str) -> str:
    upper = symbol.upper()
    if upper in DISPLAY_NAMES:
        return DISPLAY_NAMES[upper]
    base = upper.replace(".NS", "").replace(".BO", "")
    return base.replace(".", " ").title()


def _validate_yfinance(symbol: str) -> bool:
    try:
        import yfinance as yf

        hist = yf.download(symbol, period="5d", progress=False)
        return hist is not None and not hist.empty
    except Exception:
        return False


def _search_yfinance(query: str) -> ResolvedSymbol | None:
    try:
        import yfinance as yf

        results = yf.Search(query, max_results=10)
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
            return ResolvedSymbol(
                input_text=query,
                yfinance_symbol=symbol.upper(),
                display_name=display,
                market=market,
                news_query=news_query,
            )
    except Exception as exc:
        logger.warning("yfinance_search_failed", query=query, error=str(exc))
    return None


def _try_indian_suffixes(base: str) -> str | None:
    base = base.upper().replace(".NS", "").replace(".BO", "")
    for suffix in (".NS", ".BO"):
        candidate = f"{base}{suffix}"
        if _validate_yfinance(candidate):
            return candidate
    return None


def resolve_symbol(raw_input: str) -> ResolvedSymbol:
    text = raw_input.strip()
    key = _normalize_key(text)

    if key in INDIAN_ALIASES:
        symbol = INDIAN_ALIASES[key]
        display = DISPLAY_NAMES.get(symbol, text.title())
        return ResolvedSymbol(
            input_text=text,
            yfinance_symbol=symbol,
            display_name=display,
            market="IN",
            news_query=f"{display} Tata Motors stock India NSE",
        )

    upper = text.upper().replace(" ", "")

    if _is_indian_symbol(upper):
        display = _display_for(upper)
        return ResolvedSymbol(
            input_text=text,
            yfinance_symbol=upper,
            display_name=display,
            market="IN",
            news_query=f"{display} stock India NSE",
        )

    if _validate_yfinance(upper):
        market = "IN" if _is_indian_symbol(upper) else "US"
        display = _display_for(upper)
        return ResolvedSymbol(
            input_text=text,
            yfinance_symbol=upper,
            display_name=display,
            market=market,
            news_query=f"{display} stock India NSE" if market == "IN" else f"{display} stock",
        )

    indian = _try_indian_suffixes(upper)
    if indian:
        display = _display_for(indian)
        return ResolvedSymbol(
            input_text=text,
            yfinance_symbol=indian,
            display_name=display,
            market="IN",
            news_query=f"{display} stock India NSE",
        )

    searched = _search_yfinance(text)
    if searched:
        return searched

    logger.warning("symbol_resolution_fallback", input=text)
    return ResolvedSymbol(
        input_text=text,
        yfinance_symbol=upper,
        display_name=text.title(),
        market="UNKNOWN",
        news_query=f"{text} stock India",
    )
