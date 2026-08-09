#!/usr/bin/env python3
"""
Fetch BellBoard performances in yearly partitions and export clean CSVs for Git version control.

Outputs partitioned CSVs in data/bellboard/:
    data/bellboard/performances_{year}.csv
    data/bellboard/ringers_{year}.csv
    data/bellboard/footnotes_{year}.csv
    data/bellboard/flags_{year}.csv

Also inserts/updates records into the local database (data/change-ringing.db).

Usage:
    # Fetch and export a single year (e.g. 2024)
    python scripts/fetch_and_export_bellboard.py --years 2024

    # Fetch multiple historical years
    python scripts/fetch_and_export_bellboard.py --start-year 2015 --end-year 2024
"""
import argparse
import csv
import sqlite3
import sys
import time
from datetime import date
from pathlib import Path

# Add scripts directory to path for imports
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from bellboard_common import fetch_performances, parse_performance, insert_many

DEFAULT_DB = ROOT / "data" / "change-ringing.db"
DEFAULT_OUT_DIR = ROOT / "data" / "bellboard"

PERF_COLS = [
    "perf_id", "bb_id", "association", "place", "dedication", "county",
    "towerbase-id", "dove_tower_id", "dove_ring_id", "ring_type", "tenor",
    "portable", "dumb_bells", "perf_date", "duration", "changes", "method",
    "title", "details", "composer", "composition", "bb_timestamp", "ingested_at"
]

RINGER_COLS = ["perf_id", "position", "bell", "name", "conductor"]
FOOTNOTE_COLS = ["perf_id", "position", "footnote"]
FLAG_COLS = ["perf_id", "position", "flag_type", "bell", "flag_text"]


def fetch_year_data(year: int):
    print(f"\n{'='*60}\n>>> Fetching BellBoard Corpus for Year {year}\n{'='*60}", flush=True)

    months = [
        ("01-01", "01-31"), ("02-01", "02-29" if (year%4==0 and (year%100!=0 or year%400==0)) else "02-28"),
        ("03-01", "03-31"), ("04-01", "04-30"), ("05-01", "05-31"), ("06-01", "06-30"),
        ("07-01", "07-31"), ("08-01", "08-31"), ("09-01", "09-30"), ("10-01", "10-31"),
        ("11-01", "11-30"), ("12-01", "12-31"),
    ]

    all_perfs = {}
    all_ringers = []
    all_footnotes = []
    all_flags = []

    today_str = date.today().isoformat()

    for m_start, m_end in months:
        start_d = f"{year}-{m_start}"
        end_d = f"{year}-{m_end}"

        if start_d > today_str:
            continue
        if end_d > today_str:
            end_d = today_str

        print(f"  Fetching window {start_d} to {end_d} ...", flush=True)
        page = 1
        window_count = 0

        while True:
            try:
                elems = fetch_performances(date_from=start_d, date_to=end_d, page=page, pagesize=1000)
            except Exception as e:
                print(f"    [Error] Window {start_d}..{end_d} page {page}: {e}", flush=True)
                break

            if not elems:
                break

            for el in elems:
                parsed = parse_performance(el)
                if parsed:
                    p_row, r_list, fn_list, fl_list = parsed
                    p_id = p_row[0]
                    all_perfs[p_id] = p_row
                    all_ringers.extend(r_list)
                    all_footnotes.extend(fn_list)
                    all_flags.extend(fl_list)
                    window_count += 1

            print(f"    Page {page}: {len(elems)} performances", flush=True)
            if len(elems) < 1000:
                break
            page += 1
            time.sleep(1.0)

        print(f"  -> Window complete: {window_count} performances (Year total: {len(all_perfs):,})", flush=True)
        time.sleep(1.0)

    return list(all_perfs.values()), all_ringers, all_footnotes, all_flags


def export_and_save_year(year: int, out_dir: Path, db_path: Path = None):
    perfs, ringers, footnotes, flags = fetch_year_data(year)
    print(f"\n>>> Year {year} Complete: {len(perfs):,} performances, {len(ringers):,} ringers", flush=True)

    out_dir.mkdir(parents=True, exist_ok=True)
    perf_csv = out_dir / f"performances_{year}.csv"
    ringer_csv = out_dir / f"ringers_{year}.csv"
    fn_csv = out_dir / f"footnotes_{year}.csv"
    fl_csv = out_dir / f"flags_{year}.csv"

    # Write Performances CSV
    with open(perf_csv, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(PERF_COLS)
        writer.writerows(perfs)

    # Write Ringers CSV
    with open(ringer_csv, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(RINGER_COLS)
        writer.writerows(ringers)

    # Write Footnotes CSV
    with open(fn_csv, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(FOOTNOTE_COLS)
        writer.writerows(footnotes)

    # Write Flags CSV
    with open(fl_csv, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(FLAG_COLS)
        writer.writerows(flags)

    print(f"  Wrote: {perf_csv} ({perf_csv.stat().st_size / 1024:.1f} KB)", flush=True)
    print(f"  Wrote: {ringer_csv} ({ringer_csv.stat().st_size / 1024:.1f} KB)", flush=True)
    print(f"  Wrote: {fn_csv} ({fn_csv.stat().st_size / 1024:.1f} KB)", flush=True)
    print(f"  Wrote: {fl_csv} ({fl_csv.stat().st_size / 1024:.1f} KB)", flush=True)

    # Save to local database
    if db_path and db_path.exists():
        conn = sqlite3.connect(db_path)
        schema_file = ROOT / "schema" / "002_init_bellboard.sql"
        if schema_file.exists():
            try:
                conn.executescript(schema_file.read_text(encoding="utf-8"))
            except sqlite3.OperationalError:
                pass  # Tables already exist

        if perfs:
            insert_many(conn, "performances", PERF_COLS, perfs)
            perf_ids = [p[0] for p in perfs]
            for i in range(0, len(perf_ids), 900):
                chunk = perf_ids[i:i+900]
                conn.execute(f"DELETE FROM performance_ringers WHERE perf_id IN ({','.join(['?']*len(chunk))})", chunk)
                conn.execute(f"DELETE FROM performance_footnotes WHERE perf_id IN ({','.join(['?']*len(chunk))})", chunk)
                conn.execute(f"DELETE FROM performance_flags WHERE perf_id IN ({','.join(['?']*len(chunk))})", chunk)

        if ringers:
            insert_many(conn, "performance_ringers", RINGER_COLS, ringers)
        if footnotes:
            insert_many(conn, "performance_footnotes", FOOTNOTE_COLS, footnotes)
        if flags:
            insert_many(conn, "performance_flags", FLAG_COLS, flags)

        conn.commit()
        conn.close()
        print(f"  Inserted into local database {db_path.name}: {len(perfs):,} perfs, {len(ringers):,} ringers", flush=True)


def main():
    parser = argparse.ArgumentParser(description="Fetch and export BellBoard corpus partitioned by year.")
    parser.add_argument("--years", help="Comma-separated years (e.g. 2023,2024)")
    parser.add_argument("--start-year", type=int, help="Start year (e.g. 2015)")
    parser.add_argument("--end-year", type=int, help="End year (e.g. 2024)")
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR), help="Output directory for CSVs")
    parser.add_argument("--local-db", default=str(DEFAULT_DB), help="Local SQLite DB path")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    db_path = Path(args.local_db) if args.local_db else None

    years = []
    if args.years:
        years = [int(y.strip()) for y in args.years.split(",") if y.strip()]
    elif args.start_year and args.end_year:
        years = list(range(args.start_year, args.end_year + 1))
    else:
        years = [2024]

    for y in years:
        export_and_save_year(y, out_dir, db_path)


if __name__ == "__main__":
    main()
