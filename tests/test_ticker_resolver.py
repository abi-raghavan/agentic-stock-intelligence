from src.tools.ticker_resolver import resolve_symbol


def test_resolve_tata_motors_by_name():
    r = resolve_symbol("Tata Motors")
    assert r.yfinance_symbol in {"TMPV.NS", "TMCV.NS"}
    assert r.market == "IN"
    assert "Tata" in r.display_name


def test_resolve_nse_ticker():
    r = resolve_symbol("RELIANCE.NS")
    assert r.yfinance_symbol == "RELIANCE.NS"
    assert r.market == "IN"


def test_resolve_us_ticker():
    r = resolve_symbol("NVDA")
    assert r.yfinance_symbol == "NVDA"
    assert r.market == "US"
