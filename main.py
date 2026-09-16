#!/usr/bin/env python3
"""
main.py
=======
Entry point CLI untuk Program Scraping Data Finansial & Makroekonomi Publik
(Bank Indonesia / OJK / Yahoo Finance).

Contoh pemakaian
-----------------
    # Ambil semua data default (kurs BI, BI-Rate, daftar laporan OJK, saham2 utama)
    python main.py --all

    # Ambil data Yahoo Finance untuk ticker tertentu
    python main.py --yahoo BBCA.JK TLKM.JK --period 1y

    # Ambil kurs BI untuk mata uang tertentu
    python main.py --bi-kurs USD EUR JPY --start-date 2026-01-01 --end-date 2026-09-01

    # Ambil BI-Rate terkini & histori
    python main.py --bi-rate

    # Daftar laporan yang tersedia di OJK (tanpa mengunduh)
    python main.py --ojk-list

    # Unduh laporan OJK pertama yang judulnya mengandung kata kunci
    python main.py --ojk-download "Statistik Perbankan"

Semua hasil disimpan ke folder data/ dalam format CSV & Excel.
"""

import argparse
import logging
import sys

from config import DEFAULT_TICKERS
from scrapers import yahoo_finance, bi_kurs, bi_rate, ojk_stats
from utils.storage import save_all, save_csv

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("main")


def run_yahoo(tickers, period, interval):
    logger.info("=== Mengambil data Yahoo Finance ===")
    df_hist = yahoo_finance.get_multiple_tickers(tickers, period=period, interval=interval)
    save_all(df_hist, "yahoo_finance_historis")

    df_quote = yahoo_finance.get_latest_quotes_multi(tickers)
    save_all(df_quote, "yahoo_finance_kuotasi_terkini")

    if not df_quote.empty:
        print("\nKuotasi terakhir:")
        print(df_quote.to_string(index=False))


def run_bi_kurs(currency_codes, start_date, end_date):
    logger.info("=== Mengambil data Kurs Bank Indonesia ===")
    df = bi_kurs.get_kurs_multi_currency(currency_codes, start_date, end_date)
    save_all(df, "bi_kurs_transaksi")
    if not df.empty:
        print("\nContoh data kurs BI (5 baris terakhir):")
        print(df.tail().to_string(index=False))


def run_bi_rate():
    logger.info("=== Mengambil data BI-Rate ===")
    terkini = bi_rate.get_bi_rate_terkini()
    print("\nBI-Rate terkini:", terkini)

    df_hist = bi_rate.get_bi_rate_history()
    if not df_hist.empty:
        save_csv(df_hist, "bi_rate_histori")
        print("\nCuplikan histori BI-Rate:")
        print(df_hist.head().to_string(index=False))
    else:
        logger.warning(
            "Histori BI-Rate tidak berhasil diambil otomatis. "
            "Gunakan nilai 'terkini' di atas, atau lengkapi manual."
        )


def run_ojk_list(keyword=None):
    logger.info("=== Mengambil daftar laporan statistik OJK ===")
    if keyword:
        reports = ojk_stats.search_reports_by_keyword(keyword)
    else:
        reports = ojk_stats.list_available_reports()

    if not reports:
        print("Tidak ada laporan ditemukan.")
        return reports

    print(f"\nDitemukan {len(reports)} laporan:")
    for i, r in enumerate(reports, 1):
        print(f"  [{i}] ({r['tipe_file']}) {r['judul']} -> {r['url']}")
    return reports


def run_ojk_download(keyword):
    reports = run_ojk_list(keyword)
    if not reports:
        return
    target = reports[0]
    logger.info("Mengunduh laporan pertama yang cocok: %s", target["judul"])
    path = ojk_stats.download_report(target)
    if path:
        print(f"\nBerhasil diunduh ke: {path}")


def build_arg_parser():
    parser = argparse.ArgumentParser(
        description="Scraper Data Finansial & Makroekonomi Publik (BI / OJK / Yahoo Finance)"
    )
    parser.add_argument("--all", action="store_true",
                         help="Jalankan semua scraper dengan pengaturan default")

    # Yahoo Finance
    parser.add_argument("--yahoo", nargs="+", metavar="TICKER",
                         help="Ambil data Yahoo Finance untuk daftar ticker tertentu")
    parser.add_argument("--period", default="6mo",
                         help="Rentang waktu Yahoo Finance, mis. 1mo, 6mo, 1y, 5y (default: 6mo)")
    parser.add_argument("--interval", default="1d",
                         help="Interval data Yahoo Finance, mis. 1d, 1wk, 1mo (default: 1d)")

    # BI Kurs
    parser.add_argument("--bi-kurs", nargs="+", metavar="KODE_MATA_UANG",
                         help="Ambil data kurs BI untuk daftar kode mata uang, mis. USD EUR JPY")
    parser.add_argument("--start-date", help="Tanggal awal (YYYY-MM-DD) untuk data kurs BI")
    parser.add_argument("--end-date", help="Tanggal akhir (YYYY-MM-DD) untuk data kurs BI")

    # BI Rate
    parser.add_argument("--bi-rate", action="store_true",
                         help="Ambil data BI-Rate (suku bunga acuan) terkini & histori")

    # OJK
    parser.add_argument("--ojk-list", action="store_true",
                         help="Tampilkan daftar laporan statistik yang tersedia di OJK")
    parser.add_argument("--ojk-keyword", default=None,
                         help="Filter kata kunci judul laporan OJK (dipakai bersama --ojk-list)")
    parser.add_argument("--ojk-download", metavar="KATA_KUNCI",
                         help="Unduh laporan OJK pertama yang judulnya cocok dengan kata kunci")

    return parser


def main():
    parser = build_arg_parser()
    args = parser.parse_args()

    ran_something = False

    if args.all:
        run_yahoo(DEFAULT_TICKERS, period="6mo", interval="1d")
        run_bi_kurs(["USD", "EUR", "JPY"], None, None)
        run_bi_rate()
        run_ojk_list()
        ran_something = True

    if args.yahoo:
        run_yahoo(args.yahoo, period=args.period, interval=args.interval)
        ran_something = True

    if args.bi_kurs:
        run_bi_kurs(args.bi_kurs, args.start_date, args.end_date)
        ran_something = True

    if args.bi_rate:
        run_bi_rate()
        ran_something = True

    if args.ojk_list:
        run_ojk_list(args.ojk_keyword)
        ran_something = True

    if args.ojk_download:
        run_ojk_download(args.ojk_download)
        ran_something = True

    if not ran_something:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
