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


def get_expected_count(date_from: str, date_to: str) -> int:
    """Query BellBoard search.php to determine the exact expected performance count for a date range."""
    import urllib.request
    import re
    url = f"https://bb.ringingworld.co.uk/search.php?from={date_from}&to={date_to}"
    req = urllib.request.Request(url, headers={"User-Agent": "change-ringing-corpus/0.1"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                html = resp.read().decode("utf-8")
                m = re.search(r'([0-9,]+)\s+performances', html)
                if m:
                    return int(m.group(1).replace(",", ""))
                if "No performances found" in html:
                    return 0
        except Exception as e:
            if attempt == 3:
                print(f"  Warning: could not query search.php for count ({e})", flush=True)
                return -1
            time.sleep(2 * (attempt + 1))
    return -1


def fetch_year_data(year: int):
    print(f"\n{'='*60}\n>>> Fetching BellBoard Corpus for Year {year}\n{'='*60}", flush=True)

    expected_year_total = get_expected_count(f"{year}-01-01", f"{year}-12-31")
    print(f"  Ground-truth expected performances from BellBoard search.php: {expected_year_total:,}", flush=True)

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

        expected_window = get_expected_count(start_d, end_d)
        print(f"  Fetching window {start_d} to {end_d} (Expected: {expected_window:,}) ...", flush=True)
        page = 1
        window_perfs = {}

        while True:
            elems = None
            for attempt in range(5):
                try:
                    elems = fetch_performances(date_from=start_d, date_to=end_d, page=page, pagesize=1000)
                    break
                except Exception as e:
                    wait_sec = (attempt + 1) * 10
                    print(f"    [Retry {attempt+1}/5] Fetch error for {start_d}..{end_d} page {page}: {e}. Waiting {wait_sec}s...", flush=True)
                    time.sleep(wait_sec)

            if elems is None or not elems:
                break

            for el in elems:
                parsed = parse_performance(el)
                if parsed:
                    p_row, r_list, fn_list, fl_list = parsed
                    p_id = p_row[0]
                    window_perfs[p_id] = p_row
                    all_perfs[p_id] = p_row
                    all_ringers.extend(r_list)
                    all_footnotes.extend(fn_list)
                    all_flags.extend(fl_list)

            print(f"    Page {page}: {len(elems)} performances", flush=True)
            if len(elems) < 1000:
                break
            page += 1
            time.sleep(1.0)

        # Completeness Gate for window
        if expected_window > 0 and len(window_perfs) < expected_window:
            diff = expected_window - len(window_perfs)
            if diff > 5: # Tolerating minor boundary/draft edits
                print(f"  ERROR: Window {start_d}..{end_d} fetched {len(window_perfs)} < expected {expected_window} (missing {diff})", flush=True)
                raise RuntimeError(f"Completeness gate failure for window {start_d}..{end_d}")

        print(f"  -> Window complete: {len(window_perfs):,} performances (Year-to-date total: {len(all_perfs):,})", flush=True)
        time.sleep(1.0)

    # Completeness Gate for full year
    if expected_year_total > 0 and len(all_perfs) < (expected_year_total - 20):
        print(f"ERROR: Full year total {len(all_perfs):,} < expected {expected_year_total:,}", flush=True)
        raise RuntimeError(f"Completeness gate failure for full year {year}")

    print(f"\n>>> Full Year {year} Gate PASSED: {len(all_perfs):,} / {expected_year_total:,} performances", flush=True)
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
