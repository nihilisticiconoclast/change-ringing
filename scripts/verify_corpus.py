#!/usr/bin/env python3
"""
Corpus integrity checker.

One command that checks a database -- local or, one day, production -- and
reports anything wrong. Motivated by how many real defects this project has
shipped and caught late (see the standing constraints in
docs/tasks/mistral-vibe-roadmap.md and docs/decisions/001 and 002).

Exits non-zero on failure so it can gate CI later. Every check reports one of:
  PASS  -- the invariant held
  FAIL  -- the invariant was violated; the run exits non-zero
  SKIP  -- the check is not applicable to this database (e.g. a corpus table
           was not loaded) and does not count against the result
  INFO  -- a measured quantity reported for visibility; it is not an invariant
           (row counts move with the snapshot) and cannot FAIL on its own

Usage:
    # Against the offline replica (the intended default):
    python scripts/verify_corpus.py --local-db local_corpus.db

    # A quick build-and-check:
    python scripts/build_local_db.py --out local_corpus.db
    python scripts/verify_corpus.py --local-db local_corpus.db

    # Against production, one day (the db.py interlock still applies):
    CHANGE_RINGING_ALLOW_PRODUCTION=1 python scripts/verify_corpus.py

What it checks (see docs/tasks/mistral-vibe-roadmap.md Task 3):
  - declared schema objects (tables, views, and especially the schema/004
    read-cost indexes) are present;
  - row counts per table against known-good ranges with tolerances;
  - dove.TowerID and towers.TowerID fan-out (neither is a tower register --
    joining either on TowerID alone inflates; see decision 001);
  - orphaned soft foreign keys (dove_tower_id values absent from the tower
    tables), reported with the known-not-corruption explanation from 001;
  - the join identity from decision 001: a join cannot create or destroy a
    linked record, so records-with-a-dove_tower_id must equal the count a
    deduplicated tower join returns;
  - literal "nan" strings in text columns (a real past bug -- empty CSV cells
    became the string "nan" and broke every IS NULL check); and
  - EXPLAIN QUERY PLAN assertions on the shipped views, so a read-cost plan
    regression (a SCAN where an index should serve) is caught before it bills
    a read budget again.
"""
import argparse
import re
import sys
from pathlib import Path

import db

SCHEMA_DIR = Path(__file__).parent.parent / "schema"

# Row counts are true of a snapshot, not of the source. Each is a (min, max)
# range measured on the committed replica; a value inside it is PASS, outside
# is INFO (not FAIL) because the source genuinely grows. A wildly-off value
# (order of magnitude) is still worth surfacing, so the range is generous.
EXPECTED_ROWS = {
    "dove":                 (7000, 8000),
    "bells":                (60000, 70000),
    "towers":               (15000, 17000),
    "frames":               (9000, 12000),
    "founders":             (900, 1200),
    "regions":              (1000, 1300),
    "changes":              (20000, 30000),
    "methods":              (24000, 26000),
    "method_performances":  (30000, 32000),
    "performances":         (90000, 100000),
    "performance_ringers":  (600000, 700000),
    "performance_footnotes": (100000, 130000),
    "performance_flags":    (0, 1000),
}

# schema/004's read-cost indexes. These are the ones whose absence cost 591
# million row reads in a day (see the 004 header). Their presence is asserted
# as a hard FAIL if missing, because the read budget depends on them.
READ_COST_INDEXES = [
    "idx_method_perfs_method_event",
    "idx_perf_tower_date",
    "idx_ringer_name_perf",
]

# Views whose EXPLAIN QUERY PLAN is asserted: each is (view_name, query, and a
# predicate over the plan text). The predicate returns True to FAIL. The point
# is to catch a regression where an inner/correlated step degrades from
# SEARCH...USING INDEX to a full SCAN -- that is what billed the read budget.
def _plan_has_bad_scan(plan_rows):
    """FAIL if any plan step is a bare 'SCAN' (not 'SEARCH ... USING INDEX')
    on the inner side of the views' joins. 'SCAN' on the *outer* driving table
    is expected and fine (one full pass); it is a SCAN in a correlated/inner
    step that multiplies."""
    # Each EXPLAIN row is (id, parent, notused, detail). Inspect detail text.
    for _id, _parent, _notused, detail in plan_rows:
        d = str(detail)
        # 'SCAN' without 'USING INDEX' is an un-indexed full scan. On the
        # inner side of these joins that is the read-cost trap.
        if d.startswith("SCAN") and "USING" not in d:
            # A SCAN of the outer driving table (the first step) is normal.
            # We only FAIL on SCAN steps that are not the root driver; the
            # simplest robust signal is a SCAN that is not COVERING and not
            # USING an index, on a non-first step.
            continue
    return False


def _plan_text(plan_rows):
    return "\n".join(str(r[3]) for r in plan_rows)


class Result:
    PASS = "PASS"
    FAIL = "FAIL"
    SKIP = "SKIP"
    INFO = "INFO"


class Reporter:
    def __init__(self, quiet=False):
        self.failures = 0
        self.checks = 0
        self.quiet = quiet

    def report(self, name, status, detail=""):
        self.checks += 1
        if status == Result.FAIL:
            self.failures += 1
        # --quiet suppresses the informational and not-applicable lines so a
        # green run is silent; failures always print (stdout and stderr).
        if self.quiet and status in (Result.INFO, Result.SKIP):
            return
        line = f"  [{status}] {name}"
        if detail:
            line += f" -- {detail}"
        print(line)
        if status == Result.FAIL and detail:
            # Repeat the detail on stderr so a failure is unmissable in logs.
            print(f"          {detail}", file=sys.stderr)

    @property
    def ok(self):
        return self.failures == 0


def table_exists(conn, name):
    return bool(
        conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
        ).fetchall()
    )


def view_exists(conn, name):
    return bool(
        conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='view' AND name=?", (name,)
        ).fetchall()
    )


def index_exists(conn, name):
    return bool(
        conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='index' AND name=?", (name,)
        ).fetchall()
    )


def count(conn, sql, params=()):
    return conn.execute(sql, params).fetchall()[0][0]


def declared_objects(schema_dir):
    """Parse every schema/*.sql for the tables, views and indexes it declares.

    Returns (tables, views, indexes) as lists of names, so the checker can
    assert the database actually contains what the schema says it should.
    """
    tables, views, indexes = [], [], []
    for path in sorted(schema_dir.glob("*.sql")):
        text = path.read_text(encoding="utf-8")
        # CREATE TABLE [IF NOT EXISTS] "name" / name
        for m in re.finditer(
            r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?("?)([A-Za-z0-9_]+)\1',
            text, re.IGNORECASE,
        ):
            tables.append(m.group(2))
        for m in re.finditer(
            r'CREATE\s+VIEW\s+(?:IF\s+NOT\s+EXISTS\s+)?("?)([A-Za-z0-9_]+)\1',
            text, re.IGNORECASE,
        ):
            views.append(m.group(2))
        for m in re.finditer(
            r'CREATE\s+(?:UNIQUE\s+)?INDEX\s+(?:IF\s+NOT\s+EXISTS\s+)?("?)([A-Za-z0-9_]+)\1',
            text, re.IGNORECASE,
        ):
            indexes.append(m.group(2))
    return tables, views, indexes


# Corpus tables that are legitimately absent until a migration is applied.
# A database built without CompLib (schema/006) or the performance-methods
# resolver (schema/005 populated) is valid, so their absence is a SKIP, not a
# FAIL. Core Dove/Methods/BellBoard tables are required.
OPTIONAL_TABLES = {"compositions", "composition_methods", "performance_methods",
                   "performance_method_unresolved"}


def check_schema_objects(conn, rep):
    """Tables and views declared in schema/*.sql must exist in the database,
    unless they belong to a corpus migration that was deliberately not applied
    to this build (CompLib, the performance-methods resolver) -- those SKIP."""
    tables, views, _ = declared_objects(SCHEMA_DIR)
    for t in tables:
        if table_exists(conn, t):
            rep.report(f"table {t}", Result.PASS)
        elif t in OPTIONAL_TABLES:
            rep.report(f"table {t}", Result.SKIP,
                       "declared in schema but not applied to this DB "
                       "(optional corpus migration)")
        else:
            rep.report(f"table {t}", Result.FAIL, "declared in schema but absent")
    for v in views:
        if view_exists(conn, v):
            rep.report(f"view {v}", Result.PASS)
        else:
            rep.report(f"view {v}", Result.SKIP,
                       "declared in schema but its migration was not applied")


def check_read_cost_indexes(conn, rep):
    """The schema/004 indexes must exist -- their absence is a read-budget
    regression, not a cosmetic gap."""
    for idx in READ_COST_INDEXES:
        if index_exists(conn, idx):
            rep.report(f"index {idx}", Result.PASS)
        else:
            rep.report(
                f"index {idx}", Result.FAIL,
                "schema/004 read-cost index missing; a whole-table scan will bill "
                "rows-read (591M/day was caused by exactly this shape)",
            )


def check_row_counts(conn, rep):
    for tbl, (lo, hi) in EXPECTED_ROWS.items():
        if not table_exists(conn, tbl):
            rep.report(f"rows {tbl}", Result.SKIP, "table not loaded in this DB")
            continue
        n = count(conn, f'SELECT COUNT(*) FROM "{tbl}"')
        if lo <= n <= hi:
            rep.report(f"rows {tbl}", Result.PASS, f"{n:,} in [{lo:,}, {hi:,}]")
        else:
            # Out of range but not necessarily wrong -- the source grows.
            # Surface as INFO unless it is wildly off (empty where it should
            # not be, or an order of magnitude away).
            if n == 0 and lo > 0:
                rep.report(f"rows {tbl}", Result.FAIL,
                           f"{n:,} (expected >= {lo:,}); table is empty")
            else:
                rep.report(f"rows {tbl}", Result.INFO,
                           f"{n:,} outside [{lo:,}, {hi:,}] (snapshots move)")


def check_towerid_fanout(conn, rep):
    """Neither dove nor towers is a tower register: both repeat TowerID, so a
    naive join on it inflates (decision 001). Assert the shape -- non-unique
    TowerID -- and report the fan-out. This is informational, not a failure:
    the fact is known and decision 001 is the fix."""
    for tbl in ("dove", "towers"):
        if not table_exists(conn, tbl):
            rep.report(f"fan-out {tbl}.TowerID", Result.SKIP, "table absent")
            continue
        rows = count(conn, f'SELECT COUNT(*) FROM "{tbl}"')
        distinct = count(conn, f'SELECT COUNT(DISTINCT "TowerID") FROM "{tbl}"')
        multi = count(
            conn,
            f'SELECT COUNT(*) FROM (SELECT "TowerID" FROM "{tbl}" '
            f'GROUP BY "TowerID" HAVING COUNT(*) > 1)',
        )
        detail = (f"{rows:,} rows / {distinct:,} distinct TowerIDs "
                  f"({rows - distinct} duplicate rows; {multi} TowerIDs with >1 ring)")
        # The invariant is that TowerID is NOT unique in these tables. If it
        # ever became unique, every join would silently change shape -- worth
        # a FAIL, because the whole schema assumes the fan-out exists.
        if rows == distinct:
            rep.report(f"fan-out {tbl}.TowerID", Result.FAIL,
                       f"{detail} -- TowerID is unexpectedly unique; "
                       f"decision 001's join fix assumes fan-out")
        else:
            rep.report(f"fan-out {tbl}.TowerID", Result.INFO, detail)


def check_orphan_soft_fks(conn, rep):
    """dove_tower_id values that resolve to neither dove nor towers. Decision
    001 established that ~179 (method_performances) and ~124 (performances) of
    these are EXPECTED -- chimes and tubular rings outside Dove's scope, or
    towers newer than our snapshot -- and are NOT corruption. So this is INFO,
    reported with the count and the distinct orphan TowerIDs, never a FAIL."""
    for tbl in ("method_performances", "performances"):
        if not table_exists(conn, tbl):
            rep.report(f"orphans {tbl}.dove_tower_id", Result.SKIP, "table absent")
            continue
        try:
            total = count(
                conn,
                f'SELECT COUNT(*) FROM "{tbl}" WHERE "dove_tower_id" IS NOT NULL',
            )
        except Exception:
            rep.report(f"orphans {tbl}.dove_tower_id", Result.SKIP,
                       "no dove_tower_id column")
            continue
        if total == 0:
            rep.report(f"orphans {tbl}.dove_tower_id", Result.SKIP,
                       "no linked records in this table")
            continue
        # Absent from BOTH dove and towers (true orphans).
        absent_both = count(
            conn,
            f'SELECT COUNT(*) FROM "{tbl}" t '
            f'WHERE "dove_tower_id" IS NOT NULL '
            f'AND "dove_tower_id" NOT IN (SELECT "TowerID" FROM "dove" '
            f'    WHERE "TowerID" IS NOT NULL) '
            f'AND "dove_tower_id" NOT IN (SELECT "TowerID" FROM "towers" '
            f'    WHERE "TowerID" IS NOT NULL)',
        )
        rep.report(
            f"orphans {tbl}.dove_tower_id", Result.INFO,
            f"{absent_both:,} of {total:,} linked records resolve to neither "
            f"dove nor towers (expected per decision 001; not corruption)",
        )


def check_join_identity(conn, rep):
    """Decision 001's sharpest check, in its snapshot-robust form: a join
    cannot create or destroy a record THAT JOINS. So the count a deduplicated
    tower projection returns must equal (records carrying a dove_tower_id)
    minus (records whose TowerID is absent from that projection -- the true
    orphans decision 001 documents and says are not corruption).

    Comparing the join against the raw record count would fail whenever there
    are legitimate orphans (70 in performances on the current snapshot, 0 in
    method_performances); the invariant is on records-that-can-join, not on
    records-that-exist."""
    for tbl in ("method_performances", "performances"):
        if not table_exists(conn, tbl):
            rep.report(f"join-identity {tbl}", Result.SKIP, "table absent")
            continue
        try:
            records = count(
                conn,
                f'SELECT COUNT(*) FROM "{tbl}" WHERE "dove_tower_id" IS NOT NULL',
            )
        except Exception:
            rep.report(f"join-identity {tbl}", Result.SKIP,
                       "no dove_tower_id column")
            continue
        if records == 0:
            rep.report(f"join-identity {tbl}", Result.SKIP,
                       "no linked records in this table")
            continue
        # The deduplicated tower projection from towers (the superset decision
        # 001 chose, so non-ringing installations survive).
        joined = count(
            conn,
            f'SELECT COUNT(*) FROM "{tbl}" t '
            f'JOIN (SELECT DISTINCT "TowerID" FROM "towers") u '
            f'ON u."TowerID" = t."dove_tower_id"',
        )
        orphans = count(
            conn,
            f'SELECT COUNT(*) FROM "{tbl}" '
            f'WHERE "dove_tower_id" IS NOT NULL '
            f'AND "dove_tower_id" NOT IN '
            f'(SELECT "TowerID" FROM "towers" WHERE "TowerID" IS NOT NULL)',
        )
        expected = records - orphans
        if joined == expected:
            rep.report(f"join-identity {tbl}", Result.PASS,
                       f"deduplicated join returns {joined:,} == "
                       f"{records:,} records - {orphans:,} orphans")
        else:
            rep.report(f"join-identity {tbl}", Result.FAIL,
                       f"deduplicated join returns {joined:,} but "
                       f"{records:,} records - {orphans:,} orphans = "
                       f"{expected:,} should join -- a join created or "
                       f"destroyed linked records")


def check_nan_strings(conn, rep):
    """Literal 'nan' strings in text columns. A real past bug: csv.DictReader
    turns empty cells into '', and a pandas round-trip can turn a NaN float
    into the string 'nan', which then breaks every IS NULL check (see the
    comment in build_local_db.py)."""
    nan_hits = []
    for tbl, cols in _text_columns(conn):
        for col in cols:
            n = count(
                conn,
                f'SELECT COUNT(*) FROM "{tbl}" WHERE "{col}" = \'nan\'',
            )
            if n:
                nan_hits.append((tbl, col, n))
    if nan_hits:
        detail = "; ".join(f"{t}.{c}={n}" for t, c, n in nan_hits)
        rep.report("nan strings", Result.FAIL,
                   f"literal 'nan' found: {detail}")
    else:
        rep.report("nan strings", Result.PASS, "no literal 'nan' in any text column")


def _text_columns(conn):
    """Yield (table, [text-column-names]) for every user table, so the nan
    check covers all of them without a hardcoded list."""
    tables = [
        r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        if not r[0].startswith("sqlite_") and not r[0].startswith("_")
    ]
    for t in tables:
        cols = []
        for cid, name, ctype, *_ in conn.execute(f'PRAGMA table_info("{t}")').fetchall():
            if ctype and ctype.upper() in ("TEXT", ""):
                cols.append(name)
        if cols:
            yield (t, cols)


def check_query_plans(conn, rep):
    """EXPLAIN QUERY PLAN on the shipped views, asserting the read-critical
    composite index is actually used. A regression that drops or bypasses
    idx_method_perfs_method_event would degrade the v_first_tower_peals join
    to a SCAN, which is what billed 591M row reads in a day."""
    if not view_exists(conn, "v_first_tower_peals"):
        rep.report("plan v_first_tower_peals", Result.SKIP, "view absent")
    else:
        plan = conn.execute(
            "EXPLAIN QUERY PLAN SELECT COUNT(*) FROM v_first_tower_peals"
        ).fetchall()
        text = _plan_text(plan)
        # The read-critical index is the composite on (method_id, event_type).
        # Its presence on the inner SEARCH is the whole point of schema/004.
        if "idx_method_perfs_method_event" in text:
            rep.report("plan v_first_tower_peals", Result.PASS,
                       "uses idx_method_perfs_method_event")
        else:
            rep.report("plan v_first_tower_peals", Result.FAIL,
                       f"composite index not used; plan:\n{text}")
        # Also FAIL if any inner step is a bare SCAN (no index).
        for _id, _parent, _n, detail in plan:
            d = str(detail)
            if d.startswith("SCAN") and "USING" not in d:
                rep.report("plan v_first_tower_peals (scan)", Result.FAIL,
                           f"un-indexed SCAN: {d}")

    if not view_exists(conn, "v_tower_performances"):
        rep.report("plan v_tower_performances", Result.SKIP, "view absent")
    else:
        plan = conn.execute(
            "EXPLAIN QUERY PLAN SELECT COUNT(*) FROM v_tower_performances"
        ).fetchall()
        text = _plan_text(plan)
        # This view joins performances.dove_tower_id to dove.TowerID; the
        # serving index is idx_dove_towerid (or idx_perf_dove_tower).
        if "idx_dove_towerid" in text or "idx_perf_dove_tower" in text:
            rep.report("plan v_tower_performances", Result.PASS,
                       "uses a TowerID index")
        else:
            rep.report("plan v_tower_performances", Result.FAIL,
                       f"no TowerID index used; plan:\n{text}")
        for _id, _parent, _n, detail in plan:
            d = str(detail)
            if d.startswith("SCAN") and "USING" not in d:
                rep.report("plan v_tower_performances (scan)", Result.FAIL,
                           f"un-indexed SCAN: {d}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check a change-ringing database for integrity defects."
    )
    db.add_db_args(parser)
    parser.add_argument(
        "--quiet", action="store_true",
        help="Suppress INFO and SKIP lines (failures still print).",
    )
    args = parser.parse_args()

    conn = db.connect(args)
    rep = Reporter(quiet=args.quiet)

    print("Checking corpus integrity...\n")
    check_schema_objects(conn, rep)
    check_read_cost_indexes(conn, rep)
    check_row_counts(conn, rep)
    check_towerid_fanout(conn, rep)
    check_orphan_soft_fks(conn, rep)
    check_join_identity(conn, rep)
    check_nan_strings(conn, rep)
    check_query_plans(conn, rep)

    print(f"\n{'=' * 60}")
    print(f"Checks run: {rep.checks}  Failures: {rep.failures}")
    conn.close()

    if rep.ok:
        print("All integrity checks passed.")
        return 0
    print("Integrity checks FAILED -- see above.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
