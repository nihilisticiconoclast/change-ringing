#!/usr/bin/env python3
"""
BellBoard historical backfill runner -- loads INTO A DATABASE.

There are two BellBoard fetchers and choosing the wrong one wastes a long run,
so: this one loads into a database; `fetch_and_export_bellboard.py` writes the
yearly CSVs under `data/bellboard/` that the repository actually commits and
that `build_local_db.py` reads. **The 2012-2024 corpus in this repository was
produced by the exporter, not by this script.**

Both use the same completeness gate -- `bellboard_common.fetch_expected_count`
and `WINDOW_TOLERANCE` -- so neither is more trustworthy than the other about
whether a window came back whole. What this one adds is resumability: a
checkpoint file, `--resume`, `--reset-checkpoint` and `--window-tolerance`, for
a run long enough that it may be interrupted. Reach for it when loading directly
to a database, which cannot happen before the Turso freeze lifts on 2026-09-01.

An audit PR proposed labelling this file a "prototype" and pointing readers at
the exporter. That has it backwards -- this is the more capable of the two -- but
the confusion it came from is real, which is why the distinction is now written
here rather than left to be inferred from two similar filenames.

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

    # Discard any existing checkpoint and start a fresh run
    python scripts/backfill_bellboard.py --reset-checkpoint

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

Completeness gate (the lesson of the 2026-08-09 run -- see
docs/decisions/002-backfill-count-discrepancy.md). The previous runner
checkpointed windows that BellBoard had silently truncated, so a run that
captured 16% of the corpus reported success. export.php carries no row-count
signal of its own, and a truncated last page is indistinguishable from a
genuine last page. So this runner asks search.php how many performances a
window should hold, and refuses to checkpoint a window whose fetched total
falls materially short. A run that cannot fill its windows exits non-zero
rather than printing success.

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
    WINDOW_TOLERANCE,
    fetch_expected_count,
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

# Bumped when the checkpoint shape changes, so a checkpoint written by an
# older runner is discarded rather than inherited -- the 2026-08-09 run marked
# truncated windows complete, so resuming it would have carried the gap
# forward. A version mismatch is treated the same as "no checkpoint": start
# fresh.
CHECKPOINT_VERSION = 2

# How many times to retry a window that comes up short of its expected count
# before giving up on it (and therefore on the run). Each retry waits longer
# than the one before.
DEFAULT_MAX_WINDOW_RETRIES = 3
# Seconds added to the cool-off on each successive retry of a short window.
RETRY_BACKOFF = 30

# Runtime tolerance, seeded from bellboard_common.WINDOW_TOLERANCE (0.0,
# measured) and overridable with --window-tolerance. Module-level rather than
# threaded through every call because is_short() is used from three places and
# a tolerance that differs between them would be worse than either value.
TOLERANCE = WINDOW_TOLERANCE


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
        return blank_state(None, None)
    with open(checkpoint_path, "r") as f:
        state = json.load(f)
    # A checkpoint from the pre-gate runner (or any future shape change) is
    # not safe to resume from: it may mark truncated windows complete. Drop
    # it and start clean rather than inheriting the gap.
    if state.get("version") != CHECKPOINT_VERSION:
        print(
            f"Discarding checkpoint {checkpoint_path}: version "
            f"{state.get('version')!r} != current {CHECKPOINT_VERSION}. "
            f"Starting fresh (an older checkpoint may record truncated "
            f"windows as complete).",
            file=sys.stderr,
        )
        return blank_state(None, None)
    return state


def blank_state(start_date, end_date):
    """A fresh checkpoint state for a given (possibly None) date range."""
    return {
        "version": CHECKPOINT_VERSION,
        "completed": [],
        "failed": [],
        "pending": [],
        "start_date": format_date(start_date) if start_date else None,
        "end_date": format_date(end_date) if end_date else None,
    }


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


def is_short(fetched, expected):
    """Whether a window's fetched total is materially below expectation.

    expected may be None, meaning search.php reported no performances for the
    window. In that case any fetched rows are a surprise (and are reported),
    but zero is the correct, complete answer.
    """
    if expected is None:
        return fetched > 0
    threshold = expected * (1 - TOLERANCE)
    return fetched < threshold


def fetch_window_rows(date_from, date_to, delay, max_pages=0):
    """Fetch every page of a date window from export.php.

    Returns:
        tuple: (perf_elements, throttle_events, pages_fetched)

    perf_elements is the list of <performance> XML elements across all pages,
    in fetch order. Throttling is handled by re-fetching a short page once
    after a cool-off: if the re-fetch returns more rows it was throttling, so
    the larger result is kept; if not, the short page is taken as the genuine
    last page. (The completeness gate -- comparing against search.php -- is
    what catches a truncated page that looks like a genuine last page, since
    export.php gives no total of its own.)
    """
    perfs = []
    page = 1
    throttle_events = 0
    pages_fetched = 0

    while True:
        if max_pages and page > max_pages:
            print(f"  Reached max_pages {max_pages}; stopping.")
            break

        print(f"  Fetching page {page} for {date_from} to {date_to}...")

        try:
            page_perfs = fetch_performances(
                date_from=date_from, date_to=date_to, page=page, pagesize=PAGE_SIZE
            )
        except RuntimeError as exc:
            print(f"  ERROR: {exc}", file=sys.stderr)
            return perfs, throttle_events, pages_fetched

        pages_fetched += 1

        if not page_perfs:
            print(f"  Empty page; done with window.")
            break

        # Check for throttling: short page might be throttling or end of data
        if len(page_perfs) < PAGE_SIZE:
            # Back off and re-fetch to confirm
            cooloff = max(delay * 5, 15)
            print(
                f"  Short page ({len(page_perfs)} < {PAGE_SIZE}) -- could be end or throttling; "
                f"waiting {cooloff:.0f}s and re-checking"
            )
            time.sleep(cooloff)
            throttle_events += 1

            try:
                retry = fetch_performances(
                    date_from=date_from, date_to=date_to, page=page, pagesize=PAGE_SIZE
                )
            except RuntimeError as exc:
                print(f"  ERROR on retry: {exc}", file=sys.stderr)
                return perfs, throttle_events, pages_fetched

            if len(retry) > len(page_perfs):
                print(f"  Re-fetch returned {len(retry)}; was throttled, continuing")
                page_perfs = retry
            else:
                print(f"  Re-fetch returned {len(retry)}; treating as end of window")

        perfs.extend(page_perfs)
        print(f"  Page {page}: {len(page_perfs)} performances (window total {len(perfs)})")

        if len(page_perfs) < PAGE_SIZE:
            break

        page += 1
        time.sleep(delay)

    return perfs, throttle_events, pages_fetched


def store_performances(conn, perf_elements):
    """Parse and insert a window's performances.

    Returns:
        tuple: (unique_records, duplicates_seen, ringers, footnotes, flags)

    unique_records counts DISTINCT perf_ids, not rows, and that distinction is
    the whole gate. search.php's expected count is a count of performances, so
    comparing it against a row count that includes duplicates lets a window of
    re-fetched records pass: 1,000 unique plus 800 duplicates measures 1,800
    against an expected 1,792, is checkpointed complete, and leaves 792 records
    missing from the database -- which is precisely the pathology the
    size-signal investigation identifies (see
    docs/decisions/002-backfill-count-discrepancy.md). Compare like with like.

    duplicates_seen counts perf_ids that appeared more than once within this
    batch. A non-zero value means export.php returned the same record on more
    than one page, and the caller fails the window on it rather than accepting
    the unique count, because duplicates in a clean fetch are themselves
    evidence that the fetch was not clean.
    """
    perf_rows, ringers, footnotes, flags = [], [], [], []
    seen_ids = set()
    duplicates_seen = 0
    for p in perf_elements:
        parsed = parse_performance(p)
        if parsed is None:
            continue
        pr, rg, fn, fl = parsed
        pid = pr[0]
        if pid in seen_ids:
            duplicates_seen += 1
        else:
            seen_ids.add(pid)
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

    return len(seen_ids), duplicates_seen, len(ringers), len(footnotes), len(flags)


def process_window(conn, date_from, date_to, delay, max_pages=0,
                   expected=None, max_retries=DEFAULT_MAX_WINDOW_RETRIES):
    """Process a single date window, fetching all pages and checking completeness.

    Args:
        conn: libsql connection
        date_from: start date (YYYY-MM-DD string)
        date_to: end date (YYYY-MM-DD string)
        delay: seconds between page fetches
        max_pages: maximum pages to fetch (0 = no limit)
        expected: row count search.php reports for this window, or None if it
            reported none. When provided, a fetched total materially below
            this is treated as truncation and retried; a window that cannot
            be filled after max_retries attempts is reported as failed.
        max_retries: how many times to re-attempt a short window before
            giving up on it.

    Returns:
        dict with keys: rows, throttle_events, pages_fetched, duplicates,
        expected, attempts, complete (bool), short (bool)
    """
    result = {
        "rows": 0, "throttle_events": 0, "pages_fetched": 0, "duplicates": 0,
        "expected": expected, "attempts": 0, "complete": False, "short": False,
    }

    attempt = 0
    while True:
        attempt += 1
        result["attempts"] = attempt
        perfs, throttle, pages = fetch_window_rows(
            date_from, date_to, delay, max_pages
        )
        result["throttle_events"] += throttle
        result["pages_fetched"] += pages

        rows, dups, _rg, _fn, _fl = store_performances(conn, perfs)
        result["rows"] = rows          # DISTINCT perf_ids, not rows fetched
        result["duplicates"] += dups

        # No independent count to check against: accept whatever we got. This
        # is the genuine empty-window case (search.php said "no performances
        # matching"), not a truncation we are papering over.
        if expected is None:
            result["complete"] = True
            if rows:
                # Unexpected: search.php said the window was empty but
                # export.php returned rows. Flag it rather than trust either
                # silently.
                result["short"] = True
                print(
                    f"  WARNING: search.php reported no performances for "
                    f"{date_from}..{date_to} but export.php returned {rows}. "
                    f"Accepting but flagging.",
                    file=sys.stderr,
                )
            else:
                print(f"  Empty window (search.php agrees); complete.")
            return result

        if dups:
            # Not a shortfall, but not a clean fetch either. export.php returning
            # the same record twice within one window is the signal the broken
            # 2026-08-09 run left behind, so treat it as a reason to retry rather
            # than something to note and move past.
            result["short"] = True
            print(
                f"  DUPLICATES: export.php returned {dups} repeated perf_id(s) "
                f"within this window; treating as an unclean fetch.",
                file=sys.stderr,
            )
        elif not is_short(rows, expected):
            result["complete"] = True
            print(
                f"  Window complete: {rows} unique performances vs {expected} "
                f"expected"
                + (f" (within {TOLERANCE:.0%} tolerance)" if TOLERANCE else "")
            )
            return result

        # Short of expectation: BellBoard truncated the window. Retry with a
        # longer cool-off before giving up.
        result["short"] = True
        if attempt > max_retries:
            print(
                f"  SHORT: {rows} fetched vs {expected} expected after "
                f"{attempt} attempts -- truncation not resolved; marking "
                f"window FAILED.",
                file=sys.stderr,
            )
            return result

        cooloff = RETRY_BACKOFF * attempt
        print(
            f"  SHORT: {rows} fetched vs {expected} expected -- likely "
            f"truncation. Cooling off {cooloff}s and re-fetching the whole "
            f"window (attempt {attempt}/{max_retries}).",
            file=sys.stderr,
        )
        time.sleep(cooloff)


def fetch_expected_for_range(start_date, end_date):
    """Ground-truth row count for the whole backfill range, from search.php.

    Returns int or None. None means search.php reported no performances for
    the range, which for a real backfill range is itself a red flag -- but the
    caller decides what to do with it.
    """
    return fetch_expected_count(format_date(start_date), format_date(end_date))


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
        "--reset-checkpoint",
        action="store_true",
        help="Discard any existing checkpoint and start a fresh run.",
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
    parser.add_argument(
        "--max-window-retries",
        type=int,
        default=DEFAULT_MAX_WINDOW_RETRIES,
        help=f"Retries for a window that comes up short of its expected count "
             f"before failing the run (default: {DEFAULT_MAX_WINDOW_RETRIES})",
    )
    parser.add_argument(
        "--window-tolerance",
        type=float,
        default=WINDOW_TOLERANCE,
        help=f"Fraction of a window's expected count that may be missing and "
             f"still count as complete (default: {WINDOW_TOLERANCE:g}). The "
             f"default is zero because search.php and export.php were measured "
             f"agreeing exactly across six windows; raise it only with a "
             f"measurement to justify it.",
    )
    parser.add_argument(
        "--skip-count-gate",
        action="store_true",
        help="Do not query search.php for per-window or final expected "
             "counts. Only for testing against a source that does not honour "
             "search.php; a real backfill must leave this off.",
    )
    db.add_db_args(parser)
    args = parser.parse_args()

    global TOLERANCE
    TOLERANCE = args.window_tolerance
    if TOLERANCE:
        print(f"NOTE: window tolerance set to {TOLERANCE:.1%}; a window missing "
              f"up to that fraction will still be checkpointed as complete.",
              file=sys.stderr)

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
    if args.reset_checkpoint and os.path.exists(checkpoint_path):
        print(f"Discarding existing checkpoint {checkpoint_path} (--reset-checkpoint).")
        os.remove(checkpoint_path)
    state = load_checkpoint(checkpoint_path)

    # If resuming, use checkpoint dates -- but only if the checkpoint is
    # usable (right version, has dates). A version mismatch was already
    # turned into a blank state by load_checkpoint.
    if args.resume and state.get("start_date") and state.get("end_date"):
        start_date = parse_date(state["start_date"])
        end_date = parse_date(state["end_date"])
        print(f"Resuming backfill from {format_date(start_date)} to {format_date(end_date)}")
    else:
        # Start fresh
        state = blank_state(start_date, end_date)
        save_checkpoint(checkpoint_path, state)
        print(f"Starting new backfill from {format_date(start_date)} to {format_date(end_date)}")

    # Generate all windows
    all_windows = list(generate_windows(start_date, end_date, args.window_days))
    print(f"Total windows to process: {len(all_windows)}")
    print(f"Window size: {args.window_days} days")

    # Ground-truth corpus count for the whole range, queried once up front so
    # a run that cannot even reach search.php fails fast rather than after
    # hours of fetching. This is also the number the final total is compared
    # against.
    corpus_expected = None
    if not args.skip_count_gate:
        print(f"\nQuerying search.php for the corpus count over "
              f"{format_date(start_date)}..{format_date(end_date)}...")
        try:
            corpus_expected = fetch_expected_for_range(start_date, end_date)
        except RuntimeError as exc:
            print(f"ERROR: could not reach search.php for the corpus count: {exc}",
                  file=sys.stderr)
            conn.close()
            return 1
        if corpus_expected is None:
            print(f"ERROR: search.php reports no performances for "
                  f"{format_date(start_date)}..{format_date(end_date)}. "
                  f"Check the date range; refusing to run a backfill whose "
                  f"corpus size is unknown.", file=sys.stderr)
            conn.close()
            return 1
        print(f"  Corpus reports {corpus_expected:,} performances for the range.")

    # Track progress
    total_performances = 0
    total_throttle_events = 0
    total_pages = 0
    total_duplicates = 0
    windows_completed = 0
    windows_skipped = 0
    windows_failed = []

    # Process each window
    for i, (win_start, win_end) in enumerate(all_windows):
        if args.max_windows and windows_completed >= args.max_windows:
            print(f"Reached max_windows {args.max_windows}; stopping.")
            break

        wk = window_key(win_start, win_end)

        # Check if already completed
        if wk in state.get("completed", []):
            print(f"Window {i+1}/{len(all_windows)}: {format_date(win_start)} to "
                  f"{format_date(win_end)} - SKIPPED (already completed)")
            windows_skipped += 1
            continue

        # Mark as pending
        if wk not in state.get("pending", []):
            state.setdefault("pending", []).append(wk)
            save_checkpoint(checkpoint_path, state)

        date_from = format_date(win_start)
        date_to = format_date(win_end)

        print(f"\nWindow {i+1}/{len(all_windows)}: {date_from} to {date_to}")

        # Per-window expected count. This is the gate: a window fetched short
        # of this is retried, and one that cannot be filled is failed rather
        # than checkpointed. --skip-count-gate disables it for tests against a
        # source without search.php; a real run must leave it on.
        expected = None
        if not args.skip_count_gate:
            try:
                expected = fetch_expected_count(date_from, date_to)
            except RuntimeError as exc:
                print(f"  ERROR fetching expected count: {exc}", file=sys.stderr)
                # Could not get ground truth for this window: do NOT
                # checkpoint it as complete. Stop the run loudly.
                windows_failed.append(wk)
                state.setdefault("failed", []).append(wk)
                save_checkpoint(checkpoint_path, state)
                print(f"  -> FAILED: could not establish expected count; "
                      f"stopping run.", file=sys.stderr)
                break
            if expected is not None:
                print(f"  search.php expects {expected} performances for this window.")
            else:
                print(f"  search.php reports no performances for this window.")

        res = process_window(
            conn,
            date_from,
            date_to,
            args.page_delay,
            args.max_pages,
            expected=expected,
            max_retries=args.max_window_retries,
        )

        total_performances += res["rows"]
        total_throttle_events += res["throttle_events"]
        total_pages += res["pages_fetched"]
        total_duplicates += res["duplicates"]

        if res["complete"]:
            if wk in state.get("pending", []):
                state["pending"].remove(wk)
            state.setdefault("completed", []).append(wk)
            save_checkpoint(checkpoint_path, state)
            windows_completed += 1
            print(f"  -> Completed: {res['rows']} performances, "
                  f"{res['pages_fetched']} pages, {res['throttle_events']} "
                  f"throttle events"
                  + (f", {res['duplicates']} duplicate perf_ids within window"
                     if res["duplicates"] else ""))
        else:
            # Short and unfixable: do NOT checkpoint as complete. Record it
            # as failed and stop the run -- silence is the bug this gate
            # exists to prevent.
            windows_failed.append(wk)
            state.setdefault("failed", []).append(wk)
            if wk in state.get("pending", []):
                state["pending"].remove(wk)
            save_checkpoint(checkpoint_path, state)
            print(f"  -> FAILED: {res['rows']} fetched vs {expected} expected "
                  f"after {res['attempts']} attempts; NOT checkpointed. "
                  f"Stopping run.", file=sys.stderr)
            break

        # Delay between windows
        if i < len(all_windows) - 1:
            time.sleep(args.delay)

    # Final stats
    print(f"\n{'='*60}")
    print(f"Backfill Summary:")
    print(f"  Windows processed: {windows_completed + windows_skipped}")
    print(f"  Windows completed: {windows_completed}")
    print(f"  Windows skipped:  {windows_skipped}")
    print(f"  Windows failed:   {len(windows_failed)}")
    print(f"  Total performances fetched: {total_performances}")
    print(f"  Total pages fetched: {total_pages}")
    print(f"  Throttle events: {total_throttle_events}")
    if total_duplicates:
        print(f"  Duplicate perf_ids within windows: {total_duplicates} "
              f"(export.php returned the same record on more than one page)")

    # Database stats. The backfill tables always exist, but the Dove
    # join view does not unless the Dove schema was also loaded -- a
    # backfill-only database is a legitimate target, so its absence is
    # reported rather than treated as a failure that aborts the run.
    for tbl in ("performances", "performance_ringers", "performance_footnotes", "performance_flags"):
        n = conn.execute(f'SELECT COUNT(*) FROM "{tbl}"').fetchall()[0][0]
        print(f"  {tbl}: {n}")

    try:
        linked = conn.execute("SELECT COUNT(*) FROM v_tower_performances").fetchall()[0][0]
        print(f"  v_tower_performances (linked to Dove tower): {linked}")
    except Exception:
        print("  v_tower_performances: (Dove schema not loaded in this DB; skipped)")

    # Checkpoint stats
    print(f"\nCheckpoint state saved to {checkpoint_path}:")
    print(f"  Completed windows: {len(state.get('completed', []))}")
    print(f"  Pending windows:   {len(state.get('pending', []))}")
    print(f"  Failed windows:    {len(state.get('failed', []))}")

    # Final total check. A backfill that ends materially below the corpus
    # count has failed, whether or not every window individually passed: the
    # point of the gate is that silence is the bug. Compare rows in the
    # database for the range against search.php's count for the range.
    failed = False
    if windows_failed:
        failed = True
        print(f"\nFAILED: {len(windows_failed)} window(s) could not be filled to "
              f"their expected count and were not checkpointed.", file=sys.stderr)
    if not args.skip_count_gate and corpus_expected is not None:
        db_in_range = conn.execute(
            'SELECT COUNT(*) FROM "performances" WHERE "perf_date" >= ? '
            'AND "perf_date" <= ?',
            (format_date(start_date), format_date(end_date)),
        ).fetchall()[0][0]
        print(f"\nFinal total check:")
        print(f"  search.php corpus count for range: {corpus_expected:,}")
        print(f"  performances in DB for range:      {db_in_range:,}")
        if is_short(db_in_range, corpus_expected):
            failed = True
            print(f"  MISMATCH: DB holds {db_in_range:,} against an expected "
                  f"{corpus_expected:,} -- the backfill is incomplete.",
                  file=sys.stderr)
        else:
            print("  OK: matches the corpus count."
                  if not TOLERANCE else
                  f"  OK: within {TOLERANCE:.0%} of the corpus count.")

    conn.close()

    if failed:
        print("\nBackfill did NOT complete cleanly. See errors above.",
              file=sys.stderr)
        return 1

    print("\nBackfill complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
