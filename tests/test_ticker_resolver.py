import pytest

from src.tools.ticker_resolver import _looks_like_ticker, resolve_symbol


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


@pytest.mark.parametrize(
    "query,expected",
    [
        # Short forms Yahoo used to map to unrelated US listings.
        ("SBI", "SBIN.NS"),
        ("L&T", "LT.NS"),
        ("LIC", "LICI.NS"),
        # Renamed listing that no longer resolves under its old brand.
        ("Zomato", "ETERNAL.NS"),
        # NSE should win over BSE for dual-listed companies.
        ("Asian Paints", "ASIANPAINT.NS"),
        ("Adani Enterprises", "ADANIENT.NS"),
    ],
)
def test_ambiguous_indian_names_resolve_to_nse(query, expected):
    assert resolve_symbol(query).yfinance_symbol == expected


@pytest.mark.parametrize("query", ["Tata Motors Ltd", "Tata Motors Limited"])
def test_corporate_suffix_is_ignored(query):
    assert resolve_symbol(query).yfinance_symbol == "TMPV.NS"


def test_company_names_are_not_probed_as_tickers():
    assert _looks_like_ticker("NVDA")
    assert _looks_like_ticker("TMPV.NS")
    assert not _looks_like_ticker("L&T")
    assert not _looks_like_ticker("Larsen & Toubro")
    assert not _looks_like_ticker("Tata Motors")


def test_unresolvable_input_raises():
    with pytest.raises(ValueError, match="Could not resolve symbol"):
        resolve_symbol("random gibberish xyz")
