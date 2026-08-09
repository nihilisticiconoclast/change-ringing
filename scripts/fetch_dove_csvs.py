#!/usr/bin/env python3
"""
Download the seven Dove's Guide bulk CSVs.

Dove publishes these at stable URLs, so a load does not depend on anyone
having a copy sitting in their Downloads folder -- fetch, then migrate:

    python scripts/fetch_dove_csvs.py --out-dir ./dove-csvs
    python scripts/migrate_csv_to_turso.py --csv-dir ./dove-csvs

Source data: Dove's Guide for Church Bell Ringers, https://dove.cccbr.org.uk
Licence: CC BY-SA 4.0 -- see data/SOURCES.md for attribution requirements.

The downloaded CSVs are deliberately not committed to this repo (see
data/SOURCES.md); treat the output directory as a scratch area.
"""
import argparse
import sys
import urllib.request
from pathlib import Path

BASE_URL = "https://dove.cccbr.org.uk"
FILES = ["bells", "changes", "dove", "founders", "frames", "regions", "towers"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--out-dir",
        default="./dove-csvs",
        help="Directory to write the CSVs into (created if it does not exist)",
    )
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    for name in FILES:
        url = f"{BASE_URL}/{name}.csv"
        dest = out_dir / f"{name}.csv"
        print(f"Fetching {url} ...")
        try:
            urllib.request.urlretrieve(url, dest)
        except OSError as exc:
            print(f"ERROR: failed to fetch {url}: {exc}", file=sys.stderr)
            return 1
        # Row count excludes the header line.
        with open(dest, encoding="utf-8-sig") as f:
            rows = sum(1 for _ in f) - 1
        print(f"  {dest} -- {rows} rows")

    print(f"\nDone. Now run:\n  python scripts/migrate_csv_to_turso.py --csv-dir {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
