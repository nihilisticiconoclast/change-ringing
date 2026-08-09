#!/usr/bin/env python3
"""
Shared utilities for BellBoard ingestion.

This module provides importable functions for parsing BellBoard XML and
inserting data into the database, used by both ingest_bellboard.py and
backfill_bellboard.py.
"""
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
import sys
import time

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


def fetch_page(url, retries: int = 4) -> bytes:
    """Fetch a URL with retries and basic error handling.
    
    Args:
        url: URL to fetch
        retries: number of retry attempts
        
    Returns:
        bytes: response body
        
    Raises:
        RuntimeError: if all retries fail
    """
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    delay = 2
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                return resp.read()
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            if attempt == retries - 1:
                raise RuntimeError(f"Failed to fetch {url} after {retries} attempts: {exc}") from exc
            print(f"  fetch failed ({exc}); retrying in {delay}s", file=sys.stderr)
            time.sleep(delay)
            delay *= 2
    raise RuntimeError("unreachable")


def fetch_performances(changed_since=None, date_from=None, date_to=None, page=1, pagesize=PAGE_SIZE, retries=4):
    """Fetch a page of performances from BellBoard API.
    
    Args:
        changed_since: fetch performances modified on or after this date (YYYY-MM-DD)
        date_from: start date for date range (YYYY-MM-DD)
        date_to: end date for date range (YYYY-MM-DD)
        page: page number (1-indexed)
        pagesize: number of performances per page
        retries: number of retry attempts
        
    Returns:
        list: list of performance XML elements
        
    Raises:
        RuntimeError: if fetch or parse fails
    """
    # Build URL based on parameters
    if changed_since:
        url = f"{EXPORT_URL}?changed_since={changed_since}&pagesize={pagesize}&page={page}&fmt=xml"
    elif date_from and date_to:
        url = f"{EXPORT_URL}?from={date_from}&to={date_to}&pagesize={pagesize}&page={page}&fmt=xml"
    else:
        raise ValueError("Either changed_since or date_from/date_to must be provided")
    
    raw = fetch_page(url, retries)
    try:
        return ET.fromstring(raw).findall(f"{NS}performance")
    except ET.ParseError as exc:
        raise RuntimeError(f"could not parse page: {exc}") from exc


def parse_performance(p):
    """Flatten one <performance> into (perf_row, ringers, footnotes, flags).
    
    Returns:
        tuple: (perf_row, ringers, footnotes, flags) where each is a list of
        column values, or None if the performance cannot be parsed.
        
        perf_row has 23 elements matching PERF_COLS, including ingested_at timestamp.
    """
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

    # Include ingested_at timestamp (column 23) in the perf_row
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    
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
        now,  # ingested_at - column 23
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


PERF_COLS = [
    "perf_id", "bb_id", "association", "place", "dedication", "county",
    "towerbase-id", "dove_tower_id", "dove_ring_id", "ring_type", "tenor",
    "portable", "dumb_bells", "perf_date", "duration", "changes", "method",
    "title", "details", "composer", "composition", "bb_timestamp", "ingested_at",
]


def insert_many(conn, table, cols, rows):
    """Multi-row INSERT OR REPLACE. The client's executemany() costs a round
    trip per row against a remote primary -- see the comment in
    migrate_csv_to_turso.py.
    
    Args:
        conn: libsql connection
        table: table name
        cols: list of column names
        rows: list of row tuples
    """
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
