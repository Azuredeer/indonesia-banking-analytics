"""
scrapers/ojk_stats.py
=======================
Mengambil data statistik dari situs resmi OJK (ojk.go.id).

Karakteristik sumber ini:
- OJK umumnya mempublikasikan data statistik (Statistik Perbankan
  Indonesia, Statistik Perbankan Syariah, Statistik IKNB, Statistik Pasar
  Modal, dll) dalam bentuk file unduhan (.xlsx / .pdf) yang ditautkan dari
  halaman kanal statistik, BUKAN dalam tabel HTML langsung.
- Karena itu, pendekatan scraper ini ada dua lapis:
    1. `list_available_reports()`  -> scan SATU halaman OJK, kumpulkan
       semua tautan unduhan (xlsx/pdf/csv) beserta judul/labelnya.
    2. `search_reports_multi()`    -> scan BEBERAPA kategori/halaman OJK
       sekaligus (lihat `config.OJK_REPORT_SOURCES`) dan opsional
       filter kata kunci judul, hasilnya ditandai per kategori.
    3. `download_report()`         -> unduh salah satu file tsb ke folder
       data/ lokal untuk diproses lebih lanjut (mis. dengan pandas).
- Jika OJK mengubah struktur halaman, sesuaikan CSS selector pada
  `list_available_reports()`.

PENTING - soal cakupan data (lihat juga komentar di config.py):
Sejak periode Juli 2025, publikasi data OJK yang lebih baru dipindah ke
portal https://data.ojk.go.id/SJKPublic. Halaman-halaman kanal lama yang
di-scrape di sini (default.aspx) hanya masih menyimpan ARSIP unduhan untuk
periode sebelum Juli 2025. Jadi kalau daftar laporan yang muncul terlihat
"lawas", itu memang batas dari sumber data ini, bukan bug scraper.
"""

import os
import re
import logging
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from config import OJK_STATISTIK_PERBANKAN_URL, OJK_REPORT_SOURCES, DEFAULT_HEADERS, REQUEST_TIMEOUT, DATA_DIR

logger = logging.getLogger(__name__)

DOWNLOADABLE_EXTENSIONS = (".xlsx", ".xls", ".csv", ".pdf")


def list_available_reports(url: str = OJK_STATISTIK_PERBANKAN_URL) -> list[dict]:
    """
    Scan halaman statistik OJK dan kumpulkan semua tautan unduhan laporan.

    Returns
    -------
    list of dict: [{"judul": str, "url": str, "tipe_file": str}, ...]
    """
    logger.info("Mengambil daftar laporan OJK dari %s", url)
    try:
        resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.error("Gagal mengakses halaman OJK: %s", e)
        return []

    soup = BeautifulSoup(resp.text, "lxml")
    reports = []

    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        if href.lower().endswith(DOWNLOADABLE_EXTENSIONS):
            full_url = urljoin(url, href)
            judul = a_tag.get_text(strip=True) or os.path.basename(href)
            ext = os.path.splitext(href)[1].lower().lstrip(".")
            reports.append({"judul": judul, "url": full_url, "tipe_file": ext})

    # Buang duplikat berdasarkan URL sambil mempertahankan urutan
    seen = set()
    unique_reports = []
    for r in reports:
        if r["url"] not in seen:
            seen.add(r["url"])
            unique_reports.append(r)

    if not unique_reports:
        logger.warning(
            "Tidak ditemukan tautan unduhan di halaman OJK. "
            "Kemungkinan struktur halaman berubah - cek selector di "
            "scrapers/ojk_stats.py, atau situs memerlukan JavaScript "
            "rendering (pertimbangkan Selenium/Playwright jika demikian)."
        )
    else:
        logger.info("Ditemukan %d tautan laporan OJK", len(unique_reports))

    return unique_reports


def list_categories() -> dict:
    """Kembalikan daftar kategori/sumber OJK yang tersedia (lihat config.OJK_REPORT_SOURCES),
    berguna untuk ditampilkan sebagai pilihan di UI (mis. dropdown kategori)."""
    return OJK_REPORT_SOURCES


def search_reports_multi(keyword: str | None = None, category_keys: list[str] | None = None) -> list[dict]:
    """
    Cari laporan di BEBERAPA kategori/halaman OJK sekaligus, opsional
    difilter dengan kata kunci judul.

    Parameters
    ----------
    keyword       : filter judul laporan (opsional, case-insensitive).
                    Kosongkan untuk mengambil semua laporan yang tersedia.
    category_keys : daftar key dari OJK_REPORT_SOURCES yang mau discan,
                    mis. ["statistik_perbankan", "statistik_iknb"].
                    Default: semua kategori yang terdaftar.

    Returns
    -------
    list of dict: setiap laporan ditambah key 'kategori' (label kategori
    asalnya), selain 'judul', 'url', 'tipe_file' seperti biasa.
    """
    if category_keys is None:
        category_keys = list(OJK_REPORT_SOURCES.keys())

    keyword_lower = keyword.lower().strip() if keyword else None
    all_results = []

    for key in category_keys:
        source = OJK_REPORT_SOURCES.get(key)
        if not source:
            logger.warning("Kategori OJK '%s' tidak dikenal, dilewati.", key)
            continue

        reports = list_available_reports(source["url"])
        for r in reports:
            if keyword_lower and keyword_lower not in r["judul"].lower():
                continue
            r_tagged = dict(r)
            r_tagged["kategori"] = source["label"]
            all_results.append(r_tagged)

    logger.info(
        "Pencarian OJK multi-kategori: %d laporan ditemukan dari %d kategori (keyword=%r)",
        len(all_results), len(category_keys), keyword,
    )
    return all_results


def search_reports_by_keyword(keyword: str) -> list[dict]:
    """Alias kompatibel untuk pencarian laporan OJK berdasarkan keyword judul."""
    return search_reports_multi(keyword=keyword)



def download_report(report: dict, target_dir: str = DATA_DIR) -> str:
    """
    Unduh satu file laporan OJK (hasil dari list_available_reports) ke disk.

    Parameters
    ----------
    report : dict dengan key 'url' dan 'judul' (lihat list_available_reports)

    Returns
    -------
    path file lokal hasil unduhan, atau "" jika gagal.
    """
    url = report["url"]
    ext = report.get("tipe_file", "bin")

    # Bersihkan nama file dari karakter tidak aman
    safe_name = re.sub(r"[^\w\-. ]", "_", report.get("judul", "laporan_ojk"))[:100]
    filename = f"{safe_name}.{ext}" if not safe_name.endswith(f".{ext}") else safe_name
    local_path = os.path.join(target_dir, filename)

    logger.info("Mengunduh laporan OJK: %s -> %s", url, local_path)
    try:
        resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=REQUEST_TIMEOUT, stream=True)
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.error("Gagal mengunduh %s: %s", url, e)
        return ""

    os.makedirs(target_dir, exist_ok=True)
    with open(local_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)

    logger.info("Berhasil diunduh: %s", local_path)
    return local_path


def search_reports_by_keyword(keyword: str, url: str = OJK_STATISTIK_PERBANKAN_URL) -> list[dict]:
    """Cari laporan OJK yang judulnya mengandung kata kunci tertentu
    (mis. 'Statistik Perbankan', bulan/tahun tertentu, dsb)."""
    all_reports = list_available_reports(url)
    keyword_lower = keyword.lower()
    return [r for r in all_reports if keyword_lower in r["judul"].lower()]


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    reports = list_available_reports()
    for r in reports[:10]:
        print(r)
