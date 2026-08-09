#!/usr/bin/env python3
"""
BellBoard historical backfill runner.

A resumable, checkpointed, politeness-aware runner that walks the BellBoard
corpus back through time and loads it using the existing ingestion logic.

Prerequisites:
    pip install libsql
    # For production: export TURSO_DATABASE_URL, TURSO_AUTH_TOKEN, and CHANGE_RINGING_ALLOW_PRODUCTION=1
    # For local: use --local-db PATH
    # apply schema/002_init_bellboard.sql first

Usage:
    # Run a full backfill (resumable, checkpointed)
    python scripts/backfill_bellboard.py

    # Run with local database
    python scripts/backfill_bellboard.py --local-db local_corpus.db

    # Run a specific date range
    python scripts/backfill_bellboard.py --start 2020-01-01 --end 2020-12-31

    # Resume from checkpoint
    python scripts/backfill_bellboard.py --resume

    # Run with custom window size (default is 30 days)
    python scripts/backfill_bellboard.py --window-days 60

    # Run with shorter delay between windows (default is 5 seconds)
    python scripts/backfill_bellboard.py --delay 3

Source: BellBoard, https://bb.ringingworld.co.uk -- API docs at
https://bb.ringingworld.co.uk/help/api.php

API parameters discovered:
- export.php accepts 'from' and 'to' parameters for date ranges (YYYY-MM-DD format)
- export.php rejects pagesize > 10000 with HTTP 413
- date_from and date_to are NOT valid parameters (return 0 results)
- changed_since orders by modification date, not performance date

The backfill uses dated windows (from/to) rather than changed_since to ensure
a proper historical walk. Each window is checkpointed as pending/complete in
a local state file, so a resumed run skips completed windows.

Throttling: BellBoard answers sustained querying by silently truncating
responses (returning HTTP 200 with fewer rows than requested). This script:
- Keeps inter-page delay at 3s minimum (configurable)
- Treats short pages as potential throttling, backs off and re-fetches
- Increases backoff exponentially on repeated short pages
- Tracks throttle events and reports them

Writes are idempotent: INSERT OR REPLACE on BellBoard's own ID, child rows
cleared before reinsert. Overlapping windows converge, not duplicate.
"""
import argparse
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
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

# Default configuration
DEFAULT_START_DATE = "2012-01-01"  # BellBoard coverage starts around here
DEFAULT_WINDOW_DAYS = 30  # Small enough that losing one to a crash is cheap
DEFAULT_DELAY = 5.0  # Seconds between windows (on top of page delays)
CHECKPOINT_FILE = "bellboard_backfill_checkpoint.json"


def parse_date(date_str):
    """Parse a date string in YYYY-MM-DD format."""
    return datetime.strptime(date_str, "%Y-%m-%d").date()


def format_date(date_obj):
    """Format a date object as YYYY-MM-DD string."""
    return date_obj.isoformat()


def load_checkpoint(checkpoint_path):
    """Load checkpoint state from file.
    
    Returns:
        dict: checkpoint state with 'completed', 'pending', 'start_date', 'end_date'
    """
    if not os.path.exists(checkpoint_path):
        return {
            "completed": [],
            "pending": [],
            "start_date": None,
            "end_date": None,
        }
    with open(checkpoint_path, "r") as f:
        return json.load(f)


def save_checkpoint(checkpoint_path, state):
    """Save checkpoint state to file."""
    with open(checkpoint_path, "w") as f:
        json.dump(state, f, indent=2)


def generate_windows(start_date, end_date, window_days):
    """Generate date windows from start_date to end_date.
    
    Args:
        start_date: datetime.date - start of the range
        end_date: datetime.date - end of the range
        window_days: int - size of each window in days
        
    Yields:
        tuple: (window_start, window_end) as datetime.date objects
    """
    current = start_date
    while current <= end_date:
        window_end = min(current + timedelta(days=window_days - 1), end_date)
        yield (current, window_end)
        current = window_end + timedelta(days=1)


def window_key(window_start, window_end):
    """Create a unique key for a window."""
    return f"{format_date(window_start)}_{format_date(window_end)}"


def process_window(conn, date_from, date_to, delay, max_pages=0):
    """Process a single date window, fetching all pages.
    
    Args:
        conn: libsql connection
        date_from: start date (YYYY-MM-DD string)
        date_to: end date (YYYY-MM-DD string)
        delay: seconds between page fetches
        max_pages: maximum pages to fetch (0 = no limit)
        
    Returns:
        tuple: (total_performances, throttle_events, pages_fetched)
    """
    total = 0
    page = 1
    throttle_events = 0
    pages_fetched = 0
    
    while True:
        if max_pages and page > max_pages:
            print(f"  Reached max_pages {max_pages}; stopping.")
            break
            
        print(f"  Fetching page {page} for {date_from} to {date_to}...")
        
        try:
            perfs = fetch_performances(date_from=date_from, date_to=date_to, page=page, pagesize=PAGE_SIZE)
        except RuntimeError as exc:
            print(f"  ERROR: {exc}", file=sys.stderr)
            return total, throttle_events, pages_fetched
        
        pages_fetched += 1
        
        if not perfs:
            print(f"  Empty page; done with window.")
            break
        
        # Check for throttling: short page might be throttling or end of data
        if len(perfs) < PAGE_SIZE:
            # Back off and re-fetch to confirm
            cooloff = max(delay * 5, 15)
            print(
                f"  Short page ({len(perfs)} < {PAGE_SIZE}) -- could be end or throttling; "
                f"waiting {cooloff:.0f}s and re-checking"
            )
            time.sleep(cooloff)
            throttle_events += 1
            
            try:
                retry = fetch_performances(date_from=date_from, date_to=date_to, page=page, pagesize=PAGE_SIZE)
            except RuntimeError as exc:
                print(f"  ERROR on retry: {exc}", file=sys.stderr)
                return total, throttle_events, pages_fetched
            
            if len(retry) > len(perfs):
                print(f"  Re-fetch returned {len(retry)}; was throttled, continuing")
                perfs = retry
            else:
                print(f"  Re-fetch returned {len(retry)}; treating as end of window")
        
        # Parse and insert performances
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
        
        # Clear child rows for these performances
        if perf_rows:
            ids = [str(r[0]) for r in perf_rows]
            for chunk in (ids[i : i + 400] for i in range(0, len(ids), 400)):
                id_list = ",".join(chunk)
                for tbl in ("performance_ringers", "performance_footnotes", "performance_flags"):
                    conn.execute(f'DELETE FROM "{tbl}" WHERE "perf_id" IN ({id_list})')
        
        # Insert data (ingested_at is already included in perf_row from parse_performance)
        insert_many(conn, "performances", PERF_COLS, perf_rows)
        insert_many(conn, "performance_ringers",
                    ["perf_id", "position", "bell", "name", "conductor"], ringers)
        insert_many(conn, "performance_footnotes",
                    ["perf_id", "position", "footnote"], footnotes)
        insert_many(conn, "performance_flags",
                    ["perf_id", "position", "flag_type", "bell", "flag_text"], flags)
        conn.commit()
        
        total += len(perf_rows)
        print(f"  Page {page}: {len(perf_rows)} performances, {len(ringers)} ringers")
        
        if len(perfs) < PAGE_SIZE:
            break
            
        page += 1
        time.sleep(delay)
    
    return total, throttle_events, pages_fetched


def main() -> int:
    parser = argparse.ArgumentParser(
        description="BellBoard historical backfill runner (resumable)"
    )
    parser.add_argument(
        "--start",
        default=DEFAULT_START_DATE,
        help="Start date for backfill (YYYY-MM-DD, default: 2012-01-01)",
    )
    parser.add_argument(
        "--end",
        default=format_date(datetime.now().date()),
        help="End date for backfill (YYYY-MM-DD, default: today)",
    )
    parser.add_argument(
        "--window-days",
        type=int,
        default=DEFAULT_WINDOW_DAYS,
        help=f"Size of each date window in days (default: {DEFAULT_WINDOW_DAYS})",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=DEFAULT_DELAY,
        help=f"Seconds between windows (default: {DEFAULT_DELAY})",
    )
    parser.add_argument(
        "--page-delay",
        type=float,
        default=3.0,
        help="Seconds between page fetches within a window (default: 3.0)",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from existing checkpoint",
    )
    parser.add_argument(
        "--checkpoint",
        default=CHECKPOINT_FILE,
        help=f"Checkpoint file path (default: {CHECKPOINT_FILE})",
    )
    parser.add_argument(
        "--max-windows",
        type=int,
        default=0,
        help="Maximum windows to process (0 = no limit, useful for testing)",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=0,
        help="Maximum pages per window (0 = no limit, useful for testing)",
    )
    db.add_db_args(parser)
    args = parser.parse_args()

    # Parse dates
    try:
        start_date = parse_date(args.start)
        end_date = parse_date(args.end)
    except ValueError as e:
        print(f"ERROR: Invalid date format: {e}", file=sys.stderr)
        return 1

    if start_date > end_date:
        print(f"ERROR: Start date {args.start} is after end date {args.end}", file=sys.stderr)
        return 1

    conn = db.connect(args)

    # Load checkpoint
    checkpoint_path = args.checkpoint
    state = load_checkpoint(checkpoint_path)
    
    # If resuming, use checkpoint dates
    if args.resume and state.get("start_date") and state.get("end_date"):
        start_date = parse_date(state["start_date"])
        end_date = parse_date(state["end_date"])
        print(f"Resuming backfill from {args.start} to {args.end}")
    else:
        # Start fresh
        state = {
            "completed": [],
            "pending": [],
            "start_date": format_date(start_date),
            "end_date": format_date(end_date),
        }
        save_checkpoint(checkpoint_path, state)
        print(f"Starting new backfill from {args.start} to {args.end}")
    
    # Generate all windows
    all_windows = list(generate_windows(start_date, end_date, args.window_days))
    print(f"Total windows to process: {len(all_windows)}")
    print(f"Window size: {args.window_days} days")
    
    # Track progress
    total_performances = 0
    total_throttle_events = 0
    total_pages = 0
    windows_completed = 0
    windows_skipped = 0
    
    # Process each window
    for i, (win_start, win_end) in enumerate(all_windows):
        if args.max_windows and windows_completed >= args.max_windows:
            print(f"Reached max_windows {args.max_windows}; stopping.")
            break
        
        window_key_val = window_key(win_start, win_end)
        
        # Check if already completed
        if window_key_val in state.get("completed", []):
            print(f"Window {i+1}/{len(all_windows)}: {format_date(win_start)} to {format_date(win_end)} - SKIPPED (already completed)")
            windows_skipped += 1
            continue
        
        # Mark as pending
        if window_key_val not in state.get("pending", []):
            state.setdefault("pending", []).append(window_key_val)
            save_checkpoint(checkpoint_path, state)
        
        date_from = format_date(win_start)
        date_to = format_date(win_end)
        
        print(f"\nWindow {i+1}/{len(all_windows)}: {date_from} to {date_to}")
        
        # Process the window
        perf_count, throttle_count, page_count = process_window(
            conn,
            date_from,
            date_to,
            args.page_delay,
            args.max_pages
        )
        
        total_performances += perf_count
        total_throttle_events += throttle_count
        total_pages += page_count
        
        if perf_count > 0 or page_count > 0:
            # Mark as completed
            if window_key_val in state.get("pending", []):
                state["pending"].remove(window_key_val)
            state.setdefault("completed", []).append(window_key_val)
            save_checkpoint(checkpoint_path, state)
            windows_completed += 1
            print(f"  -> Completed: {perf_count} performances, {page_count} pages, {throttle_count} throttle events")
        else:
            print(f"  -> No data found")
        
        # Delay between windows
        if i < len(all_windows) - 1:
            time.sleep(args.delay)
    
    # Final stats
    print(f"\n{'='*60}")
    print(f"Backfill Summary:")
    print(f"  Windows processed: {windows_completed + windows_skipped}")
    print(f"  Windows completed: {windows_completed}")
    print(f"  Windows skipped: {windows_skipped}")
    print(f"  Total performances: {total_performances}")
    print(f"  Total pages fetched: {total_pages}")
    print(f"  Throttle events: {total_throttle_events}")
    
    # Database stats
    for tbl in ("performances", "performance_ringers", "performance_footnotes", "performance_flags"):
        n = conn.execute(f'SELECT COUNT(*) FROM "{tbl}"').fetchall()[0][0]
        print(f"  {tbl}: {n}")
    
    linked = conn.execute("SELECT COUNT(*) FROM v_tower_performances").fetchall()[0][0]
    print(f"  v_tower_performances (linked to Dove tower): {linked}")
    
    # Checkpoint stats
    print(f"\nCheckpoint state saved to {checkpoint_path}:")
    print(f"  Completed windows: {len(state.get('completed', []))}")
    print(f"  Pending windows: {len(state.get('pending', []))}")
    
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
