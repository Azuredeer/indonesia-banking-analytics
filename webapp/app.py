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
st.sidebar.title("📊 Menu Scraper")
page = st.sidebar.radio(
    "Pilih sumber data",
    ["🏠 Beranda", "💹 Yahoo Finance", "💱 Kurs Bank Indonesia", "🏦 BI-Rate", "📑 Statistik OJK"],
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
        💡 *Tahap ini fokus di scraping. Modul analisa & visualisasi data
        bisa ditambahkan belakangan di atas fondasi yang sama.*
        """
    )

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
    st.title("🏦 BI-Rate (BI 7-Day Reverse Repo Rate)")

    with st.expander("ℹ️ Apa itu BI-Rate & kenapa datanya penting?", expanded=True):
        st.markdown(
            """
            **BI-Rate** (dulu disebut BI 7-Day Reverse Repo Rate/BI7DRR) adalah
            **suku bunga acuan/kebijakan moneter** yang ditetapkan Bank Indonesia
            lewat Rapat Dewan Gubernur (RDG), biasanya bulanan.

            **Fungsinya:**
            - Jadi sinyal arah kebijakan moneter BI (ketat/longgar) untuk
              menjaga stabilitas nilai Rupiah & mengendalikan inflasi.
            - Jadi **acuan** suku bunga deposito, kredit/pinjaman bank, obligasi,
              dan berbagai instrumen keuangan lain di Indonesia.
            - **BI-Rate naik** → biasanya bunga kredit/deposito bank ikut naik,
              rupiah cenderung menguat, tapi likuiditas & pertumbuhan kredit
              bisa melambat.
            - **BI-Rate turun** → biasanya mendorong kredit & konsumsi (bunga
              lebih murah), tapi bisa menekan nilai tukar Rupiah.

            **Kegunaan untuk analisis:**
            - Bandingkan tren BI-Rate dengan pergerakan **kurs USD/IDR** (menu
              Kurs Bank Indonesia) atau **IHSG/saham perbankan** (menu Yahoo
              Finance) untuk melihat korelasi kebijakan moneter terhadap pasar.
            - Lihat **frekuensi & arah perubahan** (naik/turun/tetap) sebagai
              indikator siklus kebijakan moneter.

            📖 Baca lebih lanjut: [Apa Itu BI-Rate (bi.go.id)](https://www.bi.go.id/id/fungsi-utama/moneter/bi-rate/default.aspx)
            """
        )

    st.caption(
        "⚠️ Karena tabel di halaman BI dipaginasi dengan JavaScript, scraping HTML "
        "polos hanya bisa mengambil **±10 data histori terbaru** dari halaman pertama."
    )

    if st.button("🚀 Ambil Data BI-Rate", type="primary"):
        with st.spinner("Mengambil histori BI-Rate..."):
            df_hist = bi_rate.get_bi_rate_history()
        st.session_state["bi_rate_hist"] = df_hist

    df_hist = st.session_state.get("bi_rate_hist")

    if df_hist is None:
        st.info("Klik tombol di atas untuk mengambil data.")
    elif df_hist.empty:
        st.warning(
            "Histori BI-Rate tidak berhasil diambil otomatis (struktur halaman BI mungkin "
            "berubah). Coba lagi beberapa saat, atau lengkapi data secara manual dari "
            "siaran pers RDG BI."
        )
    else:
        # -----------------------------------------------------------
        # Ringkasan: nilai terkini + arah perubahan vs periode sebelumnya
        # -----------------------------------------------------------
        terkini = df_hist.iloc[0]
        tanggal_label = bi_rate.format_tanggal_indonesia(terkini["tanggal"])

        col1, col2, col3 = st.columns(3)
        with col1:
            delta = None
            if len(df_hist) > 1:
                delta = round(terkini["bi_rate_persen"] - df_hist.iloc[1]["bi_rate_persen"], 2)
            st.metric(
                f"BI-Rate Terkini (per {tanggal_label})",
                f"{terkini['bi_rate_persen']}%",
                delta=f"{delta:+.2f} pp vs RDG sebelumnya" if delta is not None else None,
                delta_color="inverse",  # kenaikan suku bunga = kebijakan lebih ketat
            )
        with col2:
            st.metric("Data Histori Tersedia", f"{len(df_hist)} periode RDG")
        with col3:
            n_naik = (df_hist["bi_rate_persen"].diff(-1) > 0).sum()
            n_turun = (df_hist["bi_rate_persen"].diff(-1) < 0).sum()
            st.metric("Naik / Turun (dalam data ini)", f"{n_naik} naik, {n_turun} turun")

        # -----------------------------------------------------------
        # Tabel histori + kolom arah perubahan supaya langsung kebaca
        # -----------------------------------------------------------
        df_display = df_hist.copy()
        df_display["perubahan_pp"] = -df_display["bi_rate_persen"].diff(-1)  # vs periode sebelumnya (lebih lama)
        df_display["arah"] = df_display["perubahan_pp"].apply(
            lambda x: "🔼 Naik" if pd.notna(x) and x > 0 else ("🔽 Turun" if pd.notna(x) and x < 0 else "➡️ Tetap")
        )

        st.subheader("Histori BI-Rate")
        st.dataframe(df_display, use_container_width=True)
        download_buttons(df_display, "bi_rate_histori", "bi_rate_hist")
        also_save_to_disk(save_to_disk, df_display, "bi_rate_histori")

        # -----------------------------------------------------------
        # Grafik tren
        # -----------------------------------------------------------
        st.subheader("Grafik Tren BI-Rate")
        chart_data = df_hist.set_index("tanggal")[["bi_rate_persen"]].sort_index()
        st.line_chart(chart_data)

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

    with st.expander("ℹ️ Data apa saja yang bisa ditarik & bagaimana bentuknya?", expanded=True):
        for key, src in categories.items():
            st.markdown(f"#### {src['label']}")
            st.markdown(f"**Isi data:** {src['keterangan']}")
            st.markdown(f"**Bentuk file:** {src['format_data']}")
            st.markdown("**Contoh analisis yang bisa dilakukan:**")
            for ide in src["contoh_analisis"]:
                st.markdown(f"- {ide}")
            st.markdown("---")

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
        st.success(f"Ditemukan {len(reports)} laporan (diurutkan dari periode terbaru).")

        # Tabel ringkas fokus ke kolom yang penting untuk analisis: kategori,
        # periode (hasil deteksi otomatis dari judul), judul, & tipe file.
        df_reports = pd.DataFrame(reports)[["kategori", "periode", "judul", "tipe_file", "url"]]
        st.dataframe(df_reports, use_container_width=True)
        download_buttons(df_reports, "ojk_daftar_laporan", "ojk_list")

        st.caption(
            "💡 Kolom **periode** dideteksi otomatis dari judul laporan (pola 'Bulan Tahun'). "
            "Kalau tertulis '-', berarti judulnya tidak memuat pola bulan-tahun yang standar - "
            "cek judul aslinya secara manual."
        )

        st.subheader("Unduh Laporan")
        for i, r in enumerate(reports):
            col1, col2 = st.columns([4, 1])
            with col1:
                st.write(
                    f"**({r['tipe_file']})** {r['judul']}  \n"
                    f"*Kategori: {r.get('kategori', '-')} • Periode: {r.get('periode', '-')}*"
                )
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
