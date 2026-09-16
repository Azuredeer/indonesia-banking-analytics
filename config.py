"""
config.py
=========
Konfigurasi global untuk project scraper data finansial & makroekonomi.
"""

import os

# Folder output data
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

# User-Agent standar dipakai di semua request HTTP agar tidak diblok server
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
}

# Timeout default untuk semua request (detik)
REQUEST_TIMEOUT = 20

# ---------------------------------------------------------------------------
# Bank Indonesia
# ---------------------------------------------------------------------------
# Web service resmi BI untuk data kurs (JISDOR, Kurs Transaksi BI, Kurs UKA, dll)
# Referensi: https://www.bi.go.id/biwebservice/wskursbi.asmx
BI_KURS_WS_BASE = "https://www.bi.go.id/biwebservice/wskursbi.asmx"

# Halaman publik BI untuk suku bunga acuan (BI-Rate / BI7DRR).
# BI TIDAK menyediakan API resmi untuk seri BI-Rate, sehingga diambil
# dengan HTML scraping dari halaman publikasi resminya.
BI_RATE_URL = "https://www.bi.go.id/id/statistik/indikator/bi-rate.aspx"

# ---------------------------------------------------------------------------
# OJK
# ---------------------------------------------------------------------------
# CATATAN PENTING SOAL MIGRASI DATA OJK (per Juli 2025):
# Sejak periode publikasi Juli 2025, OJK memindahkan penyajian data statistik
# sektor jasa keuangan (perbankan, perbankan syariah, dst) ke portal baru
# yang lebih interaktif:
#       https://data.ojk.go.id/SJKPublic
# Halaman-halaman "kanal" lama di bawah ini (default.aspx) TETAP menyimpan
# arsip unduhan PDF/Excel untuk periode SEBELUM Juli 2025, tapi tidak lagi
# menerima update data terbaru. Jadi:
#   - Untuk data historis / arsip lama         -> scraper di bawah ini masih relevan
#   - Untuk data bulanan TERBARU (>= Jul 2025) -> perlu akses ke data.ojk.go.id/SJKPublic
#     (portal ini berbasis dashboard interaktif/API terpisah, di luar cakupan
#     scraper HTML sederhana ini - bisa jadi pengembangan lanjutan)
#
# Struktur HTML OJK juga cukup sering berubah, jadi scraper OJK ditulis
# defensif (mencari semua tabel/link di halaman, bukan bergantung pada satu
# selector CSS yang kaku).
#
# Kategori/kata kunci sumber data OJK yang tersedia untuk di-scrape - dipakai
# baik oleh CLI (main.py) maupun web app (app.py) sebagai pilihan kategori:
#
#   statistik_perbankan
#       -> Statistik Perbankan Indonesia (SPI): kondisi bank umum konvensional
#          se-Indonesia per bulan - total aset, Dana Pihak Ketiga (DPK),
#          kredit yang disalurkan, NPL (kredit bermasalah), CAR (rasio
#          kecukupan modal), ROA/ROE, jumlah kantor/jaringan, dst.
#
#   statistik_perbankan_syariah
#       -> Statistik Perbankan Syariah (SPS): sama seperti di atas tapi
#          untuk Bank Umum Syariah (BUS), Unit Usaha Syariah (UUS), dan
#          Bank Pembiayaan Rakyat Syariah (BPRS) - aset, pembiayaan (bukan
#          "kredit"), DPK, FDR, NPF (setara NPL versi syariah), dst.
#
#   statistik_iknb
#       -> Statistik Industri Keuangan Non-Bank (asuransi, dana pensiun,
#          perusahaan pembiayaan/multifinance, fintech P2P lending, modal
#          ventura, pergadaian) - premi, klaim, aset, piutang pembiayaan,
#          jumlah pemain per sub-sektor, dst.
#
#   statistik_pasar_modal
#       -> Statistik Pasar Modal: aktivitas penawaran umum (IPO/rights
#          issue), jumlah emiten, nilai transaksi bursa, produk reksa dana,
#          dan perkembangan investor pasar modal.
#
# Tambahkan kategori baru di dict OJK_REPORT_SOURCES kalau butuh sumber lain.
OJK_REPORT_SOURCES = {
    "statistik_perbankan": {
        "label": "Statistik Perbankan Indonesia (Bank Umum)",
        "url": "https://ojk.go.id/id/kanal/perbankan/data-dan-statistik/statistik-perbankan-indonesia/default.aspx",
        "keterangan": (
            "Data bulanan bank umum konvensional: total aset, DPK, kredit, "
            "NPL, CAR, ROA/ROE, jumlah kantor. Arsip lengkap s/d Juni 2025; "
            "data terbaru ada di data.ojk.go.id/SJKPublic."
        ),
    },
    "statistik_perbankan_syariah": {
        "label": "Statistik Perbankan Syariah",
        "url": "https://ojk.go.id/id/kanal/syariah/data-dan-statistik/statistik-perbankan-syariah/default.aspx",
        "keterangan": (
            "Data bulanan Bank Umum Syariah, Unit Usaha Syariah & BPRS: "
            "aset, pembiayaan, DPK, FDR, NPF. Arsip lengkap s/d Juni 2025; "
            "data terbaru ada di data.ojk.go.id/SJKPublic."
        ),
    },
    "statistik_iknb": {
        "label": "Statistik Industri Keuangan Non-Bank (IKNB)",
        "url": "https://ojk.go.id/id/kanal/iknb/data-dan-statistik/statistik-iknb/default.aspx",
        "keterangan": (
            "Data asuransi, dana pensiun, perusahaan pembiayaan/multifinance, "
            "fintech P2P lending, modal ventura, dan pergadaian: premi, "
            "klaim, aset, piutang pembiayaan."
        ),
    },
    "statistik_pasar_modal": {
        "label": "Statistik Pasar Modal",
        "url": "https://ojk.go.id/id/kanal/pasar-modal/data-dan-statistik/statistik-pasar-modal/default.aspx",
        "keterangan": (
            "Aktivitas penawaran umum (IPO/rights issue), jumlah emiten, "
            "nilai transaksi bursa, produk reksa dana, dan perkembangan "
            "jumlah investor pasar modal."
        ),
    },
}

# Dipertahankan untuk kompatibilitas mundur dengan main.py versi lama yang
# mengimpor konstanta ini langsung.
OJK_STATISTIK_PERBANKAN_URL = OJK_REPORT_SOURCES["statistik_perbankan"]["url"]

# ---------------------------------------------------------------------------
# Yahoo Finance
# ---------------------------------------------------------------------------
# Contoh ticker relevan untuk pasar Indonesia & global (bisa diubah bebas)
DEFAULT_TICKERS = [
    "^JKSE",     # IHSG
    "BBCA.JK",   # Bank Central Asia
    "BBRI.JK",   # Bank Rakyat Indonesia
    "TLKM.JK",   # Telkom Indonesia
    "USDIDR=X",  # Kurs USD/IDR
    "^GSPC",     # S&P 500
    "GC=F",      # Emas (Gold Futures)
    "CL=F",      # Minyak WTI
]
