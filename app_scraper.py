#!/usr/bin/env python3
"""
app_scraper.py
==============
Aplikasi Web Streamlit: Scraper & Pipeline Data Finansial & Makroekonomi Publik.
(Fokus Artikel 1: Data Engineering / Web Scraping & Ingestion)

Sumber Data:
1. Bank Indonesia (Kurs Transaksi XML & Suku Bunga BI-Rate HTML)
2. OJK (Statistik Perbankan Indonesia - SPI/SPS/IKNB)
3. Yahoo Finance (Saham, Indeks, Valas, Komoditas)

Cara Menjalankan:
    streamlit run app_scraper.py \\ ini jangan lupa
"""

import logging
from datetime import date, timedelta
import pandas as pd
import streamlit as st

from config import DEFAULT_TICKERS
from scrapers import yahoo_finance, bi_kurs, bi_rate, ojk_stats
from utils.storage import save_all, save_csv, df_to_excel_bytes

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(message)s")
logger = logging.getLogger("app_scraper")

st.set_page_config(
    page_title="Data Scraper Finansial & Makroekonomi",
    page_icon="🌐",
    layout="wide",
)


# ---------------------------------------------------------------------------
# Helper UI
# ---------------------------------------------------------------------------
def download_buttons(df: pd.DataFrame, base_name: str, key_prefix: str):
    """Tampilkan tombol download CSV & Excel untuk DataFrame."""
    if df is None or df.empty:
        return
    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            "⬇️ Download CSV",
            data=df.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"{base_name}.csv",
            mime="text/csv",
            key=f"{key_prefix}_csv",
        )
    with col2:
        st.download_button(
            "⬇️ Download Excel",
            data=df_to_excel_bytes(df),
            file_name=f"{base_name}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key=f"{key_prefix}_xlsx",
        )


def also_save_to_disk(save: bool, df: pd.DataFrame, name: str):
    if save and df is not None and not df.empty:
        results = save_all(df, name)
        saved_paths = [p for p in results.values() if p]
        if saved_paths:
            st.caption("Tersimpan juga di folder `data/`: " + ", ".join(saved_paths))


# ---------------------------------------------------------------------------
# Sidebar navigasi
# ---------------------------------------------------------------------------
st.sidebar.title("🌐 Pipeline & Scraper")
st.sidebar.caption("Artikel 1: Automated Data Collection")

page = st.sidebar.radio(
    "Pilih Sumber Data:",
    [
        "🏠 Beranda Scraper",
        "💹 Yahoo Finance",
        "💱 Kurs Bank Indonesia",
        "🏦 BI-Rate",
        "📑 Statistik OJK",
    ],
)

save_to_disk = st.sidebar.checkbox(
    "Simpan hasil ke folder data/ lokal (CSV & Excel)",
    value=True,
    help="Selain bisa didownload langsung dari browser, hasil juga disimpan otomatis ke disk.",
)

st.sidebar.markdown("---")
st.sidebar.caption(
    "💡 Untuk menganalisis data yang sudah dikumpulkan, jalankan aplikasi analisa: `streamlit run app_analytics.py`"
)


# ---------------------------------------------------------------------------
# 1. Halaman: Beranda Scraper
# ---------------------------------------------------------------------------
if page == "🏠 Beranda Scraper":
    st.title("🌐 Scraper Data Finansial & Makroekonomi Publik")
    st.markdown(
        """
        Selamat datang di **Data Scraping & Ingestion Hub**. Aplikasi ini dirancang khusus
        untuk mengotomatisasi pengambilan data publik dari tiga institusi finansial utama:

        | Sumber | Jenis Data | Metode Ekstraksi | Output |
        |---|---|---|---|
        | **Bank Indonesia** | Kurs Transaksi BI (Mata Uang Asing) | Web Service Resmi (`wskursbi.asmx` XML) | CSV / Excel / DataFrame |
        | **Bank Indonesia** | Suku Bunga Acuan (BI-Rate / BI7DRR) | HTML Scraping (`BeautifulSoup` + Regex) | CSV / Excel / DataFrame |
        | **OJK** | Statistik Sektor Keuangan (SPI/SPS/IKNB) | HTML Link Extractor & File Downloader | PDF / XLSX / Arsip |
        | **Yahoo Finance** | Saham IHSG, Global, Valas, Komoditas | API Wrapper (`yfinance`) | CSV / Excel / DataFrame |

        ---
        ### 🎯 Tujuan Aplikasi Ini:
        1. Menyediakan data mentah yang bersih, terstandardisasi, dan *timezone-safe*.
        2. Menjadi fondasi data pipeline untuk artikel riset dan analisis pasar modal.
        3. Memungkinkan ekspor instan ke format CSV & Excel untuk kebutuhan pelaporan.
        """
    )


# ---------------------------------------------------------------------------
# 2. Halaman: Yahoo Finance
# ---------------------------------------------------------------------------
elif page == "💹 Yahoo Finance":
    st.title("💹 Yahoo Finance Scraper")
    st.write("Cari saham, indeks, valas, atau komoditas apa saja dengan kata kunci bebas.")

    if "yahoo_tickers" not in st.session_state:
        st.session_state["yahoo_tickers"] = []

    # 1) Search box
    st.subheader("🔍 Cari Ticker / Simbol")
    keyword = st.text_input(
        "Ketik nama perusahaan atau kata kunci",
        placeholder="mis. bank central asia, tesla, emas, bitcoin",
    )
    if st.button("Cari Ticker", disabled=not keyword.strip()):
        with st.spinner(f"Mencari '{keyword}'..."):
            results = yahoo_finance.search_ticker(keyword.strip())
        if results:
            st.success(f"Ditemukan {len(results)} hasil:")
            for r in results:
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.write(f"**{r['symbol']}** — {r['nama']} *({r['exchange']} / {r['tipe']})*")
                with col2:
                    if st.button("➕ Tambah", key=f"add_{r['symbol']}"):
                        if r["symbol"] not in st.session_state["yahoo_tickers"]:
                            st.session_state["yahoo_tickers"].append(r["symbol"])
                            st.rerun()
        else:
            st.info("Tidak ditemukan ticker untuk kata kunci tersebut.")

    # 2) Pilih ticker
    st.subheader("📋 Ticker yang Dipilih")
    default_options = list(dict.fromkeys(DEFAULT_TICKERS + st.session_state["yahoo_tickers"]))
    selected = st.multiselect(
        "Pilih satu atau lebih ticker:",
        options=default_options,
        default=st.session_state["yahoo_tickers"] or ["BBCA.JK", "BBRI.JK", "USDIDR=X"],
    )

    custom_ticker = st.text_input("Atau ketik ticker langsung (pisahkan koma jika lebih dari satu):")
    if custom_ticker.strip():
        for t in [x.strip() for x in custom_ticker.split(",") if x.strip()]:
            if t not in selected:
                selected.append(t)

    # 3) Ambil data
    if selected:
        st.subheader("⚙️ Parameter Historis")
        col1, col2 = st.columns(2)
        with col1:
            period = st.selectbox("Rentang Waktu (Period)", ["1mo", "3mo", "6mo", "1y", "2y", "5y", "max"], index=3)
        with col2:
            interval = st.selectbox("Interval", ["1d", "1wk", "1mo"], index=0)

        if st.button("🚀 Ambil Data Historis", type="primary"):
            with st.spinner("Mengambil data dari Yahoo Finance..."):
                df_hist = yahoo_finance.get_multiple_tickers(selected, period=period, interval=interval)

            if not df_hist.empty:
                st.success(f"Berhasil mengambil {len(df_hist)} baris data untuk {len(selected)} ticker.")
                st.dataframe(df_hist.head(20), use_container_width=True)

                if "Close" in df_hist.columns and "ticker" in df_hist.columns:
                    st.subheader("Grafik Harga Penutupan (Close)")
                    pivot = df_hist.pivot(index="Date", columns="ticker", values="Close")
                    st.line_chart(pivot)

                download_buttons(df_hist, f"yahoo_finance_{period}_{interval}", "yf_hist")
                also_save_to_disk(save_to_disk, df_hist, "yahoo_finance_historis")
            else:
                st.error("Gagal mengambil data historis.")


# ---------------------------------------------------------------------------
# 3. Halaman: Kurs Bank Indonesia
# ---------------------------------------------------------------------------
elif page == "💱 Kurs Bank Indonesia":
    st.title("💱 Kurs Transaksi Bank Indonesia")
    st.write("Mengambil data kurs resmi harian via Web Service BI (`wskursbi.asmx`).")

    col1, col2, col3 = st.columns(3)
    with col1:
        mata_uang = st.selectbox(
            "Mata Uang",
            ["USD", "EUR", "JPY", "SGD", "AUD", "GBP", "CNY", "HKD", "MYR", "SAR"],
            index=0,
        )
    with col2:
        tgl_akhir = st.date_input("Tanggal Akhir", value=date.today())
    with col3:
        tgl_awal = st.date_input("Tanggal Awal", value=date.today() - timedelta(days=30))

    if tgl_awal > tgl_akhir:
        st.error("Tanggal awal tidak boleh lebih besar dari tanggal akhir.")
    else:
        if st.button("🚀 Ambil Data Kurs BI", type="primary"):
            with st.spinner(f"Mengambil kurs {mata_uang} dari BI..."):
                df_kurs = bi_kurs.get_kurs_range(mata_uang, tgl_awal, tgl_akhir)

            if not df_kurs.empty:
                st.success(f"Berhasil mengambil {len(df_kurs)} baris data kurs {mata_uang}.")
                st.dataframe(df_kurs, use_container_width=True)

                st.subheader(f"Grafik Kurs {mata_uang} (Jual vs Beli)")
                chart_df = df_kurs.set_index("tanggal")[["kurs_jual", "kurs_beli"]]
                st.line_chart(chart_df)

                download_buttons(df_kurs, f"bi_kurs_{mata_uang}_{tgl_awal}_{tgl_akhir}", "bi_kurs")
                also_save_to_disk(save_to_disk, df_kurs, f"bi_kurs_{mata_uang}")
            else:
                st.warning(
                    "Tidak ada data ditemukan untuk rentang tanggal ini. "
                    "Catatan: BI tidak merilis kurs di akhir pekan / hari libur nasional."
                )


# ---------------------------------------------------------------------------
# 4. Halaman: BI-Rate
# ---------------------------------------------------------------------------
elif page == "🏦 BI-Rate":
    st.title("🏦 Suku Bunga Acuan (BI-Rate / BI7DRR)")
    st.write("Mengambil suku bunga acuan terkini & histori dari situs resmi Bank Indonesia.")

    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("📌 Ambil BI-Rate Terkini"):
            with st.spinner("Mengambil data terkini..."):
                rate = bi_rate.get_current_bi_rate()
            if rate is not None:
                st.metric("BI-Rate Terkini", f"{rate:.2f} %")
            else:
                st.error("Gagal mengambil BI-Rate terkini dari situs BI.")

    with col2:
        if st.button("📜 Ambil Histori BI-Rate", type="primary"):
            with st.spinner("Mengambil tabel histori dari BI..."):
                df_rate = bi_rate.get_bi_rate_history()

            if not df_rate.empty:
                st.success(f"Berhasil mengambil {len(df_rate)} catatan histori BI-Rate.")
                st.dataframe(df_rate, use_container_width=True)

                if "tanggal" in df_rate.columns and "bi_rate_persen" in df_rate.columns:
                    chart_df = df_rate.sort_values("tanggal").set_index("tanggal")[["bi_rate_persen"]]
                    st.line_chart(chart_df)

                download_buttons(df_rate, "bi_rate_histori", "bi_rate")
                also_save_to_disk(save_to_disk, df_rate, "bi_rate_histori")
            else:
                st.warning("Gagal mengambil tabel histori atau halaman BI sedang tidak merespons.")


# ---------------------------------------------------------------------------
# 5. Halaman: Statistik OJK
# ---------------------------------------------------------------------------
elif page == "📑 Statistik OJK":
    st.title("📑 Statistik Sektor Keuangan (OJK)")
    st.write("Pindai dan unduh laporan resmi Statistik Perbankan, Syariah, IKNB, dan Pasar Modal.")

    available_sources = ojk_stats.list_categories()
    category_options = {src["label"]: key for key, src in available_sources.items()}

    selected_labels = st.multiselect(
        "Pilih Kategori Laporan OJK:",
        list(category_options.keys()),
        default=list(category_options.keys()),
    )
    selected_keys = [category_options[label] for label in selected_labels]

    keyword = st.text_input(
        "Filter kata kunci judul laporan (opsional)",
        placeholder="mis. Statistik Perbankan, Januari 2025, Triwulan, Syariah, dst",
    )

    if st.button("🔍 Cari Laporan OJK", type="primary", disabled=not selected_keys):
        with st.spinner(f"Memindai {len(selected_keys)} kanal OJK..."):
            reports = ojk_stats.search_reports_multi(keyword.strip() or None, selected_keys)
        st.session_state["ojk_reports"] = reports

    reports = st.session_state.get("ojk_reports", [])
    if reports:
        st.success(f"Ditemukan {len(reports)} laporan OJK.")
        df_reports = pd.DataFrame(reports)
        st.dataframe(df_reports, use_container_width=True)

        st.subheader("Unduh File Laporan")
        for i, r in enumerate(reports[:15]):  # limit 15 di UI
            col1, col2 = st.columns([4, 1])
            with col1:
                st.write(f"**({r['tipe_file'].upper()})** {r['judul']}  \n*Kategori: {r.get('kategori', '-')}*")
            with col2:
                if st.button("Unduh", key=f"ojk_dl_{i}"):
                    with st.spinner("Mengunduh..."):
                        path = ojk_stats.download_report(r)
                    if path:
                        st.success(f"Tersimpan di `{path}`")
                    else:
                        st.error("Gagal mengunduh file.")
    elif "ojk_reports" in st.session_state:
        st.info("Tidak ada laporan ditemukan untuk filter tersebut.")

