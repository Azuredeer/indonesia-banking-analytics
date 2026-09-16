# 🏦 Indonesian Macro-Banking Intelligence & Analytics Platform
### *Macroeconomic Transmission, Banking Health (OJK), and Equity Performance Analysis (The Big 4 Banks: BBCA, BBRI, BMRI, BBNI)*

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-1.37%2B-red)
![Pandas](https://img.shields.io/badge/Pandas-2.0%2B-green)
![Jupyter](https://img.shields.io/badge/Jupyter-Notebook-orange)

---

## 📌 Executive Summary & Project Overview

Proyek ini merupakan **Portofolio Data Analyst Finansial & Makroekonomi** berskala *end-to-end* yang meneliti hubungan timbal balik antara:
1. **Kebijakan Moneter & Valas**: Suku Bunga Acuan (BI-Rate / BI7DRR) dan dinamika Kurs Transaksi Bank Indonesia (JISDOR / USD-IDR).
2. **Kesehatan Industri Perbankan**: Kinerja intermediasi kredit, DPK, rasio likuiditas (*Loan to Deposit Ratio* / LDR), dan risiko kredit macet (*Non-Performing Loan* / NPL) dari **Statistik Perbankan Indonesia (OJK SPI)**.
3. **Valuasi Pasar Modal**: Pergerakan harga dan imbal hasil saham 4 bank berkapitalisasi terbesar di Bursa Efek Indonesia (*The Big 4 Banks*: **BBCA**, **BBRI**, **BMRI**, **BBNI**) serta indeks acuan **IHSG** (`^JKSE`).
2. **Kesehatan Industri Perbankan Nasional**: Kinerja intermediasi kredit/pembiayaan, DPK, rasio likuiditas (*Loan to Deposit Ratio* / LDR dan FDR Syariah), dan risiko kredit macet (*Non-Performing Loan* / NPL dan NPF Syariah) dari **Statistik Perbankan Indonesia (OJK SPI)** dan **Statistik Perbankan Syariah (OJK SPS)**.
3. **Komparasi 3 Pilar Perbankan Indonesia**:
   - **Bank BUMN (Persero)**: `BBRI`, `BMRI`, `BBNI`, `BBTN` (*Agent of Development*, kredit program/UMKM & infrastruktur).
   - **Bank Swasta Nasional (BUSN)**: `BBCA`, `BNGA`, `BDMN`, `NISP` (*Commercial Maximizer*, dana murah CASA ritel >80%, NPL konservatif).
   - **Bank Syariah**: `BRIS`, `BTPS` (*Ethical & Profit-Sharing Banking*, bebas bunga, imunitas terhadap pengetatan moneter konvensional).
4. **Valuasi Pasar Modal**: Pergerakan harga dan imbal hasil saham perbankan serta indeks acuan **IHSG** (`^JKSE`) tanpa batasan ticker.

Sistem dibangun dari hulu ke hilir: **Automated Web Scrapers & APIs** $\rightarrow$ **Data Modeling & Feature Engineering** $\rightarrow$ **Exploratory Data Analysis (EDA) & Statistical Correlation** $\rightarrow$ **Interactive Web Dashboard (Streamlit)**.

---

## 💡 Key Business & Analytical Insights

Berdasarkan analisis statistik dan eksplorasi data (*Exploratory Data Analysis*):
* **Sensitivitas Kurs (Foreign Outflow Transmission)**: Saham perbankan berkapitalisasi besar memiliki korelasi negatif yang kuat terhadap pelemahan nilai tukar Rupiah (`USDIDR=X`). Ketika Rupiah terdepresiasi cepat, tekanan jual paling tajam terjadi pada bank dengan kepemilikan investor asing yang dominan, mencerminkan risiko *capital flight*.
* **Likuiditas Perbankan Masih Resilien**: Rasio LDR perbankan nasional stabil pada kisaran **84% - 87%**, masih di bawah *threshold* waspada regulator (**92%**). Ini membuktikan perbankan nasional masih memiliki ruang likuiditas yang memadai untuk ekspansi pembiayaan di tengah dinamika suku bunga acuan.
* **Kualitas Aset (NPL) Terkendali**: NPL Gross perbankan nasional terjaga stabil di kisaran **2.15% - 2.35%**, mengindikasikan manajemen risiko kredit yang *prudent* dan pembentukan Cadangan Kerugian Penurunan Nilai (CKPN) yang sehat.
* **Profil Karakteristik Saham The Big 4**:
  * **BBCA**: Volatilitas dan *Max Drawdown* terendah, didukung oleh kekuatan rasio CASA (dana murah) yang dominan.
  * **BBRI & BMRI**: Sensitivitas lebih tinggi terhadap siklus pertumbuhan kredit korporasi dan pembiayaan UMKM nasional.
* **Dinamika 3 Pilar Perbankan**:
  * **Bank Swasta (Defensive Anchor)**: Memiliki volatilitas terendah, NPL paling terjaga (~2.0%), dan paling tahan terhadap depresiasi Rupiah berkat kekuatan CASA ritel.
  * **Bank BUMN (Growth Engine)**: Memegang porsi aset terbesar (~46%) dan LDR tinggi (~87%), namun biaya dana (CoF) lebih sensitif terhadap siklus kenaikan suku bunga acuan.
  * **Bank Syariah (High Growth Potential)**: Pertumbuhan DPK dan pembiayaan melesat tercepat (>12% YoY) dengan NPF terkendali (~2.0%), membuktikan model bisnis bagi hasil dan margin tetap memiliki resiliensi unik.
* **Sensitivitas Kurs (Foreign Outflow Transmission)**: Saham perbankan berkapitalisasi besar berkorelasi negatif terhadap pelemahan nilai tukar Rupiah (`USDIDR=X`). Tekanan jual asing paling tajam terjadi pada bank-bank berlikuiditas tinggi.
* **Likuiditas Perbankan Resilien**: Rasio LDR/FDR perbankan nasional stabil pada kisaran **84% - 87%**, masih di bawah *threshold* waspada regulator (**92%**).

---

## 🏗️ Data Architecture & Pipeline

```
┌────────────────────────────────────────────────────────┐
│                   DATA EXTRACTION                      │
├───────────────────┬────────────────────┬───────────────┤
│  Bank Indonesia   │     OJK (SPI)      │ Yahoo Finance │
│  - BI-Rate (HTML) │  - Statistik SPI   │ - BBCA, BBRI, │
│  - Kurs BI (XML)  │    (Kredit, DPK,   │   BMRI, BBNI  │
│                   │    NPL, CAR, LDR)  │ - IHSG, USDIDR│
└─────────┬─────────┴─────────┬──────────┴───────┬───────┘
          │                   │                  │
          ▼                   ▼                  ▼
┌────────────────────────────────────────────────────────┐
│             ANALYTICAL & MODELING ENGINE               │
│         (analytics/macro_banking_engine.py)            │
│  - Timezone Normalization & Forward Fill Alignment     │
│  - Annualized Volatility, Beta vs IHSG, Max Drawdown   │
│  - Pearson & 30-Day Rolling Correlation with USD/IDR   │
│  - Automated Executive Storytelling Insights           │
└─────────────────────────────┬──────────────────────────┘
                              │
          ┌───────────────────┴───────────────────┐
          ▼                                       ▼
┌─────────────────────────────────┐   ┌────────────────────────────────┐
│  INTERACTIVE STREAMLIT WEB APP  │   │   JUPYTER NOTEBOOK DEEP-DIVE   │
│            (app.py)             │   │ (notebooks/macro_banking_...)  │
│ - Live Macro KPI Cards          │   │ - 7-Stage Comprehensive EDA    │
│ - Normalized Performance Charts │   │ - Statistical Significance     │
│ - Dual-Axis Stock vs FX Charts  │   │ - Seaborn Correlation Heatmaps │
│ - Portfolio Risk Matrix Export  │   │ - Strategic Recommendations    │
└─────────────────────────────────┘   └────────────────────────────────┘
```

---

## 📝 Dua Fokus Artikel & Portofolio

Proyek ini dipisahkan menjadi **2 modul aplikasi mandiri** untuk mendukung penulisan 2 artikel teknis:

1. **Artikel 1: Automated Financial Data Pipeline (Data Engineering / Scraping)**
   - Fokus: Pengambilan data publik dari BI (XML), OJK (HTML), dan Yahoo Finance (API), validasi tipe data, pembersihan timezone datetime, serta ekspor CSV/Excel.
   - Script Web: [`app_scraper.py`](file:///d:/Project%20Analysis%20Personal/Data%20Banking%20Portofolio/app_scraper.py)
   - CLI Runner: [`main.py`](file:///d:/Project%20Analysis%20Personal/Data%20Banking%20Portofolio/main.py)
2. **Artikel 2: Macroeconomic Transmission & Equity Risk Analysis (Data Analytics / Financial BI)**
   - Fokus: Menganalisis korelasi kebijakan suku bunga BI-Rate & depresiasi kurs USD/IDR terhadap kesehatan bank OJK dan risiko saham pasar modal (Big 4 Banks, Digital Banks, Komoditas).
   - Script Web: [`app_analytics.py`](file:///d:/Project%20Analysis%20Personal/Data%20Banking%20Portofolio/app_analytics.py)
   - Jupyter Notebook: [`notebooks/macro_banking_equity_analysis.ipynb`](file:///d:/Project%20Analysis%20Personal/Data%20Banking%20Portofolio/notebooks/macro_banking_equity_analysis.ipynb)

---

## 📂 Struktur Repositori

```
├── app_scraper.py                     # 🌐 Aplikasi Web Khusus Data Scraping & Ingestion (Artikel 1)
├── app_analytics.py                   # 📈 Aplikasi Web Khusus Dashboard Analitik & BI (Artikel 2)
├── app.py                             # All-in-one App (versi gabungan)
├── main.py                            # CLI Runner otomatis untuk scraping data
├── config.py                          # Konfigurasi URL, API endpoint, header, & tickers
├── requirements.txt                   # Dependensi Python proyek
├── analytics/                         # 🧠 Engine Analitik & Finansial
│   ├── __init__.py
│   └── macro_banking_engine.py        # Kalkulasi return, volatilitas, drawdown, beta, korelasi
├── notebooks/                         # 📓 Riset Eksploratif (Jupyter Notebook)
│   ├── generate_notebook.py           # Generator notebook otomatis
│   └── macro_banking_equity_analysis.ipynb # Notebook lengkap (EDA + Visualisasi)
├── scrapers/                          # 🌐 Scraper Data Publik
│   ├── bi_kurs.py                     # Scraper Web Service XML Kurs Bank Indonesia
│   ├── bi_rate.py                     # Scraper HTML publikasi suku bunga BI-Rate
│   ├── ojk_stats.py                   # Scraper laporan statistik OJK (SPI/SPS/IKNB)
│   └── yahoo_finance.py               # Integrasi data pasar Yahoo Finance (yfinance)
├── utils/
│   └── storage.py                     # Utility penyimpanan aman CSV/Excel (Timezone-safe)
└── data/                              # Folder penyimpanan dataset lokal (.csv & .xlsx)
```

---

## 🚀 Panduan Instalasi & Penggunaan

### 1. Setup Environment
Pastikan Python 3.10+ sudah terpasang. Buat dan aktifkan virtual environment:

```bash
# Windows
python -m venv .venv
.\.venv\Scripts\activate

# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate
```

Install seluruh dependensi:
```bash
pip install -r requirements.txt
```

### 2. Menjalankan Aplikasi Web (Sesuai Fokus Artikel)

* **Untuk Artikel 1 (Scraping & Data Collection):**
  ```bash
  streamlit run app_scraper.py
  ```
  Menampilkan dashboard pengumpulan data BI, OJK, dan Yahoo Finance, serta ekspor dataset.

* **Untuk Artikel 2 (Dashboard Analitik & Portofolio):**
  ```bash
  streamlit run app_analytics.py
  ```
  Menampilkan visualisasi performa relatif, grafik dual-axis kurs vs saham, matriks korelasi, rasio kesehatan bank OJK, serta matriks risiko finansial (bebas memasukkan ticker apa saja).

### 3. Menjalankan Jupyter Notebook (EDA & Riset Finansial)
Buka file notebook di VS Code atau JupyterLab:
```bash
jupyter notebook notebooks/macro_banking_equity_analysis.ipynb
```

---

## 📊 Metrik Finansial yang Dihitung

| Metrik | Formulasi / Penjelasan |
|---|---|
| **Cumulative Return (%)** | $\frac{P_t - P_0}{P_0} \times 100\%$ |
| **Annualized Volatility (%)** | $\sigma_{\text{daily}} \times \sqrt{252} \times 100\%$ |
| **Maximum Drawdown (%)** | $\min\left(\frac{P_t - \max_{0 \le s \le t} P_s}{\max_{0 \le s \le t} P_s}\right) \times 100\%$ |
| **Beta Saham terhadap IHSG** | $\beta = \frac{\text{Cov}(R_{\text{stock}}, R_{\text{IHSG}})}{\text{Var}(R_{\text{IHSG}})}$ |
| **Korelasi Kurs (FX Correlation)** | $\rho(R_{\text{stock}}, R_{\text{USDIDR}})$ |

---

## 👤 Profil & Portofolio
Proyek ini didesain sebagai studi kasus nyata dalam melamar posisi **Data Analyst**, **Business Intelligence Analyst**, atau **Financial/Risk Analyst** di sektor perbankan dan jasa keuangan.
