# 📊 Scraper Data Finansial & Makroekonomi Publik — Web App (Streamlit)

Versi web dari CLI scraper (BI / OJK / Yahoo Finance), dibangun dengan
Streamlit di atas logic scraper yang sama persis (tidak ada duplikasi kode).

## Instalasi

```bash
pip install -r requirements.txt
```

## Menjalankan Web App

```bash
streamlit run app.py
```

Browser akan otomatis terbuka ke `http://localhost:8501`.

## Fitur Web App

- **Beranda** — ringkasan sumber data
- **Yahoo Finance** — pilih ticker default / custom, ambil data historis + kuotasi terkini, lihat grafik harga, download CSV/Excel
- **Kurs Bank Indonesia** — pilih mata uang & rentang tanggal, lihat grafik kurs, download CSV/Excel
- **BI-Rate** — ambil suku bunga acuan terkini & histori
- **Statistik OJK** — cari & download laporan statistik perbankan

Semua hasil bisa didownload langsung dari browser, dan opsional juga
disimpan ke folder `data/` (bisa dimatikan lewat checkbox di sidebar).

## Struktur Project

```
webapp/
├── app.py                    # Aplikasi Streamlit (entry point web)
├── main.py                   # Entry point CLI (versi lama, masih bisa dipakai)
├── config.py
├── requirements.txt
├── scrapers/
│   ├── bi_kurs.py
│   ├── bi_rate.py
│   ├── ojk_stats.py
│   └── yahoo_finance.py
├── utils/
│   └── storage.py             # ✅ sudah di-fix: bug timezone Excel
└── data/
```

## 🔧 Bug yang Sudah Diperbaiki

**Sebelumnya:** `ValueError: Excel does not support datetimes with timezones`
saat menyimpan data Yahoo Finance ke Excel.

**Penyebab:** `yfinance` mengembalikan index/kolom tanggal yang timezone-aware
(mis. `Asia/Jakarta`), sementara openpyxl tidak mendukung datetime dengan
timezone.

**Perbaikan:** `utils/storage.py` sekarang punya fungsi `_strip_timezone()`
yang otomatis menghapus info timezone dari semua kolom/index datetime
sebelum menulis ke Excel — dipanggil otomatis di `save_excel()` dan
`df_to_excel_bytes()`.

## Pengembangan Selanjutnya (Ide)

- Modul analisa & visualisasi lanjutan (korelasi kurs vs saham, dsb.)
- Scheduler untuk scraping otomatis harian
- Simpan histori ke SQLite dan buat halaman "riwayat data" di web app
