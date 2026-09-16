"""
scrapers/bi_rate.py
=====================
Mengambil histori BI-Rate / BI 7-Day Reverse Repo Rate (BI7DRR) dari
halaman publik Bank Indonesia.

PENTING - Karakteristik sumber ini:
- Bank Indonesia TIDAK menyediakan web service/API resmi untuk seri
  BI-Rate (berbeda dengan data Kurs yang punya wskursbi.asmx).
- Karena itu, data ini diambil dengan HTML scraping dari halaman
  publikasi statistik BI (https://www.bi.go.id/id/statistik/indikator/bi-rate.aspx).
  Halaman ini server-rendered (bukan SPA React/Angular) sehingga bisa
  langsung di-scrape tanpa browser/JS engine.
- Halaman menampilkan tabel dengan kolom "No | Tanggal | BI-Rate | Pranala
  Siaran Pers", dengan format contoh baris: "19 Agustus 2026 | 5.75 %".
  PERHATIKAN: BI menuliskan persentase dengan TITIK sebagai desimal
  ("5.75 %"), bukan koma ("5,75%") seperti kebiasaan umum Indonesia -
  versi kode sebelumnya salah asumsi soal ini sehingga tabel yang valid
  selalu tertolak oleh filter dan hasilnya selalu kosong.
- Tabel di halaman ini dipaginasi lewat ASP.NET `__doPostBack` (butuh
  JavaScript), sehingga scraping HTML polos HANYA bisa mengambil
  halaman pertama (±10 baris histori terbaru). Untuk histori lebih
  panjang, lengkapi manual dari sumber sekunder atau gunakan browser
  automation (Selenium/Playwright) untuk klik paginasi.

Alternatif jika scraping gagal:
- Data BI-Rate juga rutin dipublikasikan lewat siaran pers RDG BI, atau
  bisa diinput manual/dilengkapi dari sumber sekunder (BPS, Investing.com)
  untuk keperluan portofolio/analisis non-real-time.
"""

import re
import logging
from io import StringIO

import requests
import pandas as pd
from bs4 import BeautifulSoup

from config import DEFAULT_HEADERS, REQUEST_TIMEOUT

logger = logging.getLogger(__name__)

# Beberapa kandidat URL halaman BI yang pernah/biasa memuat data BI-Rate.
# Dicoba berurutan sampai salah satu berhasil & menghasilkan tabel valid.
URL_CANDIDATES = [
    "https://www.bi.go.id/id/statistik/indikator/bi-rate.aspx",
    "https://www.bi.go.id/id/moneter/bi-rate/data/Default.aspx",
]

# Peta nama bulan Bahasa Indonesia (lengkap & singkatan) ke nomor bulan,
# dipakai untuk parsing tanggal seperti "19 Agustus 2026".
_BULAN_MAP = {
    "januari": 1, "jan": 1,
    "februari": 2, "feb": 2,
    "maret": 3, "mar": 3,
    "april": 4, "apr": 4,
    "mei": 5,
    "juni": 6, "jun": 6,
    "juli": 7, "jul": 7,
    "agustus": 8, "agu": 8, "ags": 8,
    "september": 9, "sep": 9, "sept": 9,
    "oktober": 10, "okt": 10,
    "november": 11, "nov": 11,
    "desember": 12, "des": 12,
}


def _parse_indonesian_date(text: str):
    """Parse tanggal berformat 'D Bulan YYYY' (mis. '19 Agustus 2026') ke pd.Timestamp."""
    if text is None:
        return pd.NaT
    text = str(text).strip().lower()
    m = re.match(r"(\d{1,2})\s+([a-z]+)\.?\s+(\d{4})", text)
    if not m:
        return pd.NaT
    day, month_name, year = m.groups()
    month = _BULAN_MAP.get(month_name)
    if month is None:
        return pd.NaT
    try:
        return pd.Timestamp(year=int(year), month=month, day=int(day))
    except ValueError:
        return pd.NaT


def _parse_percent(text) -> float | None:
    """Parse nilai persen yang bisa pakai titik ATAU koma sebagai desimal, mis. '5.75 %' atau '5,75%'."""
    if text is None:
        return None
    s = str(text).replace("%", "").strip()
    if not s:
        return None
    # Kalau ada koma tapi tidak ada titik, anggap koma = desimal (gaya lama BI)
    if "," in s and "." not in s:
        s = s.replace(",", ".")
    else:
        s = s.replace(",", "")  # buang koma ribuan kalau ada, sisakan titik desimal
    try:
        return float(s)
    except ValueError:
        return None


def _looks_like_rate_table(df: pd.DataFrame) -> bool:
    """Heuristik sederhana: tabel dianggap tabel suku bunga jika salah satu
    kolomnya mengandung nilai persentase (format titik ATAU koma, mis.
    '5.75' atau '5,75') dan ada kolom lain yang menyerupai tanggal/periode."""
    if df.empty or df.shape[1] < 2:
        return False
    text_blob = " ".join(df.astype(str).values.flatten())
    has_percent_like = bool(re.search(r"\d{1,2}[.,]\d{2}\s*%?", text_blob))
    has_date_like = bool(
        re.search(r"(20\d{2})|(Jan|Feb|Mar|Apr|Mei|Jun|Jul|Agu|Ags|Sep|Okt|Nov|Des)", text_blob, re.IGNORECASE)
    )
    return has_percent_like and has_date_like


def _clean_rate_table(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ubah tabel mentah hasil scraping (kolom & nama bisa bervariasi) menjadi
    DataFrame rapi dengan kolom standar: tanggal (datetime), bi_rate_persen
    (float), dan pranala_siaran_pers (jika ada, teks apa adanya).

    Kalau kolom tanggal/rate tidak berhasil dikenali, kembalikan df asli
    tanpa perubahan sebagai fallback (lebih baik data mentah daripada
    kehilangan semuanya).
    """
    def find_col(*keywords):
        for col in df.columns:
            col_lower = str(col).lower()
            if all(kw in col_lower for kw in keywords):
                return col
        return None

    col_tanggal = find_col("tanggal")
    col_rate = find_col("rate") or find_col("bi-rate") or find_col("suku", "bunga")

    if col_tanggal is None or col_rate is None:
        logger.warning(
            "Tidak bisa mengenali kolom tanggal/rate secara otomatis dari tabel BI. "
            "Mengembalikan data mentah apa adanya (kolom: %s).", list(df.columns)
        )
        return df

    out = pd.DataFrame()
    out["tanggal"] = df[col_tanggal].map(_parse_indonesian_date)
    out["bi_rate_persen"] = df[col_rate].map(_parse_percent)

    col_pranala = find_col("pranala") or find_col("siaran")
    if col_pranala:
        out["pranala_siaran_pers"] = df[col_pranala]

    out = out.dropna(subset=["tanggal"]).sort_values("tanggal", ascending=False).reset_index(drop=True)
    return out


def get_bi_rate_history() -> pd.DataFrame:
    """
    Coba ambil tabel historis BI-Rate dari halaman resmi BI.

    Returns
    -------
    pd.DataFrame dengan kolom bersih: tanggal, bi_rate_persen, (opsional)
    pranala_siaran_pers - diurutkan dari yang terbaru. Kosong jika gagal /
    tidak ditemukan tabel yang cocok di semua kandidat URL.

    CATATAN: karena paginasi tabel di halaman BI butuh JavaScript, hasil
    ini hanya mencakup histori terbaru (±10 entri dari halaman pertama).
    """
    for url in URL_CANDIDATES:
        logger.info("Mencoba mengambil BI-Rate dari %s", url)
        try:
            resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
        except requests.RequestException as e:
            logger.warning("Gagal mengakses %s: %s", url, e)
            continue

        try:
            # WAJIB dibungkus StringIO - pandas >= 2.1 memperlakukan string
            # biasa sebagai path file/URL, bukan HTML mentah, dan akan
            # melempar FileNotFoundError kalau tidak dibungkus begini.
            tables = pd.read_html(StringIO(resp.text))
        except ValueError:
            # Tidak ada tabel HTML standar ditemukan, coba fallback manual
            # parsing dengan BeautifulSoup untuk struktur non-<table>.
            tables = _fallback_parse_with_bs4(resp.text)

        for df in tables:
            if _looks_like_rate_table(df):
                logger.info("Tabel BI-Rate ditemukan di %s (%d baris mentah)", url, len(df))
                cleaned = _clean_rate_table(df)
                if not cleaned.empty:
                    return cleaned

        logger.warning("Tidak ditemukan tabel yang cocok/valid setelah dibersihkan di %s", url)

    logger.error(
        "Gagal mengambil histori BI-Rate dari semua kandidat URL. "
        "Kemungkinan struktur halaman BI berubah - cek URL_CANDIDATES "
        "di scrapers/bi_rate.py dan sesuaikan."
    )
    return pd.DataFrame(columns=["tanggal", "bi_rate_persen"])


def _fallback_parse_with_bs4(html: str) -> list[pd.DataFrame]:
    """Fallback parser jika data ditampilkan bukan dalam <table> standar,
    misalnya dalam <div>/<li> dengan class tertentu (umum di web modern)."""
    soup = BeautifulSoup(html, "lxml")
    candidates = []

    # Coba temukan elemen list/div yang berulang dan mengandung pola
    # "tanggal - persentase", contoh umum pada widget grafik BI.
    rows = []
    for el in soup.select("li, div"):
        text = el.get_text(" ", strip=True)
        if re.search(r"\d{1,2}[.,]\d{2}\s*%", text) and re.search(r"20\d{2}", text):
            rows.append(text)

    if rows:
        candidates.append(pd.DataFrame({"raw_text": rows}))

    return candidates


def get_bi_rate_terkini() -> dict:
    """
    Ambil ringkasan BI-Rate TERKINI, diambil dari baris paling atas
    (terbaru) dari histori tabel resmi BI - lebih andal dibanding regex
    bebas di seluruh teks halaman.

    Returns
    -------
    dict: {"tanggal": pd.Timestamp atau None, "nilai_persen": float atau None,
           "sumber_url": str}
    """
    df_hist = get_bi_rate_history()
    if df_hist.empty:
        return {"tanggal": None, "nilai_persen": None, "sumber_url": URL_CANDIDATES[0]}

    terbaru = df_hist.iloc[0]
    return {
        "tanggal": terbaru.get("tanggal"),
        "nilai_persen": terbaru.get("bi_rate_persen"),
        "sumber_url": URL_CANDIDATES[0],
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(get_bi_rate_terkini())
    print(get_bi_rate_history().head())
