"""
scrapers/yahoo_finance.py
===========================
Mengambil data harga saham/indeks/valas/komoditas dari Yahoo Finance
menggunakan library `yfinance` (bukan scraping HTML manual - lebih
stabil karena memakai endpoint data resmi yang dipakai yfinance).

Cocok untuk: saham IHSG (kode ".JK"), indeks global, kurs, emas, minyak, dst.
"""

import logging

import requests
import pandas as pd
import yfinance as yf

from config import DEFAULT_HEADERS, REQUEST_TIMEOUT

logger = logging.getLogger(__name__)

# Endpoint pencarian publik Yahoo Finance (dipakai fitur "search box" resmi
# di situs finance.yahoo.com). Ada 2 host yang biasa dipakai bergantian
# sebagai fallback kalau salah satu sedang rate-limit/bermasalah.
SEARCH_URL_CANDIDATES = [
    "https://query1.finance.yahoo.com/v1/finance/search",
    "https://query2.finance.yahoo.com/v1/finance/search",
]


def search_ticker(keyword: str, max_results: int = 10) -> list[dict]:
    """
    Cari kode ticker Yahoo Finance berdasarkan keyword bebas, misalnya nama
    perusahaan ("bank central asia"), singkatan ("bbca"), atau nama aset
    ("emas", "bitcoin").

    Parameters
    ----------
    keyword     : kata kunci pencarian
    max_results : jumlah hasil maksimum yang diminta ke Yahoo

    Returns
    -------
    list of dict: [{"symbol": str, "nama": str, "exchange": str, "tipe": str}, ...]
    Kosong jika keyword kosong atau pencarian gagal di semua kandidat URL.
    """
    keyword = (keyword or "").strip()
    if not keyword:
        return []

    params = {
        "q": keyword,
        "lang": "en-US",
        "region": "US",
        "quotesCount": max_results,
        "newsCount": 0,
    }

    for url in SEARCH_URL_CANDIDATES:
        logger.info("Mencari ticker Yahoo Finance untuk keyword '%s' via %s", keyword, url)
        try:
            resp = requests.get(url, params=params, headers=DEFAULT_HEADERS, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
        except (requests.RequestException, ValueError) as e:
            logger.warning("Gagal mencari ticker via %s: %s", url, e)
            continue

        quotes = data.get("quotes", [])
        results = []
        for q in quotes:
            symbol = q.get("symbol")
            if not symbol:
                continue
            results.append({
                "symbol": symbol,
                "nama": q.get("longname") or q.get("shortname") or "",
                "exchange": q.get("exchange", ""),
                "tipe": q.get("quoteType", ""),
            })

        if results:
            return results
        logger.warning("Tidak ada hasil dari %s untuk keyword '%s', coba kandidat lain.", url, keyword)

    logger.warning("Pencarian ticker gagal/kosong untuk keyword '%s' di semua kandidat URL.", keyword)
    return []


def get_historical_data(ticker: str, period: str = "6mo", interval: str = "1d") -> pd.DataFrame:
    """
    Ambil data historis harga untuk satu ticker.

    Parameters
    ----------
    ticker   : kode ticker Yahoo Finance, mis. "BBCA.JK", "^JKSE", "USDIDR=X"
    period   : rentang waktu, mis. "1mo", "6mo", "1y", "5y", "max"
    interval : granularitas, mis. "1d", "1wk", "1mo"

    Returns
    -------
    pd.DataFrame dengan kolom: Date, Open, High, Low, Close, Volume, ticker
    """
    logger.info("Mengambil data historis %s (period=%s, interval=%s)", ticker, period, interval)
    try:
        df = yf.Ticker(ticker).history(period=period, interval=interval)
    except Exception as e:  # yfinance bisa lempar berbagai jenis exception
        logger.error("Gagal mengambil data %s: %s", ticker, e)
        return pd.DataFrame()

    if df.empty:
        logger.warning("Data kosong untuk ticker %s (cek kode ticker / koneksi)", ticker)
        return df

    df = df.reset_index()
    df["ticker"] = ticker
    return df


def get_multiple_tickers(tickers: list[str], period: str = "6mo", interval: str = "1d") -> pd.DataFrame:
    """Ambil data historis untuk beberapa ticker sekaligus, digabung jadi satu DataFrame panjang."""
    all_dfs = []
    for t in tickers:
        df = get_historical_data(t, period=period, interval=interval)
        if not df.empty:
            all_dfs.append(df)
    if not all_dfs:
        return pd.DataFrame()
    return pd.concat(all_dfs, ignore_index=True)


def get_latest_quote(ticker: str) -> dict:
    """
    Ambil ringkasan kuotasi (harga terakhir, perubahan, dsb) untuk satu ticker.

    Returns
    -------
    dict berisi info ringkas, kosong jika gagal.
    """
    try:
        tk = yf.Ticker(ticker)
        info = tk.fast_info  # lebih ringan & stabil dibanding .info penuh
        return {
            "ticker": ticker,
            "harga_terakhir": getattr(info, "last_price", None),
            "harga_buka": getattr(info, "open", None),
            "harga_tertinggi_hari_ini": getattr(info, "day_high", None),
            "harga_terendah_hari_ini": getattr(info, "day_low", None),
            "volume": getattr(info, "last_volume", None),
            "mata_uang": getattr(info, "currency", None),
        }
    except Exception as e:
        logger.error("Gagal mengambil kuotasi %s: %s", ticker, e)
        return {}


def get_latest_quotes_multi(tickers: list[str]) -> pd.DataFrame:
    """Ambil kuotasi terakhir untuk beberapa ticker sekaligus dalam satu tabel ringkas."""
    rows = [get_latest_quote(t) for t in tickers]
    rows = [r for r in rows if r]  # buang yang gagal/kosong
    return pd.DataFrame(rows)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    df = get_historical_data("BBCA.JK", period="1mo")
    print(df.tail())
    print(get_latest_quotes_multi(["^JKSE", "BBCA.JK", "USDIDR=X"]))
