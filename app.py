#!/usr/bin/env python3
"""
app.py
======
Aplikasi web (Streamlit) untuk Scraper Data Finansial & Makroekonomi Publik
(Bank Indonesia / OJK / Yahoo Finance).

Ini adalah antarmuka web di atas modul-modul scraper yang sama persis
dengan versi CLI (main.py) - tidak ada duplikasi logic scraping.

Cara menjalankan:
    streamlit run app.py

Lalu buka browser ke alamat yang ditampilkan (biasanya http://localhost:8501)
"""

import logging
from datetime import date, timedelta

import pandas as pd
import streamlit as st

from config import DEFAULT_TICKERS
from scrapers import yahoo_finance, bi_kurs, bi_rate, ojk_stats
from utils.storage import save_all, save_csv, df_to_excel_bytes
from analytics import macro_banking_engine

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(message)s")
logger = logging.getLogger("app")

st.set_page_config(
    page_title="Scraper Data Finansial & Makroekonomi",
    page_icon="📊",
    layout="wide",
)


# ---------------------------------------------------------------------------
# Helper UI kecil
# ---------------------------------------------------------------------------
def download_buttons(df: pd.DataFrame, base_name: str, key_prefix: str):
    """Tampilkan tombol download CSV & Excel untuk sebuah DataFrame, tanpa
    menampilkan error kalau df kosong."""
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
st.sidebar.title("📊 Menu Utama")
page = st.sidebar.radio(
    "Pilih modul",
    [
        "🏠 Beranda",
        "📈 Analisis Makro & Bank",
        "💹 Yahoo Finance",
        "💱 Kurs Bank Indonesia",
        "🏦 BI-Rate",
        "📑 Statistik OJK",
    ],
)

save_to_disk = st.sidebar.checkbox(
    "Simpan hasil ke folder data/ juga (CSV & Excel)", value=True,
    help="Selain bisa didownload langsung dari browser, hasil juga disimpan ke disk seperti versi CLI."
)

st.sidebar.markdown("---")
st.sidebar.caption(
    "⚠️ Gunakan secara wajar. Data BI-Rate & OJK diambil lewat HTML scraping "
    "sehingga bisa gagal jika struktur halaman sumber berubah."
)


# ---------------------------------------------------------------------------
# Halaman: Beranda
# ---------------------------------------------------------------------------
if page == "🏠 Beranda":
    st.title("📊 Scraper Data Finansial & Makroekonomi Publik")
    st.markdown(
        """
        Selamat datang! Aplikasi ini mengambil data publik dari tiga sumber:

        | Sumber | Jenis Data | Metode |
        |---|---|---|
        | **Bank Indonesia** | Kurs Transaksi BI | Web service resmi (XML) |
        | **Bank Indonesia** | BI-Rate / BI7DRR | HTML scraping |
        | **OJK** | Statistik Perbankan (daftar & unduh laporan) | HTML scraping |
        | **Yahoo Finance** | Saham, indeks, kurs, komoditas | Library `yfinance` |

        Pilih sumber data di menu sebelah kiri untuk mulai mengambil data.
        Semua hasil bisa langsung didownload dari browser (CSV / Excel), dan
        opsional juga disimpan ke folder `data/` seperti versi command-line.

        ---
        💡 *Sekarang dilengkapi modul analitik: Pilih **📈 Analisis Makro & Bank** pada menu untuk melihat visualisasi korelasi dan metrik risiko terintegrasi.*
        """
    )


# ---------------------------------------------------------------------------
# Halaman: Analisis Makro & Portofolio Bank
# ---------------------------------------------------------------------------
elif page == "📈 Analisis Makro & Bank":
    st.title("📈 Analisis Makroekonomi & Kinerja Saham Perbankan")
    st.markdown(
        """
        Dashboard analitik portofolio ini mengintegrasikan **Suku Bunga Acuan (BI-Rate)**, 
        **Fluktuasi Kurs USD/IDR**, **Statistik Industri Perbankan OJK**, dan **Kinerja Saham *The Big 4 Banks* (BBCA, BBRI, BMRI, BBNI)**.
        """
    )

    # Filter parameter
    # -----------------------------------------------------------------------
    # Filter parameter (Bebas / Tanpa Batasan)
    # -----------------------------------------------------------------------
    st.subheader("⚙️ Konfigurasi Ticker & Parameter Analisis")

    # Preset shortcut buttons
    st.caption("Pilihan Cepat (Preset) atau ketik kode ticker apa saja secara bebas di bawah:")
    col_p1, col_p2, col_p3, col_p4 = st.columns(4)
    if "custom_tickers_input" not in st.session_state:
        st.session_state["custom_tickers_input"] = "BBCA.JK, BBRI.JK, BMRI.JK, BBNI.JK"

    with col_p1:
        if st.button("🏛️ The Big 4 Banks"):
            st.session_state["custom_tickers_input"] = "BBCA.JK, BBRI.JK, BMRI.JK, BBNI.JK"
            st.rerun()
    with col_p2:
        if st.button("📱 Bank Digital & Syariah"):
            st.session_state["custom_tickers_input"] = "BRIS.JK, ARTO.JK, BBTN.JK, BDMN.JK"
            st.rerun()
    with col_p3:
        if st.button("🏢 Bluechip Diversifikasi"):
            st.session_state["custom_tickers_input"] = "BBCA.JK, ASII.JK, TLKM.JK, BMRI.JK"
            st.rerun()
    with col_p4:
        if st.button("🌍 Multi-Aset & Komoditas"):
            st.session_state["custom_tickers_input"] = "BBCA.JK, ^JKSE, GC=F, CL=F"
            st.rerun()

    col_f1, col_f2 = st.columns([1, 2])
    with col_f1:
        selected_period = st.selectbox(
            "Pilih Rentang Waktu Historis",
            options=["1mo", "3mo", "6mo", "1y", "2y", "5y", "max"],
            index=3,
            help="Rentang historis data harga Yahoo Finance.",
        )
    with col_f2:
        ticker_input = st.text_input(
            "Kode Ticker yang Dianalisis (Pisahkan dengan koma):",
            value=st.session_state["custom_tickers_input"],
            help="Bebas memasukkan ticker apa saja (saham lokal .JK, saham US, indeks, kripto, komoditas). Contoh: BBCA.JK, BBRI.JK, BRIS.JK, ASII.JK, AAPL, BTC-USD",
        )
        st.session_state["custom_tickers_input"] = ticker_input
    # Konfigurasi lanjutan untuk Benchmark & Valas
    with st.expander("🛠️ Pengaturan Lanjutan (Benchmark Pasar & Kurs Valas)", expanded=False):
        col_adv1, col_adv2 = st.columns(2)
        with col_adv1:
            benchmark_ticker = st.text_input("Ticker Acuan Pasar (Benchmark):", value="^JKSE", help="Default: ^JKSE (IHSG). Bisa diubah mis. ^GSPC untuk S&P 500.").strip().upper()
        with col_adv2:
            fx_ticker = st.text_input("Ticker Kurs / Valas Pembanding:", value="USDIDR=X", help="Default: USDIDR=X (Kurs USD/IDR). Bisa diubah mis. EURIDR=X atau JPYIDR=X.").strip().upper()

    selected_assets = [t.strip().upper() for t in ticker_input.split(",") if t.strip()]

    if not selected_assets:
        st.warning("Silakan masukkan minimal satu kode ticker pada kotak input di atas.")
        st.stop()

    with st.spinner("Memuat dan mengolah data pasar, BI, dan OJK..."):
        extra_tickers = []
        if benchmark_ticker and benchmark_ticker not in selected_assets:
            extra_tickers.append(benchmark_ticker)
        if fx_ticker and fx_ticker not in selected_assets:
            extra_tickers.append(fx_ticker)

        all_tickers = selected_assets + extra_tickers
        market_df = macro_banking_engine.fetch_market_data(all_tickers, period=selected_period)
        bi_series = macro_banking_engine.load_bi_rate_series()
        ojk_df = macro_banking_engine.load_ojk_banking_df()
        metrics_df = macro_banking_engine.calculate_portfolio_metrics(market_df, benchmark_col=benchmark_ticker)
        macro_merged = macro_banking_engine.build_monthly_macro_merged_df(market_df)
        insights = macro_banking_engine.generate_executive_insights(
            metrics_df, macro_merged, benchmark_col=benchmark_ticker, fx_col=fx_ticker
        )

    if market_df.empty:
        st.error("Gagal memuat data pasar untuk ticker yang dimasukkan. Periksa kembali penulisan kode ticker atau koneksi internet.")
        st.stop()

    # -----------------------------------------------------------------------
    # 1. KPI Cards
    # -----------------------------------------------------------------------
    st.subheader("📌 Key Indicators Overview")
    kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)

    with kpi_col1:
        if not bi_series.empty:
            curr_bi = bi_series.iloc[-1]["bi_rate_persen"]
            prev_bi = bi_series.iloc[-2]["bi_rate_persen"] if len(bi_series) > 1 else curr_bi
            delta_bi = round(curr_bi - prev_bi, 2)
            st.metric("BI-Rate Terkini", f"{curr_bi:.2f}%", delta=f"{delta_bi:+.2f}%" if delta_bi != 0 else "Stabil")
        else:
            st.metric("BI-Rate Terkini", "-")

    with kpi_col2:
        if fx_ticker in market_df.columns:
            fx_curr = market_df[fx_ticker].dropna().iloc[-1]
            fx_prev = market_df[fx_ticker].dropna().iloc[-2] if len(market_df[fx_ticker].dropna()) > 1 else fx_curr
            delta_fx = round(fx_curr - fx_prev, 2)
            st.metric(f"Kurs ({fx_ticker})", f"{fx_curr:,.1f}", delta=f"{delta_fx:+,.1f}", delta_color="inverse")
        else:
            st.metric("Kurs Valas", "-")

    with kpi_col3:
        asset_metrics = metrics_df[metrics_df["Ticker"].isin(selected_assets)]
        if not asset_metrics.empty:
            top_a = asset_metrics.sort_values(by="Total Return (%)", ascending=False).iloc[0]
            st.metric("Top Performer Aset", top_a["Ticker"], delta=f"{top_a['Total Return (%)']:+.1f}% Return")
        else:
            st.metric("Top Performer Aset", "-")

    with kpi_col4:
        if not ojk_df.empty:
            latest_ldr = ojk_df.iloc[-1]["ldr_pct"]
            st.metric("LDR Industri (OJK)", f"{latest_ldr:.1f}%", help="Loan to Deposit Ratio nasional perbankan (zona aman < 92%)")
        else:
            st.metric("LDR Industri (OJK)", "-")

    st.markdown("---")

    # -----------------------------------------------------------------------
    # 2. Executive Storytelling & Insights
    # -----------------------------------------------------------------------
    st.subheader("💡 Executive Summary & Strategic Takeaways")
    for ins in insights:
        st.markdown(f"- {ins}")

    st.markdown("---")

    # -----------------------------------------------------------------------
    # 3. Interactive Visualization Tabs
    # -----------------------------------------------------------------------
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Performa Relatif Aset",
        "💱 Aset vs Kurs Valas",
        "🔗 Matriks Korelasi & Sensitivitas",
        "🏦 Fundamental Industri OJK",
    ])

    with tab1:
        st.write("### Normalized Performance (Base = 100)")
        st.caption(f"Membandingkan pertumbuhan kumulatif aset terpilih terhadap benchmark acuan ({benchmark_ticker}).")
        compare_cols = [b for b in selected_assets if b in market_df.columns]
        if benchmark_ticker in market_df.columns and benchmark_ticker not in compare_cols:
            compare_cols.append(benchmark_ticker)

        norm_df = market_df[compare_cols].dropna().copy()
        if not norm_df.empty:
            norm_indexed = (norm_df / norm_df.iloc[0]) * 100
            st.line_chart(norm_indexed)

    with tab2:
        st.write(f"### Dinamika Harga Aset vs Fluktuasi Kurs ({fx_ticker})")
        st.caption(f"Membandingkan arah pergerakan harga instrumen terhadap fluktuasi nilai tukar {fx_ticker}.")
        available_assets = [b for b in selected_assets if b in market_df.columns]
        if available_assets:
            focus_asset = st.selectbox(
                "Pilih Aset untuk Dibandingkan:",
                options=available_assets,
                format_func=lambda x: f"{x} - {macro_banking_engine.get_ticker_label(x)}",
            )
            if focus_asset in market_df.columns and fx_ticker in market_df.columns:
                chart_data = market_df[[focus_asset, fx_ticker]].dropna().copy()
                # Standarisasi nilai min-max (0-1) agar bisa ditampilkan berdampingan
                scaled = (chart_data - chart_data.min()) / (chart_data.max() - chart_data.min())
                st.line_chart(scaled)
                st.caption(f"Grafik di atas dinormalisasi (0 - 1) untuk membandingkan arah tren {focus_asset} vs {fx_ticker}.")
        else:
            st.info("Tidak ada data aset yang cocok untuk dibandingkan dengan kurs.")

    with tab3:
        st.write("### Matriks Korelasi Finansial")
        st.caption("Korelasi dihitung berdasarkan return harian. Nilai mendekati -1 berarti berlawanan arah, +1 berarti searah.")
        ret_df = market_df.pct_change().dropna(how="all")
        corr_matrix = ret_df.corr().round(2)
        st.dataframe(corr_matrix, use_container_width=True)

        if fx_ticker in market_df.columns:
            st.write(f"#### 30-Day Rolling Correlation: Aset vs {fx_ticker}")
            rolling_corr_df = pd.DataFrame()
            for b in selected_assets:
                if b in market_df.columns:
                    rolling_corr_df[b] = macro_banking_engine.calculate_rolling_correlation(market_df, b, fx_ticker, window=30)
            if not rolling_corr_df.empty:
                st.line_chart(rolling_corr_df.dropna())

    with tab4:
        st.write("### Statistik Industri Perbankan Nasional (OJK SPI)")
        col_ojk_a, col_ojk_b = st.columns(2)
        with col_ojk_a:
            st.write("#### Pertumbuhan Kredit & DPK (Triliun IDR)")
            ojk_growth = ojk_df[["periode", "kredit_triliun", "dpk_triliun"]].set_index("periode")
            st.line_chart(ojk_growth)
        with col_ojk_b:
            st.write("#### Rasio Kesehatan: NPL, CAR, dan LDR (%)")
            ojk_ratios = ojk_df[["periode", "npl_gross_pct", "car_pct", "ldr_pct"]].set_index("periode")
            st.line_chart(ojk_ratios)

    # -----------------------------------------------------------------------
    # 4. Financial Risk & Performance Matrix
    # -----------------------------------------------------------------------
    st.markdown("---")
    st.subheader("📋 Matriks Risiko & Kinerja Portofolio")
    st.dataframe(metrics_df, use_container_width=True, hide_index=True)

    download_buttons(metrics_df, f"matriks_analisis_perbankan_{selected_period}", "analytics_metrics")


# ---------------------------------------------------------------------------
# Halaman: Yahoo Finance
# ---------------------------------------------------------------------------
elif page == "💹 Yahoo Finance":
    st.title("💹 Yahoo Finance")
    st.write("Cari saham/indeks/aset apa saja pakai nama atau kata kunci, lalu ambil datanya.")

    # Daftar ticker yang sedang dipilih, disimpan di session agar tidak
    # hilang saat halaman rerun (mis. setelah klik tombol).
    if "yahoo_tickers" not in st.session_state:
        st.session_state["yahoo_tickers"] = []

    # -------------------------------------------------------------
    # 1) Cari ticker berdasarkan keyword bebas
    # -------------------------------------------------------------
    st.subheader("🔍 Cari Saham/Aset")
    keyword = st.text_input(
        "Ketik nama perusahaan atau kata kunci",
        placeholder="mis. bank central asia, tesla, emas, bitcoin",
    )
    if st.button("Cari", disabled=not keyword.strip()):
        with st.spinner(f"Mencari '{keyword}'..."):
            st.session_state["yahoo_search_results"] = yahoo_finance.search_ticker(keyword)

    search_results = st.session_state.get("yahoo_search_results", [])
    if keyword.strip() and "yahoo_search_results" in st.session_state:
        if not search_results:
            st.info("Tidak ada hasil ditemukan untuk kata kunci tersebut.")
        else:
            options = [
                f"{r['symbol']} — {r['nama']} ({r['exchange']}, {r['tipe']})"
                for r in search_results
            ]
            symbol_by_option = {opt: r["symbol"] for opt, r in zip(options, search_results)}
            chosen = st.multiselect("Hasil pencarian — pilih yang mau ditambahkan", options)
            if st.button("➕ Tambahkan ke daftar", disabled=not chosen):
                for opt in chosen:
                    sym = symbol_by_option[opt]
                    if sym not in st.session_state["yahoo_tickers"]:
                        st.session_state["yahoo_tickers"].append(sym)
                st.rerun()

    # -------------------------------------------------------------
    # 2) Tambah manual (kalau sudah tahu persis kode tickernya)
    # -------------------------------------------------------------
    with st.expander("➕ Atau tambahkan kode ticker langsung"):
        manual_input = st.text_input(
            "Kode ticker (pisahkan dengan koma)",
            placeholder="mis. BBCA.JK, ^JKSE, USDIDR=X",
            key="yahoo_manual_input",
        )
        if st.button("Tambah manual", disabled=not manual_input.strip()):
            for t in [x.strip().upper() for x in manual_input.split(",") if x.strip()]:
                if t not in st.session_state["yahoo_tickers"]:
                    st.session_state["yahoo_tickers"].append(t)
            st.rerun()

        st.caption("Atau muat cepat beberapa ticker populer Indonesia sebagai starting point:")
        if st.button("⭐ Muat ticker populer"):
            for t in DEFAULT_TICKERS:
                if t not in st.session_state["yahoo_tickers"]:
                    st.session_state["yahoo_tickers"].append(t)
            st.rerun()

    # -------------------------------------------------------------
    # 3) Daftar ticker yang sudah dipilih (bisa dihapus satu-satu)
    # -------------------------------------------------------------
    st.subheader("📌 Ticker Terpilih")
    tickers = st.session_state["yahoo_tickers"]
    if not tickers:
        st.info("Belum ada ticker dipilih. Cari dan tambahkan dari hasil pencarian di atas.")
    else:
        chip_cols = st.columns(min(len(tickers), 6) or 1)
        for i, t in enumerate(tickers):
            with chip_cols[i % len(chip_cols)]:
                if st.button(f"❌ {t}", key=f"remove_ticker_{t}", help="Hapus dari daftar"):
                    st.session_state["yahoo_tickers"].remove(t)
                    st.rerun()
        if st.button("🗑️ Bersihkan semua"):
            st.session_state["yahoo_tickers"] = []
            st.rerun()

    col1, col2 = st.columns(2)
    with col1:
        period = st.selectbox("Periode", ["1mo", "3mo", "6mo", "1y", "2y", "5y", "max"], index=2)
    with col2:
        interval = st.selectbox("Interval", ["1d", "1wk", "1mo"], index=0)

    if st.button("🚀 Ambil Data Yahoo Finance", type="primary", disabled=not tickers):
        with st.spinner(f"Mengambil data untuk {len(tickers)} ticker..."):
            df_hist = yahoo_finance.get_multiple_tickers(tickers, period=period, interval=interval)
            df_quote = yahoo_finance.get_latest_quotes_multi(tickers)

        if df_hist.empty:
            st.error("Data historis kosong. Cek kode ticker atau koneksi internet.")
        else:
            st.success(f"Berhasil mengambil {len(df_hist)} baris data historis.")
            st.subheader("Kuotasi Terkini")
            st.dataframe(df_quote, use_container_width=True)
            download_buttons(df_quote, "yahoo_finance_kuotasi_terkini", "yahoo_quote")

            st.subheader("Data Historis")
            st.dataframe(df_hist, use_container_width=True)
            download_buttons(df_hist, "yahoo_finance_historis", "yahoo_hist")

            # Grafik ringkas per ticker (kolom Close)
            if "Close" in df_hist.columns and "Date" in df_hist.columns:
                st.subheader("Grafik Harga Penutupan (Close)")
                pivot = df_hist.pivot_table(index="Date", columns="ticker", values="Close")
                st.line_chart(pivot)

            also_save_to_disk(save_to_disk, df_hist, "yahoo_finance_historis")
            also_save_to_disk(save_to_disk, df_quote, "yahoo_finance_kuotasi_terkini")

# ---------------------------------------------------------------------------
# Halaman: Kurs Bank Indonesia
# ---------------------------------------------------------------------------
elif page == "💱 Kurs Bank Indonesia":
    st.title("💱 Kurs Transaksi Bank Indonesia")
    st.write("Data resmi dari web service BI (`wskursbi.asmx`).")

    currency_input = st.text_input(
        "Kode mata uang (pisahkan dengan koma)", value="USD, EUR, JPY"
    )
    currency_codes = [c.strip().upper() for c in currency_input.split(",") if c.strip()]

    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Tanggal awal", value=date.today() - timedelta(days=30))
    with col2:
        end_date = st.date_input("Tanggal akhir", value=date.today())

    if st.button("🚀 Ambil Data Kurs BI", type="primary", disabled=not currency_codes):
        if start_date > end_date:
            st.error("Tanggal awal tidak boleh setelah tanggal akhir.")
        else:
            with st.spinner(f"Mengambil kurs untuk {', '.join(currency_codes)}..."):
                df = bi_kurs.get_kurs_multi_currency(
                    currency_codes, start_date.isoformat(), end_date.isoformat()
                )

            if df.empty:
                st.error(
                    "Data kosong. Kemungkinan rentang tanggal libur, kode mata uang "
                    "tidak valid, atau web service BI sedang bermasalah."
                )
            else:
                st.success(f"Berhasil mengambil {len(df)} baris data kurs.")
                st.dataframe(df, use_container_width=True)
                download_buttons(df, "bi_kurs_transaksi", "bi_kurs")

                if "tanggal" in df.columns and "kurs_jual" in df.columns:
                    st.subheader("Grafik Kurs Jual")
                    pivot_col = "mata_uang" if "mata_uang" in df.columns else None
                    if pivot_col:
                        pivot = df.pivot_table(index="tanggal", columns=pivot_col, values="kurs_jual")
                        st.line_chart(pivot)

                also_save_to_disk(save_to_disk, df, "bi_kurs_transaksi")

# ---------------------------------------------------------------------------
# Halaman: BI-Rate
# ---------------------------------------------------------------------------
elif page == "🏦 BI-Rate":
    st.title("🏦 BI-Rate / BI7DRR")
    st.write("Suku bunga acuan Bank Indonesia. Diambil dengan HTML scraping (bukan API resmi).")

    if st.button("🚀 Ambil Data BI-Rate", type="primary"):
        with st.spinner("Mengambil BI-Rate terkini..."):
            terkini = bi_rate.get_bi_rate_terkini()

        st.subheader("BI-Rate Terkini")
        if terkini.get("nilai_persen") is not None:
            tanggal_label = None
            if terkini.get("tanggal") is not None:
                tanggal_label = pd.Timestamp(terkini["tanggal"]).strftime("%d %B %Y")
            st.metric(
                "BI-Rate" + (f" (per {tanggal_label})" if tanggal_label else ""),
                f"{terkini['nilai_persen']}%",
            )
        else:
            st.warning("Nilai terkini tidak berhasil di-parse otomatis dari halaman BI.")
        with st.expander("Detail mentah"):
            st.json({k: str(v) for k, v in terkini.items()})

        with st.spinner("Mengambil histori BI-Rate..."):
            df_hist = bi_rate.get_bi_rate_history()

        st.subheader("Histori BI-Rate")
        if df_hist.empty:
            st.warning(
                "Histori BI-Rate tidak berhasil diambil otomatis (struktur halaman BI mungkin "
                "berubah). Gunakan nilai terkini di atas, atau lengkapi data secara manual."
            )
        else:
            st.dataframe(df_hist, use_container_width=True)
            download_buttons(df_hist, "bi_rate_histori", "bi_rate_hist")
            also_save_to_disk(save_to_disk, df_hist, "bi_rate_histori")

# ---------------------------------------------------------------------------
# Halaman: Statistik OJK
# ---------------------------------------------------------------------------
elif page == "📑 Statistik OJK":
    st.title("📑 Statistik OJK")
    st.write("Cari & unduh laporan statistik (xlsx/pdf) dari beberapa kanal resmi OJK sekaligus.")

    st.info(
        "⚠️ Sejak Juli 2025, data OJK yang lebih baru dipindah ke portal "
        "[data.ojk.go.id/SJKPublic](https://data.ojk.go.id/SJKPublic). Halaman "
        "yang di-scrape di sini hanya menyimpan **arsip laporan sebelum Juli 2025**."
    )

    categories = ojk_stats.list_categories()

    with st.expander("ℹ️ Data apa saja yang bisa ditarik dari sini?"):
        for key, src in categories.items():
            st.markdown(f"**{src['label']}**  \n{src['keterangan']}")

    category_options = {src["label"]: key for key, src in categories.items()}
    selected_labels = st.multiselect(
        "Pilih kategori/kanal OJK yang mau dicari",
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
        st.success(f"Ditemukan {len(reports)} laporan.")
        df_reports = pd.DataFrame(reports)
        st.dataframe(df_reports, use_container_width=True)

        st.subheader("Unduh Laporan")
        for i, r in enumerate(reports):
            col1, col2 = st.columns([4, 1])
            with col1:
                st.write(f"**({r['tipe_file']})** {r['judul']}  \n*Kategori: {r.get('kategori', '-')}*")
            with col2:
                if st.button("Unduh", key=f"ojk_dl_{i}"):
                    with st.spinner("Mengunduh..."):
                        path = ojk_stats.download_report(r)
                    if path:
                        with open(path, "rb") as f:
                            st.download_button(
                                "⬇️ Simpan file",
                                data=f.read(),
                                file_name=path.split("/")[-1],
                                key=f"ojk_save_{i}",
                            )
                    else:
                        st.error("Gagal mengunduh file ini.")
    elif "ojk_reports" in st.session_state:
        st.info("Tidak ada laporan ditemukan untuk filter tersebut. Coba kata kunci lain atau kategori berbeda.")
