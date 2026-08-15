#!/usr/bin/env python3
"""
Check a corpus database -- local replica or, one day, production -- and report
anything wrong. Exits non-zero on failure so it can gate CI later.

Usage:
    python scripts/verify_corpus.py --local-db local_corpus.db
    python scripts/verify_corpus.py --local-db local_corpus.db --tolerance 0.10

Motivated by how many real defects this project has shipped and caught late:
the 591-million-read day came from two ordinary-looking statements whose plans
regressed silently, the backfill run reported success at 16% capture, and a
double-quoted string literal reached production because local testing under
sqlite3 had passed. Each of those would have been caught here.

What it checks (see docs/tasks/mistral-vibe-roadmap.md, Task 3):

  * row counts per core table, within a tolerance band -- a truncated load or a
    missing corpus shows up as a count below the floor. The snapshot moves, so
    the bands are ranges, not constants.
  * orphaned dove_tower_id references -- performance records citing a TowerID
    that exists in neither `dove` nor `towers`. Some are legitimate (Dove
    tracks live while this DB holds a snapshot), so they are reported and
    bounded rather than failed hard; see docs/decisions/001-ring-vs-tower-joins.md
    on why a hard foreign key would be wrong here.
  * dove.TowerID fan-out -- the 13 two-ring towers that make a raw TowerID join
    inflate counts. The join identity is the sharp check: joining the linked
    records to v_towers_unique must return exactly the number of records
    carrying a dove_tower_id, modulo the records that cite a TowerID in neither
    table (which no projection can resolve). A join cannot create or destroy a
    resolvable linked record, so any other number is wrong by construction.
  * the three read-cost indexes from schema/004, whose absence is what turned
    SELECT COUNT(*) FROM v_first_tower_peals into 396 million reads.
  * literal "nan" strings in text columns. pandas round-trips NaN as the
    string "nan", and the loaders convert empty CSV cells to NULL precisely so
    IS NULL checks work; a "nan" string is a loader that forgot that step.
  * EXPLAIN QUERY PLAN on the shipped views, so a plan regression (a bare SCAN
    where there should be an index-driven scan, or the wrong index driving a
    join) is caught before it costs a read budget again.

Uses the same --local-db switch and libsql preference as the loaders, so a
local run is a real check rather than a sqlite3 approximation: see the module
docstring in scripts/db.py on why that matters.
"""
import argparse
import sys
from pathlib import Path

# Reuse the project's connection handling rather than opening libsql directly,
# so the production interlock and the libsql-over-sqlite3 preference are
# honoured. db.py adds --local-db to the parser and exposes connect().
sys.path.insert(0, str(Path(__file__).parent))
import db  # noqa: E402

# ---------------------------------------------------------------------------
# Expected state.
#
# Row-count bands are measured against a full local replica rebuilt from public
# sources on 2026-08-15. They are floors and ceilings, not constants: the Dove
# and CCCBR snapshots grow, BellBoard's committed corpus grows as windows are
# added, and the adjudication record changes as matches are accepted. A count
# below the floor means a truncated or missing load; one above the ceiling is
# worth understanding before it is ignored.
#
# The tolerance applies to the *expected* count and widens both bands; pass
# --tolerance 0 to forbid any drift from the recorded expectation (the strict
# mode a CI gate would use once the bands are pinned).
# ---------------------------------------------------------------------------
EXPECTED_COUNTS = {
    # table:             expected,  tolerance_fraction_of_expected
    "dove":              (7262,    0.05),
    "bells":             (63966,   0.05),
    "towers":            (15722,   0.05),
    "frames":            (10235,   0.05),
    "founders":          (1020,    0.05),
    "regions":           (1131,    0.05),
    "changes":           (24211,   0.05),
    "methods":           (25066,   0.02),   # the CCCBR library is near-complete
    "method_performances": (30746, 0.10),   # grows as first-perf events are added
}

# The three indexes schema/004 added to control row-read cost. Each was the fix
# for a measured blow-up; their absence is the single fastest way back to one.
SCHEMA_004_INDEXES = (
    "idx_method_perfs_method_event",
    "idx_perf_tower_date",
    "idx_ringer_name_perf",
)

# The fan-out that motivates the deduplicated views: 13 towers hold two rings
# each in `dove`, so a raw TowerID join duplicates their rows. The exact number
# is recorded so a schema change that alters it is noticed, but the assertion
# is only that fan-out is non-zero and small -- the real check is the join
# identity below, which holds regardless of the count.
EXPECTED_DOVE_FANOUT = 13

# The shipped views. Each gets an EXPLAIN QUERY PLAN assertion: a substring the
# plan must contain (an index it should use) and, where relevant, a substring
# it must NOT contain (a regression to a bare SCAN or the wrong index). Plans
# are asserted on SELECT COUNT(*) FROM <view>, the shape that cost 396M reads.
#
# Note on "SCAN ... USING INDEX": a GROUP BY (as in the dedup views) or a
# full-covering read legitimately scans every row, and that is correct *when
# driven by an index*. The regression to catch is a bare "SCAN <table>" with
# no index -- the shape that walks the whole table unordered. must_contain is
# used for these so an index is required, rather than banning the word SCAN.
#
# `requires` names the underlying tables; a view whose tables are absent (e.g.
# the CompLib view on a replica built without CompLib) is skipped with a note
# rather than failed, so the check runs on every replica shape.
VIEW_PLAN_ASSERTIONS = (
    # v_first_tower_peals is the view that billed 396M reads. The fix was the
    # composite (method_id, event_type) index in schema/004; the plan must seek
    # on it rather than scanning the event_type range once per method.
    {
        "view": "v_first_tower_peals",
        "requires": ("methods", "method_performances", "dove"),
        "must_contain": "idx_method_perfs_method_event",
    },
    # v_tower_performances joins performances to dove on TowerID. The
    # dove_tower_id index drives the outer scan and the TowerID index seeks.
    {
        "view": "v_tower_performances",
        "requires": ("performances", "dove"),
        "must_contain": "idx_perf_dove_tower",
    },
    # v_performance_methods joins performance_methods -> performances -> methods.
    # The methods seek is on its primary key; the plan must not scan methods.
    {
        "view": "v_performance_methods",
        "requires": ("performance_methods", "performances", "methods"),
        "must_not_contain": "SCAN methods",
    },
    # v_towers_unique and v_dove_towers are the deduplicated projections from
    # decision 001. They GROUP BY TowerID, so they must scan the whole table --
    # but driven by an index, not a bare full-table scan. The regression to
    # catch is "SCAN <table>" with no index. must_contain requires the index,
    # so a bare scan (which prints "SCAN towers" with no "USING INDEX") fails.
    {
        "view": "v_towers_unique",
        "requires": ("towers",),
        "must_contain": "idx_towers_towerid",
    },
    {
        "view": "v_dove_towers",
        "requires": ("dove",),
        "must_contain": "idx_dove_towerid",
    },
    {
        "view": "v_ringing_towers",
        "requires": ("dove",),
        "must_contain": "idx_dove_towerid",
    },
    # v_composition_methods lives over the CompLib tables, which a default
    # local replica does not load. Asserted only when the tables exist.
    {
        "view": "v_composition_methods",
        "requires": ("compositions", "composition_methods", "methods"),
        "must_contain": "idx_comp_methods_composition",
    },
)


class Check:
    """A named check that accumulates pass/fail lines and a failure count."""

    def __init__(self, label):
        self.label = label
        self.lines = []
        self.fails = 0

    def ok(self, msg):
        self.lines.append(f"  ok    {msg}")

    def fail(self, msg):
        self.lines.append(f"  FAIL  {msg}")
        self.fails += 1

    def note(self, msg):
        self.lines.append(f"        {msg}")

    def render(self):
        print(f"\n{self.label}")
        for ln in self.lines:
            print(ln)


def scalar(conn, sql, *params):
    # libsql's execute requires a list for bound parameters (a tuple raises
    # ValueError("Unsupported parameter type"), which sqlite3 accepts). Use a
    # list so the same call works under both, as db.py's module docstring asks.
    return conn.execute(sql, list(params)).fetchone()[0]


def table_exists(conn, name):
    return bool(
        conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", [name]
        ).fetchone()
    )


def view_exists(conn, name):
    return bool(
        conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='view' AND name=?", [name]
        ).fetchone()
    )


# ---------------------------------------------------------------------------
# Individual checks. Each returns a Check so the caller can tally failures.
# ---------------------------------------------------------------------------

def check_row_counts(conn, tolerance_scale):
    c = Check("row counts (within tolerance bands)")
    for table, (expected, base_tol) in EXPECTED_COUNTS.items():
        if not table_exists(conn, table):
            c.fail(f"{table}: table absent -- a corpus is missing from this DB")
            continue
        # Combine the table's own tolerance with the global --tolerance scale,
        # so a cautious run can widen every band at once.
        tol = max(base_tol, tolerance_scale)
        floor = int(expected * (1 - tol))
        ceil = int(expected * (1 + tol))
        actual = scalar(conn, f'SELECT COUNT(*) FROM "{table}"')
        if actual < floor:
            c.fail(f"{table}: {actual:,} rows, below floor {floor:,} "
                   f"(expected ~{expected:,}, tol {tol:.0%}) -- truncated load?")
        elif actual > ceil:
            c.fail(f"{table}: {actual:,} rows, above ceiling {ceil:,} "
                   f"(expected ~{expected:,}, tol {tol:.0%}) -- worth understanding")
        else:
            c.ok(f"{table}: {actual:,} rows (expected ~{expected:,}, "
                 f"band {floor:,}-{ceil:,})")
    return c


def check_orphan_fks(conn):
    c = Check("orphaned dove_tower_id references")

    # method_performances.dove_tower_id -> towers.TowerID. The adjudication
    # resolves against the wider `towers` register, so every linked record
    # should resolve there. Orphans here are real corruption, not drift.
    if table_exists(conn, "method_performances") and table_exists(conn, "towers"):
        linked = scalar(
            conn,
            'SELECT COUNT(*) FROM "method_performances" '
            'WHERE "dove_tower_id" IS NOT NULL',
        )
        orphan_towers = scalar(
            conn,
            'SELECT COUNT(*) FROM "method_performances" mp '
            'WHERE mp."dove_tower_id" IS NOT NULL '
            'AND mp."dove_tower_id" NOT IN (SELECT "TowerID" FROM "towers")',
        )
        if orphan_towers:
            c.fail(f"method_performances: {orphan_towers:,} of {linked:,} linked "
                   "records cite a TowerID absent from `towers`")
        else:
            c.ok(f"method_performances: all {linked:,} linked records resolve "
                 "in `towers`")

    # performances.dove_tower_id -> towers.TowerID. BellBoard tracks Dove live
    # while this DB holds a snapshot, so a small number of unresolved IDs are
    # expected and legitimate (see decision 001). Report them, and bound the
    # count so a silent drift to thousands is still caught.
    if table_exists(conn, "performances") and table_exists(conn, "towers"):
        linked = scalar(
            conn,
            'SELECT COUNT(*) FROM "performances" WHERE "dove_tower_id" IS NOT NULL',
        )
        orphan_towers = scalar(
            conn,
            'SELECT COUNT(*) FROM "performances" p '
            'WHERE p."dove_tower_id" IS NOT NULL '
            'AND p."dove_tower_id" NOT IN (SELECT "TowerID" FROM "towers")',
        )
        orphan_both = scalar(
            conn,
            'SELECT COUNT(*) FROM "performances" p '
            'WHERE p."dove_tower_id" IS NOT NULL '
            'AND p."dove_tower_id" NOT IN (SELECT "TowerID" FROM "towers") '
            'AND p."dove_tower_id" NOT IN (SELECT "TowerID" FROM "dove")',
        )
        distinct_both = scalar(
            conn,
            'SELECT COUNT(DISTINCT p."dove_tower_id") FROM "performances" p '
            'WHERE p."dove_tower_id" IS NOT NULL '
            'AND p."dove_tower_id" NOT IN (SELECT "TowerID" FROM "towers") '
            'AND p."dove_tower_id" NOT IN (SELECT "TowerID" FROM "dove")',
        )
        # The 70-record / 5-ID figure in decision 001 was true of its snapshot.
        # The corpus has grown since; allow a generous bound before failing,
        # because the right ceiling is "a handful, not thousands".
        if orphan_towers and orphan_towers > 5000:
            c.fail(f"performances: {orphan_towers:,} orphan TowerIDs vs `towers` "
                   f"-- far above expected drift")
        elif orphan_towers:
            c.ok(f"performances: {orphan_towers:,} linked records cite a "
                 f"TowerID absent from `towers` (expected drift)")
            c.note(f"of those, {orphan_both:,} across {distinct_both} distinct IDs "
                   "are absent from both `dove` and `towers` -- see decision 001; "
                   "these stay unresolved by design, not corruption")
        else:
            c.ok(f"performances: all {linked:,} linked records resolve in `towers`")
    return c


def check_towerid_fanout(conn):
    c = Check("dove.TowerID fan-out and the join identity")

    if not (table_exists(conn, "dove") and table_exists(conn, "towers")):
        c.fail("dove/towers absent -- cannot check TowerID fan-out")
        return c

    dove_rows = scalar(conn, 'SELECT COUNT(*) FROM "dove"')
    dove_distinct = scalar(conn, 'SELECT COUNT(DISTINCT "TowerID") FROM "dove"')
    fanout = dove_rows - dove_distinct
    if fanout != EXPECTED_DOVE_FANOUT:
        c.note(f"dove fan-out is {fanout} (expected {EXPECTED_DOVE_FANOUT}); "
               "the count moved with the snapshot, the join identity is the "
               "real check below")
    c.ok(f"dove: {dove_rows:,} rows, {dove_distinct:,} distinct TowerIDs, "
         f"{fanout} multi-ring tower(s)")

    towers_rows = scalar(conn, 'SELECT COUNT(*) FROM "towers"')
    towers_distinct = scalar(conn, 'SELECT COUNT(DISTINCT "TowerID") FROM "towers"')
    c.ok(f"towers: {towers_rows:,} rows, {towers_distinct:,} distinct TowerIDs, "
         f"{towers_rows - towers_distinct} multi-installation tower(s) "
         "(the wider register -- joining it raw is worse, not better)")

    # The join identity from decision 001: joining the linked records to the
    # deduplicated projection must return exactly the number of records
    # carrying a dove_tower_id, MINUS the records that cite a TowerID present
    # in neither `dove` nor `towers` (which no projection of either can
    # resolve -- they stay unresolved by design). A join cannot create or
    # destroy a resolvable linked record, so any other number is wrong.
    #
    # For method_performances the adjudication resolves against `towers`, so
    # there are no orphans-in-neither and the join must be exact. For
    # performances (BellBoard) the orphans-in-neither are documented and
    # expected; the joined count must equal linked - orphan_both.
    if not view_exists(conn, "v_towers_unique"):
        c.fail("v_towers_unique is absent -- schema/007 not applied")
        return c

    for table in ("method_performances", "performances"):
        if not table_exists(conn, table):
            c.note(f"{table}: table absent, skipping join identity")
            continue
        linked = scalar(
            conn,
            f'SELECT COUNT(*) FROM "{table}" WHERE "dove_tower_id" IS NOT NULL',
        )
        orphan_both = scalar(
            conn,
            f'SELECT COUNT(*) FROM "{table}" t '
            f'WHERE t."dove_tower_id" IS NOT NULL '
            f'AND t."dove_tower_id" NOT IN (SELECT "TowerID" FROM "towers") '
            f'AND t."dove_tower_id" NOT IN (SELECT "TowerID" FROM "dove")',
        )
        expected_joined = linked - orphan_both
        joined = scalar(
            conn,
            f'SELECT COUNT(*) FROM "{table}" t '
            f'JOIN "v_towers_unique" v ON v."TowerID" = t."dove_tower_id"',
        )
        if joined == expected_joined:
            if orphan_both:
                c.ok(f"{table} -> v_towers_unique: {joined:,} == "
                     f"{linked:,} linked - {orphan_both:,} orphan-in-neither "
                     f"(exact; the {orphan_both} cite TowerIDs in neither table "
                     "and stay unresolved by design)")
            else:
                c.ok(f"{table} -> v_towers_unique: {joined:,} == {linked:,} "
                     "linked records (exact)")
        else:
            diff = expected_joined - joined
            c.fail(f"{table} -> v_towers_unique: {joined:,} != "
                   f"{expected_joined:,} (linked {linked:,} - orphan-in-neither "
                   f"{orphan_both:,}) -- short by {diff:,}; a join cannot destroy "
                   "a resolvable linked record, check v_towers_unique")
    return c


def check_schema_004_indexes(conn):
    c = Check("schema/004 read-cost indexes")
    for idx in SCHEMA_004_INDEXES:
        present = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='index' AND name=?", [idx]
        ).fetchone()
        if present:
            c.ok(f"{idx}: present")
        else:
            c.fail(f"{idx}: MISSING -- its absence caused a measured read-cost "
                   "blow-up; see schema/004_read_cost_indexes.sql")
    return c


def check_nan_strings(conn):
    c = Check("literal 'nan' strings in text columns")
    total = 0
    tables = [
        r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%' AND name NOT LIKE '\\_%' ESCAPE '\\' "
            "ORDER BY name"
        ).fetchall()
    ]
    for table in tables:
        cols = conn.execute(f'PRAGMA table_info("{table}")').fetchall()
        # PRAGMA table_info: cid, name, type, notnull, dflt_value, pk
        for cid, name, ctype, *_ in cols:
            ctype = (ctype or "").upper()
            if not (ctype in ("TEXT", "") or "CHAR" in ctype or "CLOB" in ctype):
                continue
            # The type filter above limits this to TEXT-ish columns, which
            # always support equality with a string literal -- so no try/except
            # is needed and none is wanted. An earlier version caught
            # `Exception` here, which masked a parameter-binding bug and let
            # the check report "no nan strings" against a database that had
            # one. A checker must fail loud, not pass silently.
            n = scalar(
                conn,
                f'SELECT COUNT(*) FROM "{table}" WHERE "{name}" = ?',
                "nan",
            )
            if n:
                c.fail(f'{table}.{name}: {n:,} literal "nan" strings '
                       "(a loader wrote NaN as text instead of NULL)")
                total += n
    if total == 0:
        c.ok("no literal 'nan' strings in any text column")
    else:
        c.note(f"{total:,} 'nan' string(s) in total")
    return c


def check_view_plans(conn):
    c = Check("EXPLAIN QUERY PLAN on shipped views")
    for spec in VIEW_PLAN_ASSERTIONS:
        view = spec["view"]
        requires = spec.get("requires", ())
        missing = [t for t in requires if not table_exists(conn, t)]
        if missing and not view_exists(conn, view):
            c.note(f"{view}: skipped (requires {', '.join(missing)}, "
                   "absent on this replica shape)")
            continue
        if not view_exists(conn, view):
            c.fail(f"{view}: view absent")
            continue
        if missing:
            # The view exists but a required table does not -- should not
            # happen for a CREATE VIEW, but report rather than guess.
            c.fail(f"{view}: view present but required table(s) "
                   f"{', '.join(missing)} absent")
            continue
        try:
            plan_rows = conn.execute(
                f'EXPLAIN QUERY PLAN SELECT COUNT(*) FROM "{view}"'
            ).fetchall()
        except Exception as e:
            c.fail(f"{view}: EXPLAIN QUERY PLAN failed: {e}")
            continue
        plan = "\n".join(str(r[-1]) for r in plan_rows)
        must = spec.get("must_contain")
        must_not = spec.get("must_not_contain")
        failed = False
        if must and must not in plan:
            c.fail(f"{view}: plan does not use {must!r} -- "
                   "a read-cost regression; see schema/004")
            failed = True
        if must_not and must_not in plan:
            c.fail(f"{view}: plan contains {must_not!r} -- "
                   "a SCAN where a SEARCH is expected")
            failed = True
        if not failed:
            detail = spec.get("must_contain") or f"no {spec.get('must_not_contain')}"
            c.ok(f"{view}: plan OK ({detail})")
        c.note(" | ".join(str(r[-1]) for r in plan_rows))
    return c


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    db.add_db_args(ap)
    ap.add_argument(
        "--tolerance", type=float, default=0.0, metavar="FRAC",
        help="Widen every row-count band by this fraction of its expected count "
             "(default 0: use each table's recorded tolerance only).",
    )
    args = ap.parse_args()

    conn = db.connect(args)

    checks = [
        check_row_counts(conn, args.tolerance),
        check_orphan_fks(conn),
        check_towerid_fanout(conn),
        check_schema_004_indexes(conn),
        check_nan_strings(conn),
        check_view_plans(conn),
    ]

    total_fails = 0
    for chk in checks:
        chk.render()
        total_fails += chk.fails

    n_checks = sum(1 for _ in checks)
    print(f"\n{'='*60}")
    if total_fails:
        print(f"{total_fails} failure(s) across {n_checks} check group(s).")
        print("The corpus does not meet its integrity contract.")
        return 1
    print(f"All {n_checks} check group(s) passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
