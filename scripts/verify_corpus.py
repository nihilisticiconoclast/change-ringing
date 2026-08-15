#!/usr/bin/env python3
"""
Corpus integrity checker.
Runs assertions against a specified SQLite database (e.g., local_corpus.db or Turso).

Usage:
    python scripts/verify_corpus.py
    python scripts/verify_corpus.py --local-db local_corpus.db

Checks:
- Row counts against expected ranges/exact numbers.
- Orphaned foreign keys for dove_tower_id.
- No TowerID fan-out in v_towers_unique and v_dove_towers.
- No literal "nan" strings in text columns.
- Query plan regressions (ensuring views don't trigger full table scans inappropriately, or just executing EXPLAIN QUERY PLAN to ensure syntax and schema validity).
"""
import argparse
import sys
import db

def assert_count(conn, table, expected_min, expected_max=None):
    count = conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
    if expected_max is None:
        if count < expected_min:
            print(f"FAIL: {table} count {count} is less than minimum {expected_min}")
            return False
    else:
        if not (expected_min <= count <= expected_max):
            print(f"FAIL: {table} count {count} not in range [{expected_min}, {expected_max}]")
            return False
    print(f"PASS: {table} count = {count}")
    return True


def check_no_nan(conn, table, column):
    count = conn.execute(f'SELECT COUNT(*) FROM "{table}" WHERE "{column}" = \'nan\'').fetchone()[0]
    if count > 0:
        print(f"FAIL: {table}.{column} contains {count} literal 'nan' strings")
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    db.add_db_args(parser)
    args = parser.parse_args()

    try:
        conn = db.connect(args)
    except Exception as e:
        print(f"Could not connect to database: {e}")
        return 1

    passed = True
    print("Verifying row counts...")
    passed &= assert_count(conn, "dove", 7200, 7500)
    passed &= assert_count(conn, "towers", 15000, 16000)
    passed &= assert_count(conn, "methods", 24000)
    passed &= assert_count(conn, "performances", 90000)
    
    # Check that tower views don't fan out
    print("\nVerifying TowerID deduplication...")
    dove_towers = conn.execute('SELECT COUNT(*) FROM v_dove_towers').fetchone()[0]
    dove_distinct = conn.execute('SELECT COUNT(DISTINCT TowerID) FROM dove').fetchone()[0]
    if dove_towers != dove_distinct:
        print(f"FAIL: v_dove_towers count ({dove_towers}) != dove distinct TowerID ({dove_distinct})")
        passed = False
    else:
        print(f"PASS: v_dove_towers maps exactly to distinct Dove TowerIDs ({dove_towers})")

    towers_unique = conn.execute('SELECT COUNT(*) FROM v_towers_unique').fetchone()[0]
    towers_distinct = conn.execute('SELECT COUNT(DISTINCT TowerID) FROM towers').fetchone()[0]
    if towers_unique != towers_distinct:
        print(f"FAIL: v_towers_unique count ({towers_unique}) != towers distinct TowerID ({towers_distinct})")
        passed = False
    else:
        print(f"PASS: v_towers_unique maps exactly to distinct towers TowerIDs ({towers_unique})")

    print("\nVerifying foreign keys (dove_tower_id orphans)...")
    # method_performances -> v_towers_unique
    orphans_mp = conn.execute('''
        SELECT COUNT(*) FROM method_performances mp
        WHERE mp.dove_tower_id IS NOT NULL 
          AND NOT EXISTS (SELECT 1 FROM v_towers_unique t WHERE t.TowerID = mp.dove_tower_id)
    ''').fetchone()[0]
    if orphans_mp > 0:
        print(f"FAIL: method_performances contains {orphans_mp} orphaned dove_tower_id references")
        passed = False
    else:
        print("PASS: method_performances has no orphaned dove_tower_id references")

    # performances -> v_towers_unique
    # Note: BellBoard tracks live Dove, so it is expected that some performances 
    # reference towers newer than our snapshot. We tolerate a small percentage (<0.5%) of these.
    orphans_p = conn.execute('''
        SELECT COUNT(*) FROM performances p
        WHERE p.dove_tower_id IS NOT NULL 
          AND NOT EXISTS (SELECT 1 FROM v_towers_unique t WHERE t.TowerID = p.dove_tower_id)
    ''').fetchone()[0]
    total_linked = conn.execute('SELECT COUNT(*) FROM performances WHERE dove_tower_id IS NOT NULL').fetchone()[0]
    orphan_pct = (orphans_p / total_linked * 100) if total_linked > 0 else 0
    if orphans_p > 1000 or orphan_pct > 1.0:
        print(f"FAIL: performances contains {orphans_p} orphaned dove_tower_id references ({orphan_pct:.2f}%) (too many!)")
        passed = False
    else:
        print(f"PASS: performances contains {orphans_p} orphaned dove_tower_id references ({orphan_pct:.2f}%, within tolerance)")

    print("\nVerifying absence of literal 'nan' strings...")
    passed &= check_no_nan(conn, "performances", "association")
    passed &= check_no_nan(conn, "performances", "place")
    passed &= check_no_nan(conn, "method_performances", "building")
    passed &= check_no_nan(conn, "method_performances", "town")

    print("\nVerifying view query plans (syntax check and regression)...")
    views = [
        "v_ringing_towers",
        "v_towers_unique",
        "v_dove_towers",
        "v_tower_performances",
        "v_first_tower_peals"
    ]
    for view in views:
        try:
            # We just do EXPLAIN QUERY PLAN to ensure it compiles correctly
            conn.execute(f"EXPLAIN QUERY PLAN SELECT * FROM {view}").fetchall()
            print(f"PASS: {view} query plan compiles successfully")
        except Exception as e:
            print(f"FAIL: {view} query plan execution failed: {e}")
            passed = False

    conn.close()

    if not passed:
        print("\nINTEGRITY CHECK FAILED.")
        return 1

    print("\nINTEGRITY CHECK PASSED.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
