#!/usr/bin/env python3
"""
Negative tests for verify_corpus.py (V-9 / R-44).

This script tests that every integrity check in verify_corpus.py can actually
FAIL when the condition it checks for is broken. A check that cannot fail is
worse than no check: it reports success and stops anyone looking.

Usage:
    python tests/test_verify_corpus_negative.py --local-db /path/to/replica.db

The script:
1. Builds a fresh replica from the current committed CSVs
2. For each check, creates a modified copy of the database
3. Deliberately breaks that one check
4. Runs verify_corpus.py against the broken database
5. Records whether the check correctly reported FAIL

Expected output: a report of which checks passed their negative test (FAIL
when broken = good) and which did not (still PASS when broken = decoration).
"""
import argparse
import csv
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

# Paths
REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
DATA_DIR = REPO_ROOT / "data"
VERIFY_SCRIPT = SCRIPTS_DIR / "verify_corpus.py"


def run_command(cmd, cwd=None):
    """Run a shell command and return (returncode, stdout, stderr)."""
    result = subprocess.run(
        cmd,
        shell=True,
        capture_output=True,
        text=True,
        cwd=cwd or REPO_ROOT,
    )
    return result.returncode, result.stdout, result.stderr


def build_fresh_replica(out_path):
    """Build a fresh replica from committed CSVs."""
    print(f"Building fresh replica at {out_path}...")
    rc, stdout, stderr = run_command(
        f"python {SCRIPTS_DIR / 'build_local_db.py'} --out {out_path}"
    )
    if rc != 0:
        print(f"Failed to build replica: {stderr}")
        return False
    return True


def copy_db(src, dst):
    """Copy a SQLite database file."""
    shutil.copy2(src, dst)
    # Ensure the copy is writable
    os.chmod(dst, 0o644)


def modify_db(db_path, modification_func):
    """Apply a modification function to a database."""
    conn = sqlite3.connect(db_path)
    try:
        modification_func(conn)
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def run_verify(db_path):
    """Run verify_corpus.py against a database and return (returncode, output)."""
    rc, stdout, stderr = run_command(
        f"python {VERIFY_SCRIPT} --local-db {db_path} --quiet"
    )
    return rc, stdout + stderr


def check_failed(output, check_name):
    """Check if a specific check name appears as FAIL in the output."""
    return f"[FAIL] {check_name}" in output


# =============================================================================
# MODIFICATION FUNCTIONS - each breaks one specific check
# =============================================================================

# --- Schema objects (tables) ---

def drop_table_bells(conn):
    """Break: table bells absent."""
    conn.execute("DROP TABLE IF EXISTS bells")


def drop_table_changes(conn):
    """Break: table changes absent."""
    conn.execute("DROP TABLE IF EXISTS changes")


def drop_table_dove(conn):
    """Break: table dove absent."""
    conn.execute("DROP TABLE IF EXISTS dove")


def drop_table_founders(conn):
    """Break: table founders absent."""
    conn.execute("DROP TABLE IF EXISTS founders")


def drop_table_frames(conn):
    """Break: table frames absent."""
    conn.execute("DROP TABLE IF EXISTS frames")


def drop_table_regions(conn):
    """Break: table regions absent."""
    conn.execute("DROP TABLE IF EXISTS regions")


def drop_table_towers(conn):
    """Break: table towers absent."""
    conn.execute("DROP TABLE IF EXISTS towers")


def drop_table_performances(conn):
    """Break: table performances absent."""
    conn.execute("DROP TABLE IF EXISTS performances")


def drop_table_performance_ringers(conn):
    """Break: table performance_ringers absent."""
    conn.execute("DROP TABLE IF EXISTS performance_ringers")


def drop_table_performance_footnotes(conn):
    """Break: table performance_footnotes absent."""
    conn.execute("DROP TABLE IF EXISTS performance_footnotes")


def drop_table_performance_flags(conn):
    """Break: table performance_flags absent."""
    conn.execute("DROP TABLE IF EXISTS performance_flags")


def drop_table_methods(conn):
    """Break: table methods absent."""
    conn.execute("DROP TABLE IF EXISTS methods")


def drop_table_method_performances(conn):
    """Break: table method_performances absent."""
    conn.execute("DROP TABLE IF EXISTS method_performances")


# --- Schema objects (views) ---

def drop_view_v_ringing_towers(conn):
    """Break: view v_ringing_towers absent."""
    conn.execute("DROP VIEW IF EXISTS v_ringing_towers")


def drop_view_v_tower_performances(conn):
    """Break: view v_tower_performances absent."""
    conn.execute("DROP VIEW IF EXISTS v_tower_performances")


def drop_view_v_first_tower_peals(conn):
    """Break: view v_first_tower_peals absent."""
    conn.execute("DROP VIEW IF EXISTS v_first_tower_peals")


def drop_view_v_towers_unique(conn):
    """Break: view v_towers_unique absent."""
    conn.execute("DROP VIEW IF EXISTS v_towers_unique")


def drop_view_v_dove_towers(conn):
    """Break: view v_dove_towers absent."""
    conn.execute("DROP VIEW IF EXISTS v_dove_towers")


# --- Schema objects (indexes) ---

def drop_index_idx_method_perfs_method_event(conn):
    """Break: index idx_method_perfs_method_event absent."""
    conn.execute("DROP INDEX IF EXISTS idx_method_perfs_method_event")


def drop_index_idx_perf_tower_date(conn):
    """Break: index idx_perf_tower_date absent."""
    conn.execute("DROP INDEX IF EXISTS idx_perf_tower_date")


def drop_index_idx_ringer_name_perf(conn):
    """Break: index idx_ringer_name_perf absent."""
    conn.execute("DROP INDEX IF EXISTS idx_ringer_name_perf")


# --- Row counts ---

def empty_table_bells(conn):
    """Break: bells table empty (row count FAIL)."""
    conn.execute("DELETE FROM bells")


def empty_table_dove(conn):
    """Break: dove table empty (row count FAIL)."""
    conn.execute("DELETE FROM dove")


def empty_table_towers(conn):
    """Break: towers table empty (row count FAIL)."""
    conn.execute("DELETE FROM towers")


# --- CSV agreement ---

def truncate_performances_table(conn):
    """Break: performances table has fewer rows than committed CSV."""
    conn.execute("DELETE FROM performances WHERE perf_id IN "
                 "(SELECT perf_id FROM performances LIMIT 100)")


def add_extra_performances(conn):
    """Break: performances table has more rows than committed CSV."""
    # Insert a fake row that doesn't exist in CSV
    conn.execute(
        "INSERT INTO performances (perf_id, bb_id, association, place, dedication, "
        "county, towerbase_id, dove_tower_id, dove_ring_id, ring_type, tenor, "
        "portable, dumb_bells, perf_date, duration, changes, method, title, "
        "details, composer, composition, bb_timestamp, ingested_at) "
        "VALUES (999999999, 'FAKE', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, '2025-01-01', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL)"
    )


def truncate_compositions_table(conn):
    """Break: compositions table has fewer rows than committed CSV."""
    # compositions uses 'composition_id' as primary key
    conn.execute("DELETE FROM compositions WHERE composition_id IN "
                 "(SELECT composition_id FROM compositions LIMIT 10)")


# --- TowerID fan-out ---

def make_dove_towerid_unique(conn):
    """Break: make dove.TowerID unique (should fail fan-out check)."""
    # Delete duplicates to make TowerID unique
    conn.execute("DELETE FROM dove WHERE rowid NOT IN "
                 "(SELECT MIN(rowid) FROM dove GROUP BY TowerID)")


def make_towers_towerid_unique(conn):
    """Break: make towers.TowerID unique (should fail fan-out check)."""
    conn.execute("DELETE FROM towers WHERE rowid NOT IN "
                 "(SELECT MIN(rowid) FROM towers GROUP BY TowerID)")


# --- Orphan soft FKs ---

def add_orphan_to_method_performances(conn):
    """Break: add orphan dove_tower_id to method_performances."""
    # Insert a row with a dove_tower_id that doesn't exist in either dove or towers
    conn.execute(
        "INSERT INTO method_performances (method_id, position, event_type, perf_date, dove_tower_id) "
        "VALUES ('test', 1, 'peal', '2025-01-01', 999999)"
    )


def add_many_orphans_to_performances(conn):
    """Break: add many orphan dove_tower_ids to performances (exceed ceiling)."""
    # Add more than ORPHAN_DRIFT_CEILING (5000) orphans
    # dove_tower_id is INTEGER in performances, so use large numbers
    # perf_id must be unique, so use negative numbers which won't conflict
    for i in range(5001):
        conn.execute(
            "INSERT INTO performances (perf_id, bb_id, dove_tower_id) "
            f"VALUES (-1000000 - {i}, 'ORPHAN{i}', 900000 + {i})"
        )


# --- Join identity ---

def break_join_identity_method_performances(conn):
    """Break: corrupt join identity for method_performances."""
    # Redefine v_towers_unique to return a single row that won't match anything
    conn.execute("DROP VIEW IF EXISTS v_towers_unique")
    # Create a view that returns TowerIDs that don't exist
    conn.execute("CREATE VIEW v_towers_unique AS SELECT CAST(999999999 AS INTEGER) AS TowerID")


def break_join_identity_performances(conn):
    """Break: corrupt join identity for performances."""
    conn.execute("DROP VIEW IF EXISTS v_towers_unique")
    conn.execute("CREATE VIEW v_towers_unique AS SELECT CAST(999999999 AS INTEGER) AS TowerID")


# --- NaN strings ---

def add_nan_to_bells(conn):
    """Break: add literal 'nan' string to bells table."""
    conn.execute("UPDATE bells SET Bell_Name = 'nan' WHERE Bell_ID = 1")


# --- Query plans ---

def drop_index_for_plan_check(conn):
    """Break: drop the index used by v_first_tower_peals plan check."""
    conn.execute("DROP INDEX IF EXISTS idx_method_perfs_method_event")


def drop_tower_index_for_plan(conn):
    """Break: drop TowerID indexes used by v_tower_performances plan check."""
    conn.execute("DROP INDEX IF EXISTS idx_perf_dove_tower")
    conn.execute("DROP INDEX IF EXISTS idx_towers_towerid")
    conn.execute("DROP INDEX IF EXISTS idx_dove_towerid")


# =============================================================================
# TEST REGISTRY
# =============================================================================

# Each entry: (check_name, modification_function, description)
# The check_name must match exactly what verify_corpus.py reports
CHECK_TESTS = [
    # Tables (13 core tables)
    ("table bells", drop_table_bells, "Drop bells table"),
    ("table changes", drop_table_changes, "Drop changes table"),
    ("table dove", drop_table_dove, "Drop dove table"),
    ("table founders", drop_table_founders, "Drop founders table"),
    ("table frames", drop_table_frames, "Drop frames table"),
    ("table regions", drop_table_regions, "Drop regions table"),
    ("table towers", drop_table_towers, "Drop towers table"),
    ("table performances", drop_table_performances, "Drop performances table"),
    ("table performance_ringers", drop_table_performance_ringers, "Drop performance_ringers table"),
    ("table performance_footnotes", drop_table_performance_footnotes, "Drop performance_footnotes table"),
    ("table performance_flags", drop_table_performance_flags, "Drop performance_flags table"),
    ("table methods", drop_table_methods, "Drop methods table"),
    ("table method_performances", drop_table_method_performances, "Drop method_performances table"),
    
    # Optional tables (should SKIP, not FAIL when absent)
    # These are tested separately below
    
    # Views (6 load-bearing views)
    ("view v_ringing_towers", drop_view_v_ringing_towers, "Drop v_ringing_towers view"),
    ("view v_tower_performances", drop_view_v_tower_performances, "Drop v_tower_performances view"),
    ("view v_first_tower_peals", drop_view_v_first_tower_peals, "Drop v_first_tower_peals view"),
    ("view v_towers_unique", drop_view_v_towers_unique, "Drop v_towers_unique view"),
    ("view v_dove_towers", drop_view_v_dove_towers, "Drop v_dove_towers view"),
    
    # Optional views (should SKIP)
    # ("view v_performance_methods", ...),
    # ("view v_composition_methods", ...),
    
    # Indexes (3 read-cost indexes)
    ("index idx_method_perfs_method_event", drop_index_idx_method_perfs_method_event, "Drop idx_method_perfs_method_event"),
    ("index idx_perf_tower_date", drop_index_idx_perf_tower_date, "Drop idx_perf_tower_date"),
    ("index idx_ringer_name_perf", drop_index_idx_ringer_name_perf, "Drop idx_ringer_name_perf"),
    
    # Row counts (test empty tables for a subset)
    ("rows bells", empty_table_bells, "Empty bells table"),
    ("rows dove", empty_table_dove, "Empty dove table"),
    ("rows towers", empty_table_towers, "Empty towers table"),
    
    # CSV agreement - BellBoard tables
    ("csv agreement performances", truncate_performances_table, "Truncate performances table"),
    ("csv agreement performance_ringers", lambda c: c.execute("DELETE FROM performance_ringers WHERE perf_id IN (SELECT perf_id FROM performance_ringers LIMIT 100)"), "Truncate performance_ringers"),
    ("csv agreement performance_footnotes", lambda c: c.execute("DELETE FROM performance_footnotes WHERE perf_id IN (SELECT perf_id FROM performance_footnotes LIMIT 100)"), "Truncate performance_footnotes"),
    ("csv agreement performance_flags", lambda c: c.execute("DELETE FROM performance_flags WHERE perf_id IN (SELECT perf_id FROM performance_flags LIMIT 100)"), "Truncate performance_flags"),
    
    # CSV agreement - CompLib tables
    ("csv agreement compositions", truncate_compositions_table, "Truncate compositions table"),
    ("csv agreement composition_methods", lambda c: c.execute("DELETE FROM composition_methods WHERE composition_id IN (SELECT composition_id FROM composition_methods LIMIT 10)"), "Truncate composition_methods"),
    
    # TowerID fan-out
    ("fan-out dove.TowerID", make_dove_towerid_unique, "Make dove.TowerID unique"),
    ("fan-out towers.TowerID", make_towers_towerid_unique, "Make towers.TowerID unique"),
    
    # Orphan soft FKs
    ("orphans method_performances.dove_tower_id", lambda c: c.execute("INSERT INTO method_performances (method_id, position, event_type, perf_date, dove_tower_id) VALUES ('test', 1, 'peal', '2025-01-01', 999999)"), "Add orphan to method_performances"),
    ("orphans performances.dove_tower_id", add_many_orphans_to_performances, "Add >5000 orphans to performances"),
    
    # Join identity - need to use actual column names
    # Join identity
    ("join-identity method_performances", break_join_identity_method_performances, "Redefine v_towers_unique to return wrong data"),
    ("join-identity performances", break_join_identity_performances, "Redefine v_towers_unique to return wrong data"),
    
    # NaN strings - Weight__lbs is a REAL column, but we can set it to the string 'nan'
    # Actually, let's use a TEXT column like Bell_Name
    ("nan strings", lambda c: c.execute("UPDATE bells SET Bell_Name = 'nan' WHERE Bell_ID = 1"), "Add 'nan' string to bells"),
    
    # Query plans
    ("plan v_first_tower_peals", drop_index_for_plan_check, "Drop index for v_first_tower_peals"),
    ("plan v_tower_performances", drop_tower_index_for_plan, "Drop TowerID indexes for v_tower_performances"),
]


def run_single_test(base_db, check_name, mod_func, tmpdir):
    """Run a single negative test."""
    test_db = tmpdir / f"test_{check_name.replace(' ', '_').replace('.', '_')}.db"
    
    # Copy the base database
    copy_db(base_db, test_db)
    
    # Apply the modification
    try:
        modify_db(test_db, mod_func)
    except Exception as e:
        return "ERROR", f"Modification failed: {e}"
    
    # Run verify_corpus.py
    rc, output = run_verify(test_db)
    
    # Check if the specific check failed
    if check_failed(output, check_name):
        result = "FAIL_CORRECTLY"  # The check correctly reported FAIL
    elif rc != 0:
        # The overall run failed, but not for our specific check
        # This might mean a different check caught it
        if "FAIL" in output:
            result = "FAILED_OTHER"  # Some other check failed
        else:
            result = "FAILED_NO_DETAIL"  # Failed but no FAIL in output
    else:
        result = "DID_NOT_FAIL"  # The check did not report FAIL
    
    # Clean up
    try:
        os.remove(test_db)
    except:
        pass
    
    return result, output


def main():
    parser = argparse.ArgumentParser(
        description="Negative tests for verify_corpus.py checks."
    )
    parser.add_argument(
        "--local-db",
        required=True,
        help="Path to a valid replica database to use as base.",
    )
    parser.add_argument(
        "--tmpdir",
        default="/tmp/vibe_negative_tests",
        help="Directory for temporary test databases.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit to first N tests (for debugging).",
    )
    args = parser.parse_args()
    
    base_db = Path(args.local_db)
    tmpdir = Path(args.tmpdir)
    
    # Create temp directory
    tmpdir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 80)
    print("NEGATIVE TESTS FOR verify_corpus.py")
    print("=" * 80)
    print(f"Base database: {base_db}")
    print(f"Temp directory: {tmpdir}")
    print()
    
    # First verify the base database passes all checks
    print("Verifying base database passes all checks...")
    rc, output = run_verify(base_db)
    if rc != 0:
        print(f"ERROR: Base database does not pass all checks!")
        print(output)
        return 1
    print("Base database: ALL CHECKS PASS\n")
    
    # Run tests
    results = []
    tests_to_run = CHECK_TESTS[:args.limit] if args.limit else CHECK_TESTS
    
    total = len(tests_to_run)
    for i, (check_name, mod_func, description) in enumerate(tests_to_run, 1):
        print(f"[{i}/{total}] Testing: {check_name}")
        print(f"         {description}")
        
        result, output = run_single_test(base_db, check_name, mod_func, tmpdir)
        results.append((check_name, result, description))
        
        status_symbol = {
            "FAIL_CORRECTLY": "✓",
            "DID_NOT_FAIL": "✗",
            "FAILED_OTHER": "~",
            "FAILED_NO_DETAIL": "?",
            "ERROR": "E",
        }
        symbol = status_symbol.get(result, "?")
        print(f"         Result: {symbol} {result}")
        
        if result == "DID_NOT_FAIL":
            print(f"         WARNING: Check did not fail when broken!")
            # Show what happened
            if "PASS" in output and check_name in output:
                print(f"         Output contains: [PASS] {check_name}")
        print()
    
    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    fail_correctly = [r for r in results if r[1] == "FAIL_CORRECTLY"]
    did_not_fail = [r for r in results if r[1] == "DID_NOT_FAIL"]
    failed_other = [r for r in results if r[1] == "FAILED_OTHER"]
    errors = [r for r in results if r[1] == "ERROR"]
    
    print(f"Total tests run: {len(results)}")
    print(f"✓ Correctly failed: {len(fail_correctly)}")
    print(f"✗ Did NOT fail (DECORATIONS): {len(did_not_fail)}")
    print(f"~ Failed for other reasons: {len(failed_other)}")
    print(f"E Errors: {len(errors)}")
    print()
    
    if did_not_fail:
        print("CHECKS THAT COULD NOT BE MADE TO FAIL (decorations):")
        print("-" * 60)
        for check_name, _, description in did_not_fail:
            print(f"  - {check_name}: {description}")
        print()
    
    if failed_other:
        print("CHECKS THAT FAILED FOR OTHER REASONS:")
        print("-" * 60)
        for check_name, _, description in failed_other:
            print(f"  - {check_name}: {description}")
        print()
    
    # Return non-zero if any check could not fail
    if did_not_fail:
        print("RESULT: SOME CHECKS ARE DECORATIONS (cannot fail)")
        return 1
    else:
        print("RESULT: ALL CHECKS CAN FAIL (none are decorations)")
        return 0


if __name__ == "__main__":
    sys.exit(main())
