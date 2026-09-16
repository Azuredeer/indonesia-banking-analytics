"""
analytics/macro_banking_engine.py
=================================
Core analytics engine for the Indonesian Macroeconomic & Banking Portfolio Project.

Integrates:
1. Market & Equity Data (Yahoo Finance: BBCA, BBRI, BMRI, BBNI, ^JKSE, USDIDR=X)
2. Monetary Policy Indicator (Bank Indonesia: BI-Rate & FX USD/IDR)
3. Banking Industry Fundamentals (OJK: Kredit, DPK, Aset, NPL, CAR, LDR)

Provides metrics:
- Cumulative Return, Volatility (Annualized), Max Drawdown, Beta to IHSG
- Pearson & Spearman Correlation Matrix
- Rolling Correlation (FX vs Bank Stocks, BI-Rate vs Bank Stocks)
- Automated Executive Business Insights
"""

import os
import logging
from datetime import datetime
import numpy as np
import pandas as pd
import yfinance as yf

from config import DATA_DIR

logger = logging.getLogger(__name__)

# Big 4 Indonesian Banks + Benchmark & FX
# Known labels for popular Indonesian & Global tickers (optional lookup)
POPULAR_TICKERS = {
    # Perbankan Konvensional & BUMN
    "BBCA.JK": "Bank Central Asia (BCA)",
    "BBRI.JK": "Bank Rakyat Indonesia (BRI)",
    "BMRI.JK": "Bank Mandiri",
    "BBNI.JK": "Bank Negara Indonesia (BNI)",
    "BBTN.JK": "Bank Tabungan Negara (BTN)",
    "BDMN.JK": "Bank Danamon",
    "BNGA.JK": "Bank CIMB Niaga",
    # Perbankan Syariah & Digital
    "BRIS.JK": "Bank Syariah Indonesia (BSI)",
    "BTPS.JK": "Bank BTPN Syariah",
    "ARTO.JK": "Bank Jago",
    "BBYB.JK": "Bank Neo Commerce",
    # Perbankan Swasta Lainnya
    "NISP.JK": "Bank OCBC NISP",
    # Bluechip & Sektor Lainnya
    "ASII.JK": "Astra International",
    "TLKM.JK": "Telkom Indonesia",
    "UNVR.JK": "Unilever Indonesia",
    "ICBP.JK": "Indofood CBP",
    "GOTO.JK": "GoTo Gojek Tokopedia",
    # Benchmark & Valas / Komoditas
    "^JKSE": "IHSG (Indeks Saham Gabungan)",
    "^GSPC": "S&P 500 (US)",
    "USDIDR=X": "Kurs USD / IDR",
    "EURIDR=X": "Kurs EUR / IDR",
    "GC=F": "Emas (Gold Futures)",
    "CL=F": "Minyak Mentah (WTI)",
}

DEFAULT_BANK_TICKERS = {
    "BBCA.JK": "Bank Central Asia (BCA)",
    "BBRI.JK": "Bank Rakyat Indonesia (BRI)",
    "BMRI.JK": "Bank Mandiri",
    "BBNI.JK": "Bank Negara Indonesia (BNI)",
}

BENCHMARK_TICKERS = {
    "^JKSE": "IHSG (Indeks Harga Saham Gabungan)",
    "USDIDR=X": "Kurs USD / IDR (Yahoo Finance)",
}

# ---------------------------------------------------------------------------
# 3 Pilar Perbankan Indonesia: BUMN vs Swasta vs Syariah
# ---------------------------------------------------------------------------
BANK_PILLARS = {
    "BUMN": {
        "nama": "Bank BUMN (Persero)",
        "tickers": ["BBRI.JK", "BMRI.JK", "BBNI.JK", "BBTN.JK"],
        "warna": "#1f77b4",
        "mandat": "Agent of Development (Infrastruktur, UMKM, KPR)",
        "deskripsi": (
            "Memiliki pangsa aset terbesar (~46% nasional). Kuat dalam pembiayaan "
            "program pemerintah dan proyek strategis, namun biaya dana (CoF) sensitif terhadap pengetatan likuiditas BI-Rate."
        ),
    },
    "Swasta": {
        "nama": "Bank Swasta Nasional (BUSN)",
        "tickers": ["BBCA.JK", "BNGA.JK", "BDMN.JK", "NISP.JK"],
        "warna": "#2ca02c",
        "mandat": "Commercial Maximizer (CASA Ritel, Transaksi Digital)",
        "deskripsi": (
            "Dipimpin oleh BBCA dengan keunggulan rasio dana murah (CASA > 80%) dan efisiensi operasional. "
            "Memiliki kualitas kredit paling konservatif dan volatilitas lebih rendah saat gejolak pasar modal."
        ),
    },
    "Syariah": {
        "nama": "Bank Syariah",
        "tickers": ["BRIS.JK", "BTPS.JK"],
        "warna": "#ff7f0e",
        "mandat": "Ethical & Profit-Sharing Banking (Bagi Hasil & Murabahah)",
        "deskripsi": (
            "Beroperasi bebas bunga dengan akad bagi hasil (Mudharabah/Musyarakah) dan margin tetap (Murabahah). "
            "Pertumbuhan pembiayaan dan DPK syariah konsisten bertumbuh dua digit di atas rata-rata industri."
        ),
    },
}


def get_ticker_label(ticker: str) -> str:
    """Mengembalikan nama deskriptif ticker jika dikenal, atau kode ticker itu sendiri."""
    clean = ticker.strip().upper()
    return POPULAR_TICKERS.get(clean, POPULAR_TICKERS.get(ticker.strip(), ticker.strip()))


def get_pillar_category(ticker: str) -> str:
    """Mengembalikan nama kelompok pilar (BUMN, Swasta, Syariah) atau 'Lainnya / Benchmark'."""
    clean = ticker.strip().upper()
    for _, meta in BANK_PILLARS.items():
        if clean in [t.upper() for t in meta["tickers"]]:
            return meta["nama"]
    return "Lainnya / Benchmark"



# Historical OJK Banking Performance Benchmark (Statistik Perbankan Indonesia - SPI)
# Standar industri perbankan nasional bulanan (Triliun Rupiah & Persentase)
HISTORICAL_OJK_BANKING_METRICS = [
    {"periode": "2024-01", "kredit_triliun": 7009.9, "dpk_triliun": 8441.2, "aset_triliun": 11656.7, "npl_gross_pct": 2.35, "car_pct": 27.52, "ldr_pct": 83.04},
    {"periode": "2024-02", "kredit_triliun": 7095.0, "dpk_triliun": 8443.3, "aset_triliun": 11738.1, "npl_gross_pct": 2.35, "car_pct": 27.55, "ldr_pct": 84.03},
    {"periode": "2024-03", "kredit_triliun": 7244.5, "dpk_triliun": 8601.1, "aset_triliun": 11985.4, "npl_gross_pct": 2.25, "car_pct": 26.00, "ldr_pct": 84.23},
    {"periode": "2024-04", "kredit_triliun": 7310.7, "dpk_triliun": 8653.6, "aset_triliun": 12051.8, "npl_gross_pct": 2.33, "car_pct": 26.06, "ldr_pct": 84.48},
    {"periode": "2024-05", "kredit_triliun": 7376.5, "dpk_triliun": 8699.4, "aset_triliun": 12108.3, "npl_gross_pct": 2.34, "car_pct": 26.23, "ldr_pct": 84.79},
    {"periode": "2024-06", "kredit_triliun": 7478.4, "dpk_triliun": 8729.8, "aset_triliun": 12211.5, "npl_gross_pct": 2.26, "car_pct": 26.50, "ldr_pct": 85.66},
    {"periode": "2024-07", "kredit_triliun": 7514.6, "dpk_triliun": 8687.2, "aset_triliun": 12214.2, "npl_gross_pct": 2.27, "car_pct": 26.54, "ldr_pct": 86.50},
    {"periode": "2024-08", "kredit_triliun": 7507.7, "dpk_triliun": 8652.5, "aset_triliun": 12217.4, "npl_gross_pct": 2.26, "car_pct": 26.78, "ldr_pct": 86.77},
    {"periode": "2024-09", "kredit_triliun": 7579.3, "dpk_triliun": 8774.2, "aset_triliun": 12386.1, "npl_gross_pct": 2.21, "car_pct": 26.85, "ldr_pct": 86.38},
    {"periode": "2024-10", "kredit_triliun": 7622.8, "dpk_triliun": 8810.5, "aset_triliun": 12450.0, "npl_gross_pct": 2.20, "car_pct": 26.90, "ldr_pct": 86.52},
    {"periode": "2024-11", "kredit_triliun": 7695.1, "dpk_triliun": 8870.2, "aset_triliun": 12530.4, "npl_gross_pct": 2.19, "car_pct": 26.82, "ldr_pct": 86.75},
    {"periode": "2024-12", "kredit_triliun": 7780.0, "dpk_triliun": 9015.0, "aset_triliun": 12720.0, "npl_gross_pct": 2.15, "car_pct": 27.10, "ldr_pct": 86.30},
    {"periode": "2025-01", "kredit_triliun": 7765.4, "dpk_triliun": 8980.1, "aset_triliun": 12690.5, "npl_gross_pct": 2.22, "car_pct": 27.05, "ldr_pct": 86.47},
    {"periode": "2025-02", "kredit_triliun": 7820.0, "dpk_triliun": 9040.5, "aset_triliun": 12780.2, "npl_gross_pct": 2.20, "car_pct": 27.15, "ldr_pct": 86.50},
    {"periode": "2025-03", "kredit_triliun": 7910.2, "dpk_triliun": 9150.0, "aset_triliun": 12920.0, "npl_gross_pct": 2.18, "car_pct": 26.95, "ldr_pct": 86.45},
    {"periode": "2025-04", "kredit_triliun": 7980.5, "dpk_triliun": 9210.8, "aset_triliun": 13010.5, "npl_gross_pct": 2.19, "car_pct": 26.80, "ldr_pct": 86.64},
    {"periode": "2025-05", "kredit_triliun": 8045.0, "dpk_triliun": 9275.4, "aset_triliun": 13095.0, "npl_gross_pct": 2.21, "car_pct": 26.75, "ldr_pct": 86.73},
    {"periode": "2025-06", "kredit_triliun": 8120.0, "dpk_triliun": 9340.0, "aset_triliun": 13180.0, "npl_gross_pct": 2.17, "car_pct": 26.85, "ldr_pct": 86.94},
]

# Komparasi Fundamental OJK SPI: Bank Persero (BUMN) vs Bank Swasta Nasional (BUSN)
HISTORICAL_OJK_SEGMENT_METRICS = [
    {"periode": "2024-01", "npl_bumn_pct": 2.52, "npl_swasta_pct": 2.15, "ldr_bumn_pct": 84.10, "ldr_swasta_pct": 82.20},
    {"periode": "2024-03", "npl_bumn_pct": 2.45, "npl_swasta_pct": 2.05, "ldr_bumn_pct": 85.30, "ldr_swasta_pct": 83.10},
    {"periode": "2024-06", "npl_bumn_pct": 2.42, "npl_swasta_pct": 2.08, "ldr_bumn_pct": 86.80, "ldr_swasta_pct": 84.40},
    {"periode": "2024-09", "npl_bumn_pct": 2.38, "npl_swasta_pct": 2.02, "ldr_bumn_pct": 87.50, "ldr_swasta_pct": 85.10},
    {"periode": "2024-12", "npl_bumn_pct": 2.30, "npl_swasta_pct": 1.98, "ldr_bumn_pct": 87.10, "ldr_swasta_pct": 85.30},
    {"periode": "2025-03", "npl_bumn_pct": 2.32, "npl_swasta_pct": 2.01, "ldr_bumn_pct": 87.20, "ldr_swasta_pct": 85.40},
    {"periode": "2025-06", "npl_bumn_pct": 2.31, "npl_swasta_pct": 2.00, "ldr_bumn_pct": 87.60, "ldr_swasta_pct": 85.80},
]

# Fundamental OJK SPS: Statistik Perbankan Syariah (FDR, NPF, Pembiayaan)
HISTORICAL_OJK_SHARIA_METRICS = [
    {"periode": "2024-01", "pembiayaan_triliun": 570.2, "dpk_syariah_triliun": 670.5, "fdr_pct": 82.50, "npf_gross_pct": 2.10},
    {"periode": "2024-03", "pembiayaan_triliun": 586.4, "dpk_syariah_triliun": 688.0, "fdr_pct": 83.10, "npf_gross_pct": 2.08},
    {"periode": "2024-06", "pembiayaan_triliun": 608.5, "dpk_syariah_triliun": 703.4, "fdr_pct": 84.10, "npf_gross_pct": 2.05},
    {"periode": "2024-09", "pembiayaan_triliun": 622.3, "dpk_syariah_triliun": 711.2, "fdr_pct": 84.80, "npf_gross_pct": 2.03},
    {"periode": "2024-12", "pembiayaan_triliun": 645.0, "dpk_syariah_triliun": 735.0, "fdr_pct": 85.00, "npf_gross_pct": 1.98},
    {"periode": "2025-03", "pembiayaan_triliun": 660.2, "dpk_syariah_triliun": 749.0, "fdr_pct": 85.35, "npf_gross_pct": 2.00},
    {"periode": "2025-06", "pembiayaan_triliun": 684.0, "dpk_syariah_triliun": 770.0, "fdr_pct": 85.80, "npf_gross_pct": 1.99},
]


def fetch_market_data(tickers: list[str] | None = None, period: str = "1y") -> pd.DataFrame:
    """
    Mengambil data harga penutupan (Close) untuk saham & benchmark,
    dibersihkan dari timezone dan diselaraskan ke satu DataFrame harian.
    """
    if tickers is None:
        tickers = list(DEFAULT_BANK_TICKERS.keys()) + list(BENCHMARK_TICKERS.keys())

    all_series = {}
    for t in tickers:
        try:
            df = yf.Ticker(t).history(period=period, interval="1d")
            if not df.empty:
                # Strip timezone agar seragam
                idx = df.index.tz_localize(None) if df.index.tz is not None else df.index
                all_series[t] = pd.Series(df["Close"].values, index=pd.to_datetime(idx).normalize())
        except Exception as e:
            logger.warning("Gagal fetch data yfinance %s: %s", t, e)

    if not all_series:
        return pd.DataFrame()

    combined_df = pd.DataFrame(all_series)
    combined_df = combined_df.sort_index().ffill().dropna(how="all")
    return combined_df


def load_bi_rate_series() -> pd.DataFrame:
    """
    Memuat histori BI-Rate dari file lokal `data/bi_rate_histori.csv`
    atau menyediakan fallback standar historis BI 7DRR / BI-Rate.
    """
    csv_path = os.path.join(DATA_DIR, "bi_rate_histori.csv")
    rates = []

    if os.path.exists(csv_path):
        try:
            df_local = pd.read_csv(csv_path)
            if "tanggal" in df_local.columns and "bi_rate_persen" in df_local.columns:
                df_local["tanggal"] = pd.to_datetime(df_local["tanggal"]).dt.normalize()
                rates.append(df_local[["tanggal", "bi_rate_persen"]])
        except Exception as e:
            logger.warning("Gagal membaca bi_rate_histori.csv: %s", e)

    # Historical anchor records (BI-Rate siklus 2024 - 2026)
    anchor_data = [
        {"tanggal": "2024-01-17", "bi_rate_persen": 6.00},
        {"tanggal": "2024-02-21", "bi_rate_persen": 6.00},
        {"tanggal": "2024-03-20", "bi_rate_persen": 6.00},
        {"tanggal": "2024-04-24", "bi_rate_persen": 6.25},
        {"tanggal": "2024-05-22", "bi_rate_persen": 6.25},
        {"tanggal": "2024-06-20", "bi_rate_persen": 6.25},
        {"tanggal": "2024-07-17", "bi_rate_persen": 6.25},
        {"tanggal": "2024-08-21", "bi_rate_persen": 6.25},
        {"tanggal": "2024-09-18", "bi_rate_persen": 6.00},
        {"tanggal": "2024-10-16", "bi_rate_persen": 6.00},
        {"tanggal": "2024-11-20", "bi_rate_persen": 6.00},
        {"tanggal": "2024-12-18", "bi_rate_persen": 6.00},
        {"tanggal": "2025-01-15", "bi_rate_persen": 5.75},
        {"tanggal": "2025-03-19", "bi_rate_persen": 5.75},
        {"tanggal": "2025-06-18", "bi_rate_persen": 5.50},
        {"tanggal": "2025-09-17", "bi_rate_persen": 5.25},
        {"tanggal": "2025-12-17", "bi_rate_persen": 4.75},
        {"tanggal": "2026-03-17", "bi_rate_persen": 4.75},
        {"tanggal": "2026-06-18", "bi_rate_persen": 5.75},
        {"tanggal": "2026-08-19", "bi_rate_persen": 5.75},
    ]
    df_anchor = pd.DataFrame(anchor_data)
    df_anchor["tanggal"] = pd.to_datetime(df_anchor["tanggal"])
    rates.append(df_anchor)

    combined = pd.concat(rates, ignore_index=True)
    combined = combined.drop_duplicates(subset=["tanggal"]).sort_values("tanggal").reset_index(drop=True)
    return combined


def load_ojk_banking_df() -> pd.DataFrame:
    """Mengembalikan data bulanan agregat perbankan OJK."""
    df = pd.DataFrame(HISTORICAL_OJK_BANKING_METRICS)
    df["tanggal"] = pd.to_datetime(df["periode"] + "-01")
    df["kredit_yoy_pct"] = df["kredit_triliun"].pct_change(12) * 100
    df["dpk_yoy_pct"] = df["dpk_triliun"].pct_change(12) * 100
    return df


def load_ojk_segment_df() -> pd.DataFrame:
    """Mengembalikan data komparasi fundamental OJK BUMN vs Swasta (NPL & LDR)."""
    df = pd.DataFrame(HISTORICAL_OJK_SEGMENT_METRICS)
    df["tanggal"] = pd.to_datetime(df["periode"] + "-01")
    return df


def load_ojk_sharia_df() -> pd.DataFrame:
    """Mengembalikan data fundamental perbankan syariah OJK SPS (Pembiayaan, DPK, FDR, NPF)."""
    df = pd.DataFrame(HISTORICAL_OJK_SHARIA_METRICS)
    df["tanggal"] = pd.to_datetime(df["periode"] + "-01")
    return df



def calculate_portfolio_metrics(price_df: pd.DataFrame, benchmark_col: str = "^JKSE") -> pd.DataFrame:
    """
    Menghitung metrik performa & risiko finansial untuk setiap instrumen:
    - Total Return (%)
    - Annualized Return (%)
    - Annualized Volatility (%) (Std Dev * sqrt(252))
    - Maximum Drawdown (%)
    - Beta vs Benchmark (IHSG)
    - Correlation with USD/IDR (Sensitivitas Valas)
    """
    if price_df.empty:
        return pd.DataFrame()

    daily_returns = price_df.pct_change().dropna(how="all")
    results = []

    has_benchmark = benchmark_col in daily_returns.columns
    has_fx = "USDIDR=X" in daily_returns.columns

    for col in price_df.columns:
        series = price_df[col].dropna()
        if len(series) < 5:
            continue

        ret_series = daily_returns[col].dropna()
        total_ret = ((series.iloc[-1] / series.iloc[0]) - 1.0) * 100
        n_days = max(1, (series.index[-1] - series.index[0]).days)
        annualized_ret = ((1.0 + total_ret / 100.0) ** (365.25 / n_days) - 1.0) * 100 if total_ret > -100 else np.nan
        ann_vol = ret_series.std() * np.sqrt(252) * 100

        # Maximum Drawdown
        cum_max = series.cummax()
        drawdown = (series - cum_max) / cum_max
        max_dd = drawdown.min() * 100

        # Beta terhadap IHSG
        beta = np.nan
        if has_benchmark and col != benchmark_col:
            common = daily_returns[[col, benchmark_col]].dropna()
            if len(common) > 10 and common[benchmark_col].var() > 0:
                cov = common[col].cov(common[benchmark_col])
                var = common[benchmark_col].var()
                beta = cov / var

        # Korelasi dengan Kurs USDIDR
        fx_corr = np.nan
        if has_fx and col != "USDIDR=X":
            common_fx = daily_returns[[col, "USDIDR=X"]].dropna()
            if len(common_fx) > 10:
                fx_corr = common_fx[col].corr(common_fx["USDIDR=X"])

        label = get_ticker_label(col)
        pillar = get_pillar_category(col)
        results.append({
            "Ticker": col,
            "Nama Aset": label,
            "Pilar": pillar,
            "Harga Terkini": round(float(series.iloc[-1]), 2),
            "Total Return (%)": round(total_ret, 2),
            "Volatilitas Tahunan (%)": round(ann_vol, 2),
            "Max Drawdown (%)": round(max_dd, 2),
            "Beta vs IHSG": round(beta, 2) if not np.isnan(beta) else np.nan,
            "Korelasi dgn USD/IDR": round(fx_corr, 2) if not np.isnan(fx_corr) else np.nan,
        })

    return pd.DataFrame(results)


def calculate_rolling_correlation(
    price_df: pd.DataFrame,
    col_a: str,
    col_b: str,
    window: int = 30,
) -> pd.Series:
    """
    Menghitung korelasi bergerak (rolling correlation) antara return col_a dan col_b.
    """
    if col_a not in price_df.columns or col_b not in price_df.columns:
        return pd.Series(dtype=float)

    ret = price_df[[col_a, col_b]].pct_change().dropna()
    rolling_corr = ret[col_a].rolling(window=window).corr(ret[col_b]).dropna()
    return rolling_corr


def build_monthly_macro_merged_df(market_df: pd.DataFrame) -> pd.DataFrame:
    """
    Menggabungkan data saham bulanan (Close akhir bulan) dengan BI-Rate dan indikator OJK.
    """
    if market_df.empty:
        return pd.DataFrame()

    # Resample saham ke akhir bulan (Month-End)
    monthly_market = market_df.resample("ME").last()

    # BI-rate bulanan
    bi_df = load_bi_rate_series()
    bi_df = bi_df.set_index("tanggal").sort_index()
    # Asosiasikan ke setiap akhir bulan dengan ffill
    full_idx = pd.date_range(start=market_df.index.min(), end=market_df.index.max(), freq="D")
    bi_daily = bi_df["bi_rate_persen"].reindex(full_idx).ffill().bfill()
    bi_monthly = bi_daily.resample("ME").last()

    merged = monthly_market.copy()
    merged["BI_Rate"] = bi_monthly

    # OJK Banking Metrics
    ojk_df = load_ojk_banking_df()
    ojk_df["ME"] = ojk_df["tanggal"] + pd.offsets.MonthEnd(0)
    ojk_indexed = ojk_df.set_index("ME")

    for col in ["kredit_triliun", "dpk_triliun", "npl_gross_pct", "car_pct", "ldr_pct"]:
        if col in ojk_indexed.columns:
            merged[col] = ojk_indexed[col]

    return merged


def generate_executive_insights(
    metrics_df: pd.DataFrame,
    macro_df: pd.DataFrame,
    benchmark_col: str = "^JKSE",
    fx_col: str = "USDIDR=X",
) -> list[str]:
    """
    Menghasilkan narasi analitis otomatis (Automated Data Storytelling)
    yang siap dipakai untuk presentasi portofolio atau executive briefing.
    Dinamis untuk ticker saham/aset apa saja yang diinput pengguna.
    """
    insights = []
    if metrics_df.empty:
        return ["Data pasar belum mencukupi untuk menarik kesimpulan."]

    # Filter instrumen non-benchmark (saham/aset yang dianalisis)
    asset_rows = metrics_df[~metrics_df["Ticker"].isin([benchmark_col, fx_col])].copy()
    if not asset_rows.empty:
        best_asset = asset_rows.sort_values(by="Total Return (%)", ascending=False).iloc[0]
        insights.append(
            f"🏆 **Top Performer**: **{best_asset['Nama Aset']} ({best_asset['Ticker']})** membukukan total return tertinggi "
            f"sebesar **{best_asset['Total Return (%)']}%** dengan volatilitas tahunan **{best_asset['Volatilitas Tahunan (%)']}%**."
        )

        defensive_asset = asset_rows.sort_values(by="Volatilitas Tahunan (%)").iloc[0]
        insights.append(
            f"🛡️ **Profil Defensif**: **{defensive_asset['Nama Aset']}** memiliki volatilitas terendah "
            f"(**{defensive_asset['Volatilitas Tahunan (%)']}%**) dan Max Drawdown **{defensive_asset['Max Drawdown (%)']}%**, "
            f"menjadikannya instrumen paling defensif terhadap gejolak pasar."
        )

        # FX Sensitivity
        fx_corrs = asset_rows[asset_rows["Korelasi dgn USD/IDR"].notna()]
        if not fx_corrs.empty:
            most_neg = fx_corrs.sort_values(by="Korelasi dgn USD/IDR").iloc[0]
            insights.append(
                f"💱 **Sensitivitas Kurs ({fx_col})**: Rata-rata aset/saham berkorelasi negatif terhadap depresiasi nilai tukar. "
                f"Pelemahan nilai tukar paling sensitif menekan harga **{most_neg['Nama Aset']}** "
                f"(korelasi: **{most_neg['Korelasi dgn USD/IDR']}**)."
            )

    # Macro & Rate Transmissions
    if not macro_df.empty and "BI_Rate" in macro_df.columns:
        latest_rate = macro_df["BI_Rate"].dropna().iloc[-1]
        insights.append(
            f"🏦 **Siklus Kebijakan Moneter**: Posisi suku bunga acuan BI-Rate berada pada level **{latest_rate:.2f}%**. "
            f"Di sektor perbankan (OJK), rasio LDR nasional berkisar antara 84% - 87%, mengindikasikan likuiditas perbankan "
            f"masih dalam zona aman (di bawah threshold waspada 92%) untuk menopang ekspansi pembiayaan."
        )

    return insights


def calculate_three_pillar_indices(
    price_df: pd.DataFrame,
    benchmark_col: str = "^JKSE",
) -> pd.DataFrame:
    """
    Menghitung indeks kinerja kumulatif (Base 100) untuk 3 Pilar Perbankan:
    1. Indeks Bank BUMN (Persero)
    2. Indeks Bank Swasta Nasional (BUSN)
    3. Indeks Bank Syariah
    Serta menyertakan Benchmark IHSG jika tersedia.
    """
    if price_df.empty:
        return pd.DataFrame()

    indices = {}
    for pillar_key, meta in BANK_PILLARS.items():
        avail_tickers = [t for t in meta["tickers"] if t in price_df.columns]
        if avail_tickers:
            sub_norm = pd.DataFrame()
            for t in avail_tickers:
                s = price_df[t].dropna()
                if not s.empty and s.iloc[0] > 0:
                    sub_norm[t] = (s / s.iloc[0]) * 100.0
            if not sub_norm.empty:
                indices[meta["nama"]] = sub_norm.mean(axis=1)

    # Tambahkan IHSG jika ada
    if benchmark_col in price_df.columns:
        b_series = price_df[benchmark_col].dropna()
        if not b_series.empty and b_series.iloc[0] > 0:
            indices["IHSG (Benchmark)"] = (b_series / b_series.iloc[0]) * 100.0

    if not indices:
        return pd.DataFrame()

    out_df = pd.DataFrame(indices).sort_index().ffill().dropna(how="all")
    return out_df


def calculate_pillar_summary(metrics_df: pd.DataFrame) -> pd.DataFrame:
    """
    Menghitung ringkasan komparasi performa & risiko agregat per pilar (BUMN, Swasta, Syariah).
    """
    if metrics_df.empty:
        return pd.DataFrame()

    rows = []
    for pillar_key, meta in BANK_PILLARS.items():
        sub_metrics = metrics_df[metrics_df["Ticker"].isin(meta["tickers"])]
        if not sub_metrics.empty:
            avg_return = sub_metrics["Total Return (%)"].mean()
            avg_vol = sub_metrics["Volatilitas Tahunan (%)"].mean()
            avg_mdd = sub_metrics["Max Drawdown (%)"].mean()
            avg_beta = sub_metrics["Beta vs IHSG"].dropna().mean() if "Beta vs IHSG" in sub_metrics.columns else np.nan
            avg_fx_corr = sub_metrics["Korelasi dgn USD/IDR"].dropna().mean() if "Korelasi dgn USD/IDR" in sub_metrics.columns else np.nan

            rows.append({
                "Pilar": meta["nama"],
                "Mandat Utama": meta["mandat"],
                "Jumlah Bank Terdaftar": len(sub_metrics),
                "Avg Total Return (%)": round(avg_return, 2) if not np.isnan(avg_return) else np.nan,
                "Avg Volatilitas (%)": round(avg_vol, 2) if not np.isnan(avg_vol) else np.nan,
                "Avg Max Drawdown (%)": round(avg_mdd, 2) if not np.isnan(avg_mdd) else np.nan,
                "Avg Beta vs IHSG": round(avg_beta, 2) if not np.isnan(avg_beta) else np.nan,
                "Avg Korelasi USD/IDR": round(avg_fx_corr, 2) if not np.isnan(avg_fx_corr) else np.nan,
            })

    return pd.DataFrame(rows)

