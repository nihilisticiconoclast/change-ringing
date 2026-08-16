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
    read-cost indexes) are present -- a missing view FAILs unless it belongs to
    a migration listed as optional;
  - **the replica agrees exactly with the committed CSVs.** The sharpest check
    here, and the only one that catches a database that is internally perfect
    and simply out of date -- which is what a merged backfill leaves behind
    until someone rebuilds;
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
import csv
import re
import sys
from pathlib import Path

import db

SCHEMA_DIR = Path(__file__).parent.parent / "schema"

# Row counts are true of a snapshot, not of the source. Each is a (min, max)
# range; a value inside it is PASS, outside is INFO (not FAIL) because the
# sources genuinely grow. A wildly-off value is still worth surfacing, so the
# ranges are generous.
#
# These are for the DOVE AND METHODS tables, which come from live sources and so
# genuinely drift. The BellBoard tables are NOT ranged here: they are built from
# CSVs committed in this repository, so their expected count is not a guess but
# an exact number, and check_csv_agreement asserts it. A range on a table whose
# true value is knowable is a weaker check pretending to be a stronger one --
# `performance_flags: (0, 1000)` passed at 0 for as long as flags existed,
# because 0 is in the range, while 25,030 committed rows were never loaded.
#
# Measured 2026-08-15 against the rebuilt replica.
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
}

# schema/004's read-cost indexes. These are the ones whose absence cost 591
# million row reads in a day (see the 004 header). Their presence is asserted
# as a hard FAIL if missing, because the read budget depends on them.
READ_COST_INDEXES = [
    "idx_method_perfs_method_event",
    "idx_perf_tower_date",
    "idx_ringer_name_perf",
]

# performances.dove_tower_id values resolving in neither `dove` nor `towers`.
# A handful is expected -- BellBoard tracks Dove live and this database holds a
# snapshot -- and decision 001 says not to "clean" them. It was 70 on the
# 2021-24 corpus and is 208 on 2018-24, so it scales with the corpus and no
# fixed figure is right. The ceiling is not a prediction, it is the line between
# "upstream drifted" and "a reload went wrong": thousands is never drift.
ORPHAN_DRIFT_CEILING = 5000

def _plan_text(plan_rows):
    return "\n".join(str(r[3]) for r in plan_rows)


_SCAN_RE = re.compile(r"^SCAN\s+(\w+)")


def bad_scans(conn, plan_rows):
    """The plan steps that are genuinely un-indexed scans of a base table.

    The rule matters more than it looks, because the obvious version is wrong in
    both directions.

    A bare `SCAN x` -- no `USING INDEX` -- is only a read-cost problem when `x`
    is a real table AND it is not the step driving the query. One full pass over
    the outer table is how a join starts; it is a SCAN on the *inner* side that
    multiplies, and that is what billed 591M rows-read in a day.

    It also has to skip aliases that are not tables at all. A view built on
    another view produces steps like `CO-ROUTINE v_towers_unique` followed by
    `SCAN d`, where `d` is the co-routine, already materialised. Failing on that
    would fail a healthy database -- and did: moving `v_tower_performances` onto
    `v_towers_unique` (decision 001) makes exactly that plan, so the cruder rule
    turned a correctness fix into a red build.

    Returns a list of offending detail strings, empty when the plan is fine.
    """
    tables = {
        r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type IN ('table','view')"
        ).fetchall()
    }
    bad = []
    for i, (_id, _parent, _notused, detail) in enumerate(plan_rows):
        d = str(detail)
        if i == 0 or "USING" in d:
            continue  # the driving step, or an indexed one
        m = _SCAN_RE.match(d)
        if m and m.group(1) in tables:
            bad.append(d)
    return bad


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

# Views belonging to those same optional migrations. Everything NOT listed here
# is load-bearing and its absence is a FAIL.
#
# This started as "every missing view is a SKIP", which sounds cautious and is
# the opposite. Proved during review by deleting `v_towers_unique` -- the entire
# artefact of decision 001, the thing this checker exists to defend -- from a
# copy of the database: the run reported SKIP and exited 0. A gate that shrugs
# when you remove the thing it guards is not a gate.
OPTIONAL_VIEWS = {"v_composition_methods", "v_performance_methods"}


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
        elif v in OPTIONAL_VIEWS:
            rep.report(f"view {v}", Result.SKIP,
                       "declared in schema but its migration was not applied")
        else:
            rep.report(f"view {v}", Result.FAIL,
                       "declared in schema but absent; this view is load-bearing "
                       "(see OPTIONAL_VIEWS for the ones that may be missing)")


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


def check_csv_agreement(conn, rep):
    """The replica must hold every row the committed CSVs hold.

    This is the one check here that caught a defect live in the repository the
    day it was written, and it is worth explaining why the others could not.

    `data/bellboard/*.csv` is the corpus; the database is a build product of it.
    Merging a year of CSVs without rebuilding leaves a database that is perfectly
    self-consistent -- every index present, every join identity holding, every
    row count inside its expected range -- and simply missing a year. Every check
    above passes. The published pages then get rebuilt from it and quietly report
    a corpus one year smaller than the one in the repository, with no error
    anywhere.

    That is exactly what happened after the 2020 backfill merged: the CSVs said
    106,756 performances, the replica said 96,067, and the README said 96,067
    too, because it had been written from the replica. The gap survived a merge
    review and two page rebuilds.

    A range check cannot catch this. Only comparing the database against the
    thing it is built from can, and that comparison is exact, not approximate:
    the CSVs are committed, so there is no snapshot drift to forgive.
    """
    bb = Path(__file__).resolve().parent.parent / "data" / "bellboard"
    if not bb.is_dir():
        rep.report("csv agreement", Result.SKIP, "data/bellboard not present")
        return
    csv.field_size_limit(1 << 27)  # footnote and composition fields are long

    def rows(path):
        with path.open(newline="", encoding="utf-8") as fh:
            r = csv.reader(fh)
            next(r, None)
            return sum(1 for _ in r)

    for stem, table in (("performances", "performances"),
                        ("ringers", "performance_ringers"),
                        ("footnotes", "performance_footnotes"),
                        ("flags", "performance_flags")):
        paths = sorted(bb.glob(f"{stem}_*.csv"))
        if not paths:
            rep.report(f"csv agreement {table}", Result.SKIP, "no CSVs committed")
            continue
        if not table_exists(conn, table):
            rep.report(f"csv agreement {table}", Result.SKIP, "table absent")
            continue
        expected = sum(rows(p) for p in paths)
        actual = count(conn, f'SELECT COUNT(*) FROM "{table}"')
        years = f"{len(paths)} year{'s' if len(paths) != 1 else ''}"
        if actual == expected:
            rep.report(f"csv agreement {table}", Result.PASS,
                       f"{actual:,} == {expected:,} across {years} of CSVs")
        elif actual > expected:
            # More in the DB than in the repo: rows loaded from a source that is
            # not committed. Not fatal, but the replica is then not reproducible
            # from this repository, which is the property the CSVs exist to give.
            rep.report(f"csv agreement {table}", Result.FAIL,
                       f"{actual:,} rows in the database but only {expected:,} "
                       f"in {years} of committed CSVs -- {actual - expected:,} "
                       f"rows came from somewhere not in this repository, so the "
                       f"replica cannot be rebuilt from it")
        else:
            rep.report(f"csv agreement {table}", Result.FAIL,
                       f"{actual:,} rows in the database but {expected:,} in "
                       f"{years} of committed CSVs -- {expected - actual:,} "
                       f"missing; the replica is stale, rebuild it with "
                       f"scripts/rebuild_all.py")

    # CompLib: same property for the fourth corpus. The CSVs are single files
    # per table (not split by year like BellBoard), so the check is a direct
    # one-to-one comparison. The API walk that produced them is
    # scripts/ingest_complib.py; scripts/load_complib_csv.py rebuilds from
    # them. Without this, a CompLib load from the API that is not committed
    # looks complete in every other check, exactly as the year-old BellBoard
    # replica once did.
    cl = Path(__file__).resolve().parent.parent / "data" / "complib"
    for csv_name, table in (("compositions.csv", "compositions"),
                            ("composition_methods.csv", "composition_methods")):
        path = cl / csv_name
        if not path.exists():
            # An absent CSV is only benign if the table is empty too. Rows in the
            # database with nothing committed behind them is the exact condition
            # this check exists to catch -- a load that happened on somebody's
            # machine and cannot be reproduced from the repository -- and
            # reporting SKIP there would announce success at the moment the check
            # stopped being able to see anything. Measured: with the CSV moved
            # aside and 86,054 rows still loaded, the first version skipped.
            n = count(conn, f'SELECT COUNT(*) FROM "{table}"') \
                if table_exists(conn, table) else 0
            if n:
                rep.report(f"csv agreement {table}", Result.FAIL,
                           f"{n:,} rows in the database and no committed CSV -- "
                           f"this data cannot be rebuilt from the repository")
            else:
                rep.report(f"csv agreement {table}", Result.SKIP,
                           "no CSV committed, table empty")
            continue
        if not table_exists(conn, table):
            rep.report(f"csv agreement {table}", Result.SKIP, "table absent")
            continue
        expected = rows(path)
        actual = count(conn, f'SELECT COUNT(*) FROM "{table}"')
        if actual == expected:
            rep.report(f"csv agreement {table}", Result.PASS,
                       f"{actual:,} == {expected:,} against committed CSV")
        elif actual > expected:
            rep.report(f"csv agreement {table}", Result.FAIL,
                       f"{actual:,} rows in the database but only {expected:,} "
                       f"in the committed CSV -- {actual - expected:,} rows came "
                       f"from somewhere not in this repository")
        else:
            rep.report(f"csv agreement {table}", Result.FAIL,
                       f"{actual:,} rows in the database but {expected:,} in the "
                       f"committed CSV -- {expected - actual:,} missing; rebuild "
                       f"with scripts/load_complib_csv.py")


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
        # The two tables are NOT the same kind of claim, and reporting both as
        # INFO -- which this did -- throws away the difference. Taken from Vibe's
        # second submission (PR #11), which got this right.
        #
        # method_performances.dove_tower_id was populated by adjudicating
        # candidates AGAINST `towers`. Every value in it was therefore chosen
        # because it resolves there, so an orphan is not drift, it is corruption
        # or a botched reload. Measured today: 0 of 22,117. That zero is an
        # invariant and should FAIL if it ever moves.
        #
        # performances.dove_tower_id comes from BellBoard, which tracks Dove live
        # while this database holds a snapshot, so a handful of unresolvable IDs
        # is expected and decision 001 says explicitly not to "clean" them. But
        # unbounded INFO means a silent drift from 208 to 20,000 would report
        # just as cheerfully, so it is bounded: a handful is drift, thousands is
        # a broken reload.
        if tbl == "method_performances":
            if absent_both:
                rep.report(
                    f"orphans {tbl}.dove_tower_id", Result.FAIL,
                    f"{absent_both:,} of {total:,} adjudicated links cite a "
                    f"TowerID in neither dove nor towers. These were resolved "
                    f"against `towers` when they were adjudicated, so an orphan "
                    f"here is corruption, not upstream drift",
                )
            else:
                rep.report(f"orphans {tbl}.dove_tower_id", Result.PASS,
                           f"all {total:,} adjudicated links resolve")
        elif absent_both > ORPHAN_DRIFT_CEILING:
            rep.report(
                f"orphans {tbl}.dove_tower_id", Result.FAIL,
                f"{absent_both:,} of {total:,} linked records resolve to neither "
                f"dove nor towers -- above the {ORPHAN_DRIFT_CEILING:,} ceiling "
                f"for upstream drift. A handful is expected (decision 001); this "
                f"many means a reload went wrong or Dove was refreshed badly",
            )
        else:
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
        #
        # Join v_towers_unique itself, not a hand-written `SELECT DISTINCT
        # TowerID FROM towers` that resembles it. The check is worth having only
        # if it exercises the object the rest of the codebase joins: an inline
        # equivalent passes happily while the real view is broken, missing, or
        # quietly redefined. Lesson 20 -- recorded SQL must be the SQL that runs.
        # The DISTINCT form stays as the fallback for a database predating 007,
        # and says so rather than pretending it checked the view.
        if view_exists(conn, "v_towers_unique"):
            projection, via = '"v_towers_unique"', "v_towers_unique"
        else:
            projection, via = ('(SELECT DISTINCT "TowerID" FROM "towers")',
                               "inline DISTINCT -- v_towers_unique absent")
        joined = count(
            conn,
            f'SELECT COUNT(*) FROM "{tbl}" t '
            f'JOIN {projection} u ON u."TowerID" = t."dove_tower_id"',
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
                       f"{via}: {joined:,} == {records:,} records "
                       f"- {orphans:,} orphans")
        else:
            rep.report(f"join-identity {tbl}", Result.FAIL,
                       f"{via}: join returns {joined:,} but "
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
        for d in bad_scans(conn, plan):
            rep.report("plan v_first_tower_peals (scan)", Result.FAIL,
                       f"un-indexed SCAN of a base table: {d}")

    if not view_exists(conn, "v_tower_performances"):
        rep.report("plan v_tower_performances", Result.SKIP, "view absent")
    else:
        plan = conn.execute(
            "EXPLAIN QUERY PLAN SELECT COUNT(*) FROM v_tower_performances"
        ).fetchall()
        text = _plan_text(plan)
        # Since decision 001 this view joins performances.dove_tower_id to
        # v_towers_unique, which is a GROUP BY over towers -- so the plan reads
        # `CO-ROUTINE v_towers_unique / SCAN towers USING INDEX
        # idx_towers_towerid / SCAN d / SEARCH p USING COVERING INDEX
        # idx_perf_dove_tower`. Either serving index satisfies the assertion;
        # what must not happen is a bare scan of performances or towers.
        if ("idx_perf_dove_tower" in text or "idx_towers_towerid" in text
                or "idx_dove_towerid" in text):
            rep.report("plan v_tower_performances", Result.PASS,
                       "uses a TowerID index")
        else:
            rep.report("plan v_tower_performances", Result.FAIL,
                       f"no TowerID index used; plan:\n{text}")
        for d in bad_scans(conn, plan):
            rep.report("plan v_tower_performances (scan)", Result.FAIL,
                       f"un-indexed SCAN of a base table: {d}")


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
    check_csv_agreement(conn, rep)
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
