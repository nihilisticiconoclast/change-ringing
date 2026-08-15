#!/usr/bin/env python3
"""
Writes the yearly CSVs this repository commits. THIS is what produced the
2012-2024 corpus; `backfill_bellboard.py` is the other BellBoard fetcher and
loads into a database instead. Both share the same completeness gate.

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

from bellboard_common import (fetch_performances, parse_performance, insert_many,
                              fetch_expected_count, WINDOW_TOLERANCE)

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

    # Completeness gate. export.php gives no total of its own and a truncated
    # page is indistinguishable from a genuine last page, so every window is
    # checked against the count search.php reports for the same range, and the
    # year is checked against the year. A short fetch raises; silence is the bug.
    #
    # fetch_expected_count comes from bellboard_common, deliberately: it is the
    # same function backfill_bellboard.py gates on, so the two runners cannot
    # disagree about what a window should hold. An earlier version of this file
    # carried its own copy, which drifted in three ways -- a regex without the
    # "Found" anchor that could match another number on the page, an empty-window
    # check for text search.php does not emit, and a hardcoded five-record
    # tolerance. The shared version's tolerance is 0, measured across six windows
    # where search.php and export.php agreed exactly.
    expected_year = fetch_expected_count(f"{year}-01-01",
                                         min(f"{year}-12-31", today_str))
    if expected_year is None:
        raise RuntimeError(
            f"search.php reports no performances for {year}; refusing to run a "
            f"backfill whose expected size is unknown.")
    print(f"  search.php expects {expected_year:,} performances for {year}", flush=True)

    for m_start, m_end in months:
        start_d = f"{year}-{m_start}"
        end_d = f"{year}-{m_end}"

        if start_d > today_str:
            continue
        if end_d > today_str:
            end_d = today_str

        expected_window = fetch_expected_count(start_d, end_d)
        print(f"  Fetching window {start_d} to {end_d} "
              f"(expecting {expected_window if expected_window is not None else 'none'}) ...",
              flush=True)
        page = 1
        window_perfs = set()

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
                    all_perfs[p_id] = p_row
                    all_ringers.extend(r_list)
                    all_footnotes.extend(fn_list)
                    all_flags.extend(fl_list)
                    # DISTINCT ids, not a row counter: export.php can return the
                    # same record on more than one page, and a counter would let
                    # duplicates make up a shortfall.
                    window_perfs.add(p_id)

            print(f"    Page {page}: {len(elems)} performances", flush=True)
            if len(elems) < 1000:
                break
            page += 1
            time.sleep(1.0)

        if expected_window is not None:
            floor = expected_window * (1 - WINDOW_TOLERANCE)
            if len(window_perfs) < floor:
                raise RuntimeError(
                    f"completeness gate: {start_d}..{end_d} fetched "
                    f"{len(window_perfs)} unique performances against "
                    f"{expected_window} expected. BellBoard truncates silently, "
                    f"so a short window is a truncated one, not a finished one.")
        elif window_perfs:
            print(f"  WARNING: search.php reported no performances for "
                  f"{start_d}..{end_d} but export.php returned "
                  f"{len(window_perfs)}", flush=True)

        print(f"  -> Window complete: {len(window_perfs):,} performances "
              f"(year to date {len(all_perfs):,})", flush=True)
        time.sleep(1.0)

    if len(all_perfs) < expected_year * (1 - WINDOW_TOLERANCE):
        raise RuntimeError(
            f"completeness gate: {year} fetched {len(all_perfs):,} unique "
            f"performances against {expected_year:,} expected.")
    print(f"  {year} gate passed: {len(all_perfs):,} / {expected_year:,}", flush=True)

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
