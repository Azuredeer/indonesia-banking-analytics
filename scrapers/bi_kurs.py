"""
scrapers/bi_kurs.py
====================
Mengambil data KURS dari Bank Indonesia menggunakan web service resmi
(bukan HTML scraping) sehingga jauh lebih stabil.

Referensi web service:
    https://www.bi.go.id/biwebservice/wskursbi.asmx

Endpoint yang dipakai di sini: getSubKursLokal3
    -> Data Kurs Transaksi BI berdasarkan kode mata uang & rentang tanggal.
    Format response: XML hasil serialisasi System.Data.DataSet (.NET),
    dengan struktur kurang lebih:

        <NewDataSet>
          <xs:schema>...</xs:schema>
          <Table>
            <tanggal>2026-09-01</tanggal>
            <nilai>1</nilai>
            <jual>15834</jual>
            <beli>15676</beli>
          </Table>
          <Table>...</Table>
          ...
        </NewDataSet>

    PENTING: setiap baris data ada di elemen <Table>, BUKAN <Tkurs> seperti
    yang diasumsikan versi sebelumnya - itulah sebabnya dulu hasilnya selalu
    kosong walau request-nya sukses. Response ini juga TIDAK menyertakan
    kolom kode mata uang per baris (karena kita sudah query per satu kode),
    jadi kolom 'mata_uang' kita isi sendiri dari parameter yang diminta.

Catatan penting:
- Web service ini kadang lambat / tidak selalu online 24 jam. Kode di
  bawah sudah menangani error/timeouts dengan baik.
- Kode mata uang mengikuti format 3 huruf standar (USD, EUR, JPY, dst).
- Data BI hanya tersedia untuk hari kerja (tidak ada data di akhir pekan
  / hari libur nasional) - itu normal, bukan berarti scraper gagal.
"""

import re
import logging
from datetime import date, timedelta

import requests
import pandas as pd
from xml.etree import ElementTree as ET

from config import BI_KURS_WS_BASE, DEFAULT_HEADERS, REQUEST_TIMEOUT

logger = logging.getLogger(__name__)

OUTPUT_COLUMNS = ["tanggal", "mata_uang", "kurs_jual", "kurs_beli", "nilai"]


def _parse_id_number(value) -> float | None:
    """
    Parse angka yang bisa datang dalam beberapa format berbeda:
    - "15834"           -> 15834.0
    - "15834.5"         -> 15834.5   (titik sebagai desimal, gaya umum API)
    - "15.834,50"        -> 15834.5   (titik ribuan + koma desimal, gaya ID)
    - "15834,50"        -> 15834.5   (koma sebagai desimal)
    """
    if value is None:
        return None
    s = str(value).strip().replace("%", "")
    if not s:
        return None

    if "," in s and "." in s:
        # Asumsikan format Indonesia: '.' ribuan, ',' desimal
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    # kalau cuma ada '.', biarkan apa adanya (sudah format desimal standar)

    try:
        return float(s)
    except ValueError:
        return None


def _extract_rows_from_dataset_xml(xml_bytes: bytes) -> list[dict]:
    """
    Ambil semua baris data dari XML hasil serialisasi DataSet .NET.

    DataSet .NET biasanya membungkus setiap baris dalam elemen bernama
    "Table" (kadang "Table1", dst kalau ada multiple result set). Fungsi
    ini defensif: elemen apapun yang namanya diawali "table" (setelah
    namespace dibuang) dianggap satu baris data, KECUALI elemen skema XSD.
    """
    root = ET.fromstring(xml_bytes)
    rows = []
    for el in root.iter():
        tag = el.tag.split("}")[-1]  # buang namespace
        if tag.lower().startswith("table") and list(el):
            row = {child.tag.split("}")[-1]: (child.text or "").strip() for child in el}
            rows.append(row)
    return rows


def get_kurs_transaksi_bi(currency_code: str = "USD",
                           start_date: str | None = None,
                           end_date: str | None = None) -> pd.DataFrame:
    """
    Ambil data Kurs Transaksi BI untuk satu mata uang dalam rentang tanggal.

    Parameters
    ----------
    currency_code : kode mata uang 3 huruf, misal "USD", "EUR", "JPY"
    start_date    : format 'YYYY-MM-DD'. Default: 30 hari yang lalu.
    end_date      : format 'YYYY-MM-DD'. Default: hari ini.

    Returns
    -------
    pd.DataFrame dengan kolom: tanggal, mata_uang, kurs_jual, kurs_beli, nilai
    ('nilai' = satuan kelipatan kurs, mis. 100 untuk JPY - kadang dipakai
    BI untuk mata uang bernilai kecil per unit)
    """
    if end_date is None:
        end_date = date.today().isoformat()
    if start_date is None:
        start_date = (date.today() - timedelta(days=30)).isoformat()

    url = f"{BI_KURS_WS_BASE}/getSubKursLokal3"
    params = {
        "mts": currency_code.upper(),
        "startdate": start_date,
        "enddate": end_date,
    }

    logger.info("Mengambil kurs %s dari BI (%s s/d %s)", currency_code, start_date, end_date)

    try:
        resp = requests.get(url, params=params, headers=DEFAULT_HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.error("Gagal mengambil data kurs BI: %s", e)
        return pd.DataFrame(columns=OUTPUT_COLUMNS)

    try:
        rows = _extract_rows_from_dataset_xml(resp.content)
    except ET.ParseError as e:
        logger.error("Gagal parsing XML response BI: %s", e)
        return pd.DataFrame(columns=OUTPUT_COLUMNS)

    if not rows:
        logger.warning(
            "Tidak ada data ditemukan untuk %s pada rentang %s s/d %s "
            "(kemungkinan hari libur/akhir pekan, atau kode mata uang salah).",
            currency_code, start_date, end_date,
        )
        return pd.DataFrame(columns=OUTPUT_COLUMNS)

    raw_df = pd.DataFrame(rows)

    # Cari nama kolom secara case-insensitive & fleksibel, karena field
    # XML dari BI kadang berbeda kapitalisasi/penamaan kecil antar endpoint.
    def find_col(*keywords):
        for col in raw_df.columns:
            col_lower = col.lower()
            if any(kw in col_lower for kw in keywords):
                return col
        return None

    col_tanggal = find_col("tgl", "tanggal", "date")
    col_jual = find_col("jual")
    col_beli = find_col("beli")
    col_nilai = find_col("nil", "nilai")

    out = pd.DataFrame()
    out["tanggal"] = pd.to_datetime(raw_df[col_tanggal], errors="coerce") if col_tanggal else pd.NaT
    out["mata_uang"] = currency_code.upper()
    out["kurs_jual"] = raw_df[col_jual].map(_parse_id_number) if col_jual else None
    out["kurs_beli"] = raw_df[col_beli].map(_parse_id_number) if col_beli else None
    out["nilai"] = raw_df[col_nilai].map(_parse_id_number) if col_nilai else 1

    out = out.dropna(subset=["tanggal"]).sort_values("tanggal").reset_index(drop=True)
    return out


def get_kurs_range(currency_code: str = "USD",
                   start_date: str | date | None = None,
                   end_date: str | date | None = None) -> pd.DataFrame:
    """Alias kompatibilitas UI untuk get_kurs_transaksi_bi (menerima str maupun datetime.date)."""
    start_str = start_date.isoformat() if hasattr(start_date, "isoformat") else (str(start_date) if start_date else None)
    end_str = end_date.isoformat() if hasattr(end_date, "isoformat") else (str(end_date) if end_date else None)
    return get_kurs_transaksi_bi(currency_code, start_str, end_str)



def get_kurs_multi_currency(currency_codes: list[str],
                             start_date: str | None = None,
                             end_date: str | None = None) -> pd.DataFrame:
    """Ambil kurs untuk beberapa mata uang sekaligus, digabung jadi satu DataFrame."""
    all_dfs = []
    for code in currency_codes:
        df = get_kurs_transaksi_bi(code, start_date, end_date)
        if not df.empty:
            all_dfs.append(df)
    if not all_dfs:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)
    return pd.concat(all_dfs, ignore_index=True)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    df = get_kurs_transaksi_bi("USD")
    print(df.tail(10))
