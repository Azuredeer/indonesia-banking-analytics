"""
utils/storage.py
=================
Fungsi bantu untuk menyimpan DataFrame hasil scraping ke berbagai format:
CSV, Excel (.xlsx), dan SQLite.
"""

import os
import sqlite3
import logging
from datetime import datetime

import pandas as pd

from config import DATA_DIR

logger = logging.getLogger(__name__)


def _timestamped_path(name: str, ext: str) -> str:
    """Bangun path file dengan timestamp agar histori data tidak tertimpa."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{name}_{ts}.{ext}"
    return os.path.join(DATA_DIR, filename)


def _strip_timezone(df: pd.DataFrame) -> pd.DataFrame:
    """
    Hilangkan timezone dari semua kolom/index datetime bertipe tz-aware.

    Excel (lewat openpyxl) tidak mendukung datetime yang punya timezone,
    jadi ini WAJIB dipanggil sebelum df.to_excel(). yfinance secara default
    mengembalikan index/kolom tanggal dengan timezone (mis. Asia/Jakarta
    atau America/New_York), makanya error ini sering muncul.
    """
    df = df.copy()

    # Index datetime tz-aware (umum terjadi sebelum df.reset_index())
    if isinstance(df.index, pd.DatetimeIndex) and df.index.tz is not None:
        df.index = df.index.tz_localize(None)

    # Kolom datetime tz-aware
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            try:
                if getattr(df[col].dt, "tz", None) is not None:
                    df[col] = df[col].dt.tz_localize(None)
            except (AttributeError, TypeError):
                pass

    return df


def save_csv(df: pd.DataFrame, name: str, timestamped: bool = False) -> str:
    """Simpan DataFrame ke file CSV. Return path file yang dihasilkan."""
    if df is None or df.empty:
        logger.warning("DataFrame '%s' kosong, tidak ada yang disimpan (CSV).", name)
        return ""
    path = _timestamped_path(name, "csv") if timestamped else os.path.join(DATA_DIR, f"{name}.csv")
    df.to_csv(path, index=False, encoding="utf-8-sig")
    logger.info("Data '%s' disimpan ke %s (%d baris)", name, path, len(df))
    return path


def save_excel(df: pd.DataFrame, name: str, timestamped: bool = False) -> str:
    """Simpan DataFrame ke file Excel (.xlsx). Return path file yang dihasilkan."""
    if df is None or df.empty:
        logger.warning("DataFrame '%s' kosong, tidak ada yang disimpan (Excel).", name)
        return ""
    path = _timestamped_path(name, "xlsx") if timestamped else os.path.join(DATA_DIR, f"{name}.xlsx")
    df_export = _strip_timezone(df)
    df_export.to_excel(path, index=False, engine="openpyxl")
    logger.info("Data '%s' disimpan ke %s (%d baris)", name, path, len(df))
    return path


def save_sqlite(df: pd.DataFrame, table_name: str, db_name: str = "portfolio_data.db",
                 if_exists: str = "append") -> str:
    """
    Simpan DataFrame ke tabel SQLite lokal.
    if_exists: 'append' (tambah histori) | 'replace' (timpa) | 'fail'
    """
    if df is None or df.empty:
        logger.warning("DataFrame '%s' kosong, tidak ada yang disimpan (SQLite).", table_name)
        return ""
    db_path = os.path.join(DATA_DIR, db_name)
    df_export = _strip_timezone(df)
    conn = sqlite3.connect(db_path)
    try:
        df_export.to_sql(table_name, conn, if_exists=if_exists, index=False)
    finally:
        conn.close()
    logger.info("Data '%s' disimpan ke tabel '%s' pada %s (%d baris)",
                table_name, table_name, db_path, len(df))
    return db_path


def save_all(df: pd.DataFrame, name: str, formats=("csv", "xlsx")) -> dict:
    """
    Simpan DataFrame ke beberapa format sekaligus.
    formats bisa berisi kombinasi: 'csv', 'xlsx', 'sqlite'
    Return dict {format: path_atau_info}
    """
    results = {}
    if "csv" in formats:
        results["csv"] = save_csv(df, name)
    if "xlsx" in formats:
        results["xlsx"] = save_excel(df, name)
    if "sqlite" in formats:
        results["sqlite"] = save_sqlite(df, table_name=name)
    return results


def df_to_excel_bytes(df: pd.DataFrame) -> bytes:
    """
    Konversi DataFrame ke bytes .xlsx di memori (dipakai oleh web app untuk
    tombol download tanpa perlu menulis file ke disk terlebih dahulu).
    """
    from io import BytesIO
    df_export = _strip_timezone(df)
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df_export.to_excel(writer, index=False)
    return buffer.getvalue()
