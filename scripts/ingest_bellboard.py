#!/usr/bin/env python3
"""
Ingest BellBoard performances into the Turso database.

Prerequisites:
    pip install libsql
    # For production: export TURSO_DATABASE_URL, TURSO_AUTH_TOKEN, and CHANGE_RINGING_ALLOW_PRODUCTION=1
    # For local: use --local-db PATH
    # apply schema/002_init_bellboard.sql first (see --init)

Usage:
    # create the BellBoard tables (once)
    python scripts/ingest_bellboard.py --init

    # backfill a window
    python scripts/ingest_bellboard.py --changed-since 2026-01-01

    # incremental: pick up where the last run left off
    python scripts/ingest_bellboard.py --since-last

    # local database
    python scripts/ingest_bellboard.py --local-db local_corpus.db --changed-since 2026-01-01

Source: BellBoard, https://bb.ringingworld.co.uk -- API docs at
https://bb.ringingworld.co.uk/help/api.php

Incremental sync uses BellBoard's own changed_since parameter, which orders by
modification date, so an edited performance is re-fetched and overwritten
rather than missed. Writes are idempotent: performances are INSERT OR REPLACE
by BellBoard's own ID, and child rows are deleted before reinsert, so re-running
over an overlapping window converges rather than duplicating.

Deletions are NOT handled. BellBoard does not record deletion dates (see its
API docs), so a performance removed upstream will linger here until a full
reload. Treat this corpus as complete-plus rather than exactly-equal.
"""
import argparse
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

import db

from bellboard_common import (
    NS,
    EXPORT_URL,
    PAGE_SIZE,
    fetch_performances,
    parse_performance,
    insert_many,
    PERF_COLS,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--changed-since",
        help="Fetch performances modified on or after this date (YYYY-MM-DD)",
    )
    group.add_argument(
        "--since-last",
        action="store_true",
        help="Resume from the newest bb_timestamp already in the database",
    )
    parser.add_argument(
        "--init",
        action="store_true",
        help="Apply schema/002_init_bellboard.sql before ingesting",
    )
    parser.add_argument(
        "--schema",
        default=str(Path(__file__).parent.parent / "schema" / "002_init_bellboard.sql"),
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=0,
        help="Stop after N pages (0 = no limit). Useful for a bounded first run.",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=3.0,
        help="Seconds to wait between page fetches (default 3). BellBoard "
        "throttles sustained querying -- it starts returning short pages "
        "rather than an error status, so do not lower this for a backfill.",
    )
    db.add_db_args(parser)
    args = parser.parse_args()

    conn = db.connect(args)

    if args.init:
        print(f"Applying schema from {args.schema} ...")
        with open(args.schema) as f:
            conn.executescript(f.read())
        conn.commit()

    changed_since = args.changed_since
    if args.since_last:
        row = conn.execute("SELECT MAX(bb_timestamp) FROM performances").fetchall()
        newest = row[0][0] if row and row[0][0] else None
        if not newest:
            print(
                "ERROR: --since-last needs at least one existing row; "
                "run --changed-since first.",
                file=sys.stderr,
            )
            return 1
        # Re-fetch the whole final day rather than slicing mid-timestamp:
        # changed_since takes a date, and overlap is free because writes are
        # idempotent, whereas a gap silently loses performances.
        changed_since = newest[:10]
        print(f"Resuming from newest bb_timestamp {newest} -> changed_since={changed_since}")

    if not changed_since:
        print("ERROR: pass --changed-since YYYY-MM-DD or --since-last.", file=sys.stderr)
        return 1

    def load_page(n):
        return fetch_performances(changed_since=changed_since, page=n, pagesize=PAGE_SIZE)

    total = 0
    page = 1
    while True:
        if args.max_pages and page > args.max_pages:
            print(f"Reached --max-pages {args.max_pages}; stopping.")
            break
        print(f"Fetching page {page} (changed_since={changed_since}) ...")
        try:
            perfs = load_page(page)
        except RuntimeError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1

        if not perfs:
            print("  empty page; done.")
            break

        # A short page normally means the last page -- but BellBoard answers
        # sustained querying by truncating pages rather than returning an error
        # status, and a throttled page is also short. Taking it at face value
        # would end a backfill early and silently. Back off and re-fetch once:
        # if more rows come back, it was throttling, not the end.
        if len(perfs) < PAGE_SIZE:
            cooloff = max(args.delay * 5, 15)
            print(
                f"  short page ({len(perfs)} < {PAGE_SIZE}) -- could be the last page "
                f"or throttling; waiting {cooloff:.0f}s and re-checking"
            )
            time.sleep(cooloff)
            try:
                retry = load_page(page)
            except RuntimeError as exc:
                print(f"ERROR: {exc}", file=sys.stderr)
                return 1
            if len(retry) > len(perfs):
                print(f"  re-fetch returned {len(retry)}; was throttled, continuing")
                perfs = retry
            else:
                print(f"  re-fetch returned {len(retry)}; treating as the last page")

        perf_rows, ringers, footnotes, flags = [], [], [], []
        for p in perfs:
            parsed = parse_performance(p)
            if parsed is None:
                continue
            pr, rg, fn, fl = parsed
            perf_rows.append(pr)
            ringers.extend(rg)
            footnotes.extend(fn)
            flags.extend(fl)

        # Child rows are keyed by (perf_id, position); if an edit upstream
        # shortened a list, stale tail rows would survive an INSERT OR REPLACE.
        # Clear them first so each performance's children match the source.
        ids = [str(r[0]) for r in perf_rows]
        for chunk in (ids[i : i + 400] for i in range(0, len(ids), 400)):
            id_list = ",".join(chunk)
            for tbl in ("performance_ringers", "performance_footnotes", "performance_flags"):
                conn.execute(f'DELETE FROM "{tbl}" WHERE "perf_id" IN ({id_list})')

        insert_many(conn, "performances", PERF_COLS, perf_rows)
        insert_many(conn, "performance_ringers",
                    ["perf_id", "position", "bell", "name", "conductor"], ringers)
        insert_many(conn, "performance_footnotes",
                    ["perf_id", "position", "footnote"], footnotes)
        insert_many(conn, "performance_flags",
                    ["perf_id", "position", "flag_type", "bell", "flag_text"], flags)
        conn.commit()

        total += len(perf_rows)
        print(f"  page {page}: {len(perf_rows)} performances, {len(ringers)} ringers")
        if len(perfs) < PAGE_SIZE:
            break
        page += 1
        time.sleep(args.delay)

    print(f"\nIngested {total} performances.")
    for tbl in ("performances", "performance_ringers", "performance_footnotes",
                "performance_flags"):
        n = conn.execute(f'SELECT COUNT(*) FROM "{tbl}"').fetchall()[0][0]
        print(f"  {tbl}: {n}")
    linked = conn.execute("SELECT COUNT(*) FROM v_tower_performances").fetchall()[0][0]
    print(f"  v_tower_performances (linked to a Dove tower): {linked}")

    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
