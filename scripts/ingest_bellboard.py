#!/usr/bin/env python3
"""
Ingest BellBoard performances into the Turso database.

Prerequisites:
    pip install libsql
    export TURSO_DATABASE_URL="libsql://<your-db>.turso.io"
    export TURSO_AUTH_TOKEN="<your-token>"
    # apply schema/002_init_bellboard.sql first (see --init)

Usage:
    # create the BellBoard tables (once)
    python scripts/ingest_bellboard.py --init

    # backfill a window
    python scripts/ingest_bellboard.py --changed-since 2026-01-01

    # incremental: pick up where the last run left off
    python scripts/ingest_bellboard.py --since-last

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
import os
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

import libsql

NS = "{http://bb.ringingworld.co.uk/NS/performances#}"
EXPORT_URL = "https://bb.ringingworld.co.uk/export.php"
PAGE_SIZE = 1000  # BellBoard rejects >10000 with HTTP 413; 1000 keeps pages small
PARAM_BUDGET = 16000
USER_AGENT = (
    "change-ringing-corpus/0.1 (+https://github.com/nihilisticiconoclast/change-ringing)"
)


def text_of(elem):
    """Flattened text of an element, or None. Footnotes and details contain
    markup in places, so itertext() rather than .text."""
    if elem is None:
        return None
    s = "".join(elem.itertext()).strip()
    return s or None


def fetch_page(changed_since: str, page: int, retries: int = 4) -> bytes:
    url = (
        f"{EXPORT_URL}?changed_since={changed_since}"
        f"&pagesize={PAGE_SIZE}&page={page}&fmt=xml"
    )
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    delay = 2
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                return resp.read()
        except (urllib.error.URLError, TimeoutError) as exc:
            if attempt == retries - 1:
                raise
            print(f"  fetch failed ({exc}); retrying in {delay}s", file=sys.stderr)
            time.sleep(delay)
            delay *= 2
    raise RuntimeError("unreachable")


def parse_performance(p):
    """Flatten one <performance> into (perf_row, ringers, footnotes, flags)."""
    bb_id = p.get("id") or ""
    perf_id = int(bb_id.lstrip("P")) if bb_id.lstrip("P").isdigit() else None
    if perf_id is None:
        return None

    place = p.find(f"{NS}place")
    names = {}
    towerbase = dove_tower = dove_ring = ring_type = tenor = portable = dumb = None
    if place is not None:
        towerbase = place.get("towerbase-id")
        dove_tower = place.get("dove-tower-id")
        for n in place.findall(f"{NS}place-name"):
            names[n.get("type")] = text_of(n)
        ring = place.find(f"{NS}ring")
        if ring is not None:
            ring_type = ring.get("type")
            tenor = ring.get("tenor")
            dove_ring = ring.get("dove-ring-id")
            portable = ring.get("portable")
            dumb = ring.get("dumb-bells")

    title_el = p.find(f"{NS}title")
    changes = method = None
    if title_el is not None:
        changes = text_of(title_el.find(f"{NS}changes"))
        method = text_of(title_el.find(f"{NS}method"))

    as_int = lambda v: int(v) if v is not None and str(v).isdigit() else None

    perf_row = [
        perf_id,
        bb_id,
        text_of(p.find(f"{NS}association")),
        names.get("place"),
        names.get("dedication"),
        names.get("county"),
        as_int(towerbase),
        as_int(dove_tower),
        as_int(dove_ring),
        ring_type,
        tenor,
        portable,
        dumb,
        text_of(p.find(f"{NS}date")),
        text_of(p.find(f"{NS}duration")),
        as_int(changes),
        method,
        text_of(title_el),
        text_of(p.find(f"{NS}details")),
        text_of(p.find(f"{NS}composer")),
        text_of(p.find(f"{NS}composition")),
        text_of(p.find(f"{NS}timestamp")),
        datetime.now(timezone.utc).isoformat(timespec="seconds"),
    ]

    ringers = []
    holder = p.find(f"{NS}ringers")
    if holder is not None:
        for i, r in enumerate(holder.findall(f"{NS}ringer")):
            ringers.append(
                [
                    perf_id,
                    i,
                    r.get("bell"),
                    text_of(r),
                    1 if r.get("conductor") == "true" else 0,
                ]
            )

    footnotes = [
        [perf_id, i, text_of(f)] for i, f in enumerate(p.findall(f"{NS}footnote"))
    ]
    flags = [
        [perf_id, i, f.get("type"), f.get("bell"), text_of(f)]
        for i, f in enumerate(p.findall(f"{NS}flag"))
    ]
    return perf_row, ringers, footnotes, flags


def insert_many(conn, table, cols, rows):
    """Multi-row INSERT OR REPLACE. The client's executemany() costs a round
    trip per row against a remote primary -- see the comment in
    migrate_csv_to_turso.py."""
    if not rows:
        return
    col_list = ", ".join(f'"{c}"' for c in cols)
    tup = "(" + ", ".join("?" for _ in cols) + ")"
    batch_size = max(1, min(500, PARAM_BUDGET // len(cols)))
    for i in range(0, len(rows), batch_size):
        batch = rows[i : i + batch_size]
        sql = (
            f'INSERT OR REPLACE INTO "{table}" ({col_list}) VALUES '
            + ", ".join([tup] * len(batch))
        )
        conn.execute(sql, [v for row in batch for v in row])


PERF_COLS = [
    "perf_id", "bb_id", "association", "place", "dedication", "county",
    "towerbase-id", "dove_tower_id", "dove_ring_id", "ring_type", "tenor",
    "portable", "dumb_bells", "perf_date", "duration", "changes", "method",
    "title", "details", "composer", "composition", "bb_timestamp", "ingested_at",
]


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
    args = parser.parse_args()

    url = os.environ.get("TURSO_DATABASE_URL")
    token = os.environ.get("TURSO_AUTH_TOKEN")
    if not url or not token:
        print(
            "ERROR: set TURSO_DATABASE_URL and TURSO_AUTH_TOKEN in the environment.",
            file=sys.stderr,
        )
        return 1

    conn = libsql.connect(database=url, auth_token=token)

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

    total = 0
    page = 1
    while True:
        if args.max_pages and page > args.max_pages:
            print(f"Reached --max-pages {args.max_pages}; stopping.")
            break
        print(f"Fetching page {page} (changed_since={changed_since}) ...")
        raw = fetch_page(changed_since, page)
        try:
            root = ET.fromstring(raw)
        except ET.ParseError as exc:
            print(f"ERROR: could not parse page {page}: {exc}", file=sys.stderr)
            return 1

        perfs = root.findall(f"{NS}performance")
        if not perfs:
            print("  empty page; done.")
            break

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
