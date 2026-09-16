#!/usr/bin/env python3
"""
app_analytics.py
================
Aplikasi Web Streamlit: Dashboard Analitik Finansial & Makroekonomi Indonesia.
(Fokus Artikel 2: Data Analytics / Macroeconomic Transmission & Equity Risk)

Menganalisis:
1. Suku Bunga Acuan (BI-Rate) & Fluktuasi Kurs Valas (USD/IDR)
2. Kesehatan Industri Perbankan Nasional (OJK SPI: Kredit, DPK, LDR, NPL, CAR)
3. Kinerja Saham & Valuasi Portofolio (Bebas / Tanpa Batasan Ticker)

Cara Menjalankan:
    streamlit run app_analytics.py \\ ini jangan lupa
"""

import logging
import pandas as pd
import streamlit as st

from analytics import macro_banking_engine
from utils.storage import df_to_excel_bytes

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(message)s")
logger = logging.getLogger("app_analytics")

st.set_page_config(
    page_title="Dashboard Analitik Makro & Saham Perbankan",
    page_icon="📈",
    layout="wide",
)


# ---------------------------------------------------------------------------
# Helper Download UI
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


# ---------------------------------------------------------------------------
# Header & Pengantar
# ---------------------------------------------------------------------------
st.title("📈 Financial & Macroeconomic Intelligence Dashboard")
st.markdown(
    """
    **Studi Analitis Transmisi Makroekonomi & Risiko Pasar Finansial Indonesia**  
    Dashboard ini meneliti keterkaitan dinamika kebijakan moneter Bank Indonesia (**BI-Rate**), 
    fluktuasi nilai tukar valas (**Kurs USD/IDR**), kondisi intermediasi perbankan (**OJK SPI**), 
    dan performa saham/aset pasar modal.
    """
)

# ---------------------------------------------------------------------------
# Sidebar: Konfigurasi Ticker & Parameter Analisis (Bebas Tanpa Batasan)
# ---------------------------------------------------------------------------
st.sidebar.title("⚙️ Kontrol Analisis")
st.sidebar.caption("Artikel 2: Financial Analytics & Storytelling")

st.sidebar.markdown("### 🏛️ Pilihan Preset Cepat:")
if "analytics_tickers" not in st.session_state:
    st.session_state["analytics_tickers"] = "BBRI.JK, BMRI.JK, BBNI.JK, BBCA.JK, BNGA.JK, BRIS.JK"

col_sb1, col_sb2 = st.sidebar.columns(2)
with col_sb1:
    if st.button("🏛️ 3 Pilar Lengkap", use_container_width=True):
        st.session_state["analytics_tickers"] = "BBRI.JK, BMRI.JK, BBNI.JK, BBTN.JK, BBCA.JK, BNGA.JK, BDMN.JK, NISP.JK, BRIS.JK, BTPS.JK"
        st.rerun()
    if st.button("The Big 4", use_container_width=True):
        st.session_state["analytics_tickers"] = "BBCA.JK, BBRI.JK, BMRI.JK, BBNI.JK"
        st.rerun()
    if st.button("Bluechip Non-Bank", use_container_width=True):
        st.session_state["analytics_tickers"] = "BBCA.JK, ASII.JK, TLKM.JK, BMRI.JK"
        st.rerun()
with col_sb2:
    if st.button("BUMN vs Swasta", use_container_width=True):
        st.session_state["analytics_tickers"] = "BBRI.JK, BMRI.JK, BBNI.JK, BBTN.JK, BBCA.JK, BNGA.JK, BDMN.JK, NISP.JK"
        st.rerun()
    if st.button("Bank Syariah Focus", use_container_width=True):
        st.session_state["analytics_tickers"] = "BRIS.JK, BTPS.JK, BBCA.JK, BMRI.JK"
        st.rerun()
    if st.button("Multi-Aset Global", use_container_width=True):
        st.session_state["analytics_tickers"] = "BBCA.JK, ^JKSE, GC=F, CL=F"
        st.rerun()

st.sidebar.markdown("---")
ticker_input = st.sidebar.text_area(
    "Daftar Ticker yang Dianalisis (Pisahkan Koma):",
    value=st.session_state["analytics_tickers"],
    height=80,
    help="Bebas memasukkan kode ticker Yahoo Finance apa saja tanpa batasan. Contoh: BBCA.JK, BRIS.JK, ASII.JK, AAPL, BTC-USD, GC=F",
)
st.session_state["analytics_tickers"] = ticker_input

selected_period = st.sidebar.selectbox(
    "Rentang Waktu Historis:",
    options=["1mo", "3mo", "6mo", "1y", "2y", "5y", "max"],
    index=3,
)

with st.sidebar.expander("🛠️ Pengaturan Benchmark & Valas", expanded=False):
    benchmark_ticker = st.text_input("Ticker Acuan (Benchmark):", value="^JKSE").strip().upper()
    fx_ticker = st.text_input("Ticker Valas Pembanding:", value="USDIDR=X").strip().upper()

st.sidebar.markdown("---")
st.sidebar.caption(
    "💡 Untuk mengambil/memperbarui data mentah via scraper, jalankan: `streamlit run app_scraper.py`"
)

# Parse tickers
selected_assets = [t.strip().upper() for t in ticker_input.split(",") if t.strip()]

if not selected_assets:
    st.warning("Silakan masukkan minimal satu kode ticker pada panel sidebar di sebelah kiri.")
    st.stop()

# ---------------------------------------------------------------------------
# Data Loading & Processing
# ---------------------------------------------------------------------------
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
    ojk_segment_df = macro_banking_engine.load_ojk_segment_df()
    ojk_sharia_df = macro_banking_engine.load_ojk_sharia_df()
    metrics_df = macro_banking_engine.calculate_portfolio_metrics(market_df, benchmark_col=benchmark_ticker)
    macro_merged = macro_banking_engine.build_monthly_macro_merged_df(market_df)
    pillar_indices_df = macro_banking_engine.calculate_three_pillar_indices(market_df, benchmark_col=benchmark_ticker)
    pillar_summary_df = macro_banking_engine.calculate_pillar_summary(metrics_df)
    insights = macro_banking_engine.generate_executive_insights(
        metrics_df, macro_merged, benchmark_col=benchmark_ticker, fx_col=fx_ticker
    )

if market_df.empty:
    st.error("Gagal memuat data pasar untuk ticker yang dimasukkan. Periksa koneksi internet atau ejaan ticker.")
    st.stop()

# ---------------------------------------------------------------------------
# 1. KPI Cards
# ---------------------------------------------------------------------------
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

# ---------------------------------------------------------------------------
# 2. Executive Storytelling & Strategic Takeaways
# ---------------------------------------------------------------------------
st.subheader("💡 Executive Summary & Strategic Takeaways")
for ins in insights:
    st.markdown(f"- {ins}")

st.markdown("---")

# ---------------------------------------------------------------------------
# 3. Interactive Visualization Tabs
# ---------------------------------------------------------------------------
tab0, tab1, tab2, tab3, tab4 = st.tabs([
    "🏛️ 3 Pilar: BUMN vs Swasta vs Syariah",
    "📊 Performa Relatif Aset",
    "💱 Aset vs Kurs Valas",
    "🔗 Matriks Korelasi & Sensitivitas",
    "🏦 Fundamental Industri OJK",
])

with tab0:
    st.write("### 🏛️ Komparasi Strategis: Bank BUMN vs Swasta vs Syariah")
    st.caption(
        "Menelaah perbedaan struktural, mandat bisnis, profil risiko, dan dinamika performa antara 3 pilar perbankan Indonesia."
    )

    # Mandate & Storytelling Cards
    col_p1, col_p2, col_p3 = st.columns(3)
    with col_p1:
        st.markdown(
            """
            <div style="border-left: 4px solid #1f77b4; padding: 12px 16px; background-color: rgba(31, 119, 180, 0.08); border-radius: 6px;">
                <h4 style="margin: 0; color: #1f77b4;">🏛️ Bank BUMN (Persero)</h4>
                <p style="margin: 6px 0 0 0; font-size: 0.9em;"><b>Mandat:</b> <i>Agent of Development</i></p>
                <p style="font-size: 0.85em; color: #444; line-height: 1.4;">
                    Menguasai ~46% pangsa aset nasional. Bertugas menyalurkan program pemerintah (KUR, KPR subsidi BBTN, sindikasi infrastruktur). 
                    <br><b>Sensitivitas Moneter:</b> Biaya dana (CoF) relatif lebih sensitif saat BI-Rate naik karena persaingan likuiditas deposito korporasi & institusi.
                </p>
                <code style="font-size: 0.8em;">BBRI.JK, BMRI.JK, BBNI.JK, BBTN.JK</code>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col_p2:
        st.markdown(
            """
            <div style="border-left: 4px solid #2ca02c; padding: 12px 16px; background-color: rgba(44, 160, 44, 0.08); border-radius: 6px;">
                <h4 style="margin: 0; color: #2ca02c;">🏢 Bank Swasta (BUSN)</h4>
                <p style="margin: 6px 0 0 0; font-size: 0.9em;"><b>Mandat:</b> <i>Commercial & Profit Maximizer</i></p>
                <p style="font-size: 0.85em; color: #444; line-height: 1.4;">
                    Dipimpin oleh BBCA dengan dominasi ekosistem transaksi dan rasio dana murah (CASA > 80%). Efisiensi operasional sangat tinggi (CIR rendah).
                    <br><b>Sensitivitas Moneter:</b> Kualitas aset sangat konservatif (NPL rendah), paling defensif terhadap pelemahan Rupiah & volatilitas pasar modal.
                </p>
                <code style="font-size: 0.8em;">BBCA.JK, BNGA.JK, BDMN.JK, NISP.JK</code>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col_p3:
        st.markdown(
            """
            <div style="border-left: 4px solid #ff7f0e; padding: 12px 16px; background-color: rgba(255, 127, 14, 0.08); border-radius: 6px;">
                <h4 style="margin: 0; color: #ff7f0e;">🌙 Bank Syariah</h4>
                <p style="margin: 6px 0 0 0; font-size: 0.9em;"><b>Mandat:</b> <i>Ethical & Profit-Sharing Banking</i></p>
                <p style="font-size: 0.85em; color: #444; line-height: 1.4;">
                    Beroperasi bebas bunga berdasarkan akad jual-beli margin tetap (Murabahah) dan bagi hasil (Mudharabah/Musyarakah).
                    <br><b>Sensitivitas Moneter:</b> Margin pembiayaan lebih tahan banting terhadap lonjakan suku bunga acuan. Laju pertumbuhan volume DPK & pembiayaan konsisten dua digit (>12% YoY).
                </p>
                <code style="font-size: 0.8em;">BRIS.JK, BTPS.JK</code>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # Chart 1: Performa Saham Kumulatif Indeks Gabungan per Pilar
    st.write("#### 📈 Kinerja Saham Kumulatif: Indeks BUMN vs Swasta vs Syariah (Base = 100)")
    st.caption("Indeks dihitung dari rata-rata harga saham ter-normalisasi (Base 100) masing-masing pilar yang ada dalam dataset.")
    if not pillar_indices_df.empty:
        st.line_chart(pillar_indices_df)
    else:
        st.info("Masukkan ticker saham bank untuk menampilkan perbandingan indeks pilar.")

    # Rangkuman Kinerja & Profil Risiko Agregat per Pilar
    if not pillar_summary_df.empty:
        st.write("#### 📊 Rangkuman Kinerja & Profil Risiko Agregat per Pilar")
        st.dataframe(pillar_summary_df, use_container_width=True, hide_index=True)

    st.markdown("---")

    # Chart 2 & 3: Fundamental OJK SPI & SPS
    st.write("#### 🏛️ Komparasi Fundamental Intermediasi & Kualitas Aset (OJK SPI & SPS)")
    st.caption("Data resmi Otoritas Jasa Keuangan (Statistik Perbankan Indonesia & Statistik Perbankan Syariah).")

    f_col1, f_col2 = st.columns(2)
    with f_col1:
        st.write("##### 1. Kualitas Kredit & Pembiayaan: NPL BUMN vs NPL Swasta vs NPF Syariah (%)")
        if not ojk_segment_df.empty and not ojk_sharia_df.empty:
            merged_credit = pd.merge(
                ojk_segment_df[["periode", "npl_bumn_pct", "npl_swasta_pct"]],
                ojk_sharia_df[["periode", "npf_gross_pct"]],
                on="periode",
                how="inner",
            ).rename(columns={
                "npl_bumn_pct": "NPL Bank BUMN (%)",
                "npl_swasta_pct": "NPL Bank Swasta (%)",
                "npf_gross_pct": "NPF Bank Syariah (%)",
            }).set_index("periode")
            st.line_chart(merged_credit)
            st.caption(
                "💡 **Insight Analis:** NPL Bank Swasta (~2.0%) dan NPF Syariah (~2.0%) relatif lebih rendah dibanding BUMN (~2.3% - 2.5%) "
                "karena bank BUMN memikul porsi besar restrukturisasi kredit program dan penugasan UMKM."
            )

    with f_col2:
        st.write("##### 2. Intermediasi Likuiditas: LDR BUMN vs LDR Swasta vs FDR Syariah (%)")
        if not ojk_segment_df.empty and not ojk_sharia_df.empty:
            merged_ldr = pd.merge(
                ojk_segment_df[["periode", "ldr_bumn_pct", "ldr_swasta_pct"]],
                ojk_sharia_df[["periode", "fdr_pct"]],
                on="periode",
                how="inner",
            ).rename(columns={
                "ldr_bumn_pct": "LDR Bank BUMN (%)",
                "ldr_swasta_pct": "LDR Bank Swasta (%)",
                "fdr_pct": "FDR Bank Syariah (%)",
            }).set_index("periode")
            st.line_chart(merged_ldr)
            st.caption(
                "💡 **Insight Analis:** LDR Bank BUMN bertahan tinggi di kisaran ~87%, mencerminkan ekspansi kredit pembangunan. "
                "Financing to Deposit Ratio (FDR) syariah berada di tingkat optimal 82% - 86%."
            )

    # Chart 4: Volume Pertumbuhan Industri Syariah
    st.write("##### 3. Pertumbuhan Volume Industri Syariah: Pembiayaan vs DPK (Triliun IDR)")
    if not ojk_sharia_df.empty:
        sharia_vol = ojk_sharia_df[["periode", "pembiayaan_triliun", "dpk_syariah_triliun"]].rename(columns={
            "pembiayaan_triliun": "Pembiayaan Syariah (Rp T)",
            "dpk_syariah_triliun": "DPK Syariah (Rp T)",
        }).set_index("periode")
        st.bar_chart(sharia_vol)
        st.caption(
            "💡 **Insight Analis:** Industri syariah mengalami akselerasi pembiayaan melampaui Rp 680 Triliun "
            "dan penghimpunan DPK melewati Rp 770 Triliun, membuktikan potensi penetrasi perbankan syariah yang terus meningkat."
        )

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
        st.info("Tidak ada data aset yang cocok untuk dibandingkan.")

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

# ---------------------------------------------------------------------------
# 4. Financial Risk & Performance Matrix
# ---------------------------------------------------------------------------
st.markdown("---")
st.subheader("📋 Matriks Risiko & Kinerja Portofolio")
st.dataframe(metrics_df, use_container_width=True, hide_index=True)

download_buttons(metrics_df, f"matriks_analisis_perbankan_{selected_period}", "analytics_metrics")

