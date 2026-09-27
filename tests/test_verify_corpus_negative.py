#!/usr/bin/env python3
"""Negative tests for every check in scripts/verify_corpus.py (R-44).

`verify_corpus.py` is the most load-bearing file in the repository, and until
now its 51 checks were assertions nobody had falsified. A check that cannot
fail is worse than no check: it reports success and stops anyone looking --
which is what PR #26's CompLib arm did, reporting SKIP over 86,054 uncommitted
rows, and what PR #21 and #24 did before it in other files.

Each test breaks ONE thing in an otherwise healthy database and asserts:

  1. the check it was aimed at reports FAIL (or crashes -- main() turns a
     crash into a non-zero exit via traceback, loud but report-truncating;
     see below), and
  2. only the checks that break PREDICTABLY fail with it. Dropping a table
     drops its indexes and orphans its committed CSVs, so those breaks
     legitimately trip more than one check; each test names the collateral
     it expects. Anything outside that set means the FAIL may not belong to
     the break, and the test fails.

The healthy database is built by verify_corpus_fixture.py: the committed
schema files plus a handful of rows shaped around the checker's own
invariants (fan-out, adjudicated links, drift orphans, exact CSV counts). It
builds and checks in ~0.1s with no network, so this suite runs in CI -- where
the real replica cannot be built (R-27) -- against every pull request.

What the suite found on the day it was written (the full account is in
docs/negative_testing_verify_corpus.md):

  - 45 of the 51 arms can be made to FAIL cleanly, each proven here.
  - 6 arms cannot: the four optional-corpus table checks and the two
    optional-view checks report SKIP on absence even when the rest of the
    database shows the migration WAS applied. For the two CompLib tables the
    loss is caught by their csv-agreement siblings; for
    performance_methods, performance_method_unresolved and the two optional
    views, nothing catches it. Those are the decorations, and the contract
    is pinned in TestOptionalCorpusArms rather than left implicit.
  - 6 breaks (dropping dove, towers, methods, method_performances,
    performances or v_towers_unique) make a later check raise instead of
    reporting FAIL: the run is loud but truncated. run_checks() isolates each
    check function and records the crash as `crash: <function>` so the rest
    of the report still runs; main() as shipped aborts at the first one.
"""
import sqlite3
import sys
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS_DIR))

from verify_corpus_fixture import (
    passing_database, run_checks, fixture_root, build, _load_checker,
)


class NegativeTestCase(unittest.TestCase):
    """One deliberately broken database, per check."""

    def break_and_run(self, mutate, expect_fail):
        """Build the healthy fixture, apply `mutate`, run all 51 checks.

        `expect_fail` is the check name (or a set of names) that must report
        FAIL. Everything else must not, so a break that trips an unexpected
        check fails the test -- the FAIL then belongs to collateral damage,
        not to the break. SKIP and INFO are not FAIL and are always allowed.
        """
        if isinstance(expect_fail, str):
            expect_fail = {expect_fail}
        with passing_database() as (checker, db_path):
            conn = sqlite3.connect(str(db_path))
            try:
                mutate(conn)
                conn.commit()
            finally:
                conn.close()
            rep = run_checks(checker, db_path)
        failed = {name for name, status, _ in rep.names if status == "FAIL"}
        missing = expect_fail - failed
        collateral = failed - expect_fail
        self.assertFalse(
            missing,
            f"check(s) {sorted(missing)} did not FAIL -- decoration, or the "
            f"break does not reach it. Recorded statuses: "
            f"{ {n: s for n, s, _ in rep.names if n in missing} }",
        )
        self.assertFalse(
            collateral,
            f"break tripped unexpected check(s) {sorted(collateral)}; the "
            f"FAIL may not belong to the intended check",
        )
        return rep

    def break_repository_and_run(self, root_mutation, expect_fail):
        """For breaks that live in the repository half (a CSV moved aside),
        not the database half."""
        if isinstance(expect_fail, str):
            expect_fail = {expect_fail}
        with fixture_root() as root:
            db_path = root / "fixture.db"
            build(db_path, root)
            root_mutation(root)
            checker = _load_checker(root)
            rep = run_checks(checker, db_path)
        failed = {name for name, status, _ in rep.names if status == "FAIL"}
        self.assertFalse(expect_fail - failed,
                         f"check(s) {sorted(expect_fail - failed)} did not FAIL")
        self.assertFalse(failed - expect_fail,
                         f"break tripped unexpected check(s) "
                         f"{sorted(failed - expect_fail)}")
        return rep


class TestSchemaTableChecks(NegativeTestCase):
    """Tables declared in schema/*.sql must exist in a loaded database.

    Dropping a table also drops its indexes (SQLite drops dependent objects
    with the table) and, for tables with committed CSVs, trips csv-agreement
    -- a replica missing a table IS a stale replica, which is what that check
    says. Collateral is named per break so the table-existence FAIL is still
    proven on its own.
    """

    def test_missing_table_bells(self):
        self.break_and_run(
            lambda c: c.execute("DROP TABLE bells"), "table bells")

    def test_missing_table_changes(self):
        self.break_and_run(
            lambda c: c.execute("DROP TABLE changes"), "table changes")

    def test_missing_table_dove(self):
        # The orphan check queries dove directly, so it raises rather than
        # reporting -- recorded as a crash by the fixture's run_checks.
        self.break_and_run(
            lambda c: c.execute("DROP TABLE dove"),
            {"table dove", "crash: check_orphan_soft_fks"})

    def test_missing_table_founders(self):
        self.break_and_run(
            lambda c: c.execute("DROP TABLE founders"), "table founders")

    def test_missing_table_frames(self):
        self.break_and_run(
            lambda c: c.execute("DROP TABLE frames"), "table frames")

    def test_missing_table_regions(self):
        self.break_and_run(
            lambda c: c.execute("DROP TABLE regions"), "table regions")

    def test_missing_table_towers(self):
        # towers underpins v_towers_unique and every view built on it, so
        # the orphan, join-identity and plan checks all raise.
        self.break_and_run(
            lambda c: c.execute("DROP TABLE towers"),
            {"table towers", "crash: check_orphan_soft_fks",
             "crash: check_join_identity", "crash: check_query_plans"})

    def test_missing_table_performances(self):
        self.break_and_run(
            lambda c: c.execute("DROP TABLE performances"),
            {"table performances", "index idx_perf_tower_date",
             "csv agreement performances", "crash: check_query_plans"})

    def test_missing_table_performance_ringers(self):
        self.break_and_run(
            lambda c: c.execute("DROP TABLE performance_ringers"),
            {"table performance_ringers", "index idx_ringer_name_perf",
             "csv agreement performance_ringers"})

    def test_missing_table_performance_footnotes(self):
        self.break_and_run(
            lambda c: c.execute("DROP TABLE performance_footnotes"),
            {"table performance_footnotes",
             "csv agreement performance_footnotes"})

    def test_missing_table_performance_flags(self):
        self.break_and_run(
            lambda c: c.execute("DROP TABLE performance_flags"),
            {"table performance_flags", "csv agreement performance_flags"})

    def test_missing_table_methods(self):
        self.break_and_run(
            lambda c: c.execute("DROP TABLE methods"),
            {"table methods", "crash: check_query_plans"})

    def test_missing_table_method_performances(self):
        self.break_and_run(
            lambda c: c.execute("DROP TABLE method_performances"),
            {"table method_performances",
             "index idx_method_perfs_method_event",
             "crash: check_query_plans"})

    def test_missing_table_compositions(self):
        # The table-existence arm itself SKIPs (optional corpus), but the
        # committed CSV means csv-agreement catches the loss -- the exact
        # pairing PR #26 fixed.
        self.break_and_run(
            lambda c: c.execute("DROP TABLE compositions"),
            "csv agreement compositions")

    def test_missing_table_composition_methods(self):
        self.break_and_run(
            lambda c: c.execute("DROP TABLE composition_methods"),
            "csv agreement composition_methods")


class TestSchemaViewChecks(NegativeTestCase):
    """Views declared in schema/*.sql must exist. The two optional-corpus
    views SKIP by design (pinned in TestOptionalCorpusArms); everything else
    FAILs, which is the fix for the bug that made missing views a SKIP --
    deleting v_towers_unique once reported SKIP and exited 0."""

    def test_missing_view_v_ringing_towers(self):
        self.break_and_run(
            lambda c: c.execute("DROP VIEW v_ringing_towers"),
            "view v_ringing_towers")

    def test_missing_view_v_tower_performances(self):
        self.break_and_run(
            lambda c: c.execute("DROP VIEW v_tower_performances"),
            "view v_tower_performances")

    def test_missing_view_v_first_tower_peals(self):
        self.break_and_run(
            lambda c: c.execute("DROP VIEW v_first_tower_peals"),
            "view v_first_tower_peals")

    def test_missing_view_v_towers_unique(self):
        # The entire artefact of decision 001.
        self.break_and_run(
            lambda c: c.execute("DROP VIEW v_towers_unique"),
            {"view v_towers_unique", "crash: check_query_plans"})

    def test_missing_view_v_dove_towers(self):
        self.break_and_run(
            lambda c: c.execute("DROP VIEW v_dove_towers"), "view v_dove_towers")


class TestReadCostIndexChecks(NegativeTestCase):
    """The schema/004 indexes must exist: their absence is a read-budget
    regression, not a cosmetic gap. Dropping the composite also degrades the
    plan that uses it, which is the regression being asserted."""

    def test_missing_index_idx_method_perfs_method_event(self):
        self.break_and_run(
            lambda c: c.execute("DROP INDEX idx_method_perfs_method_event"),
            {"index idx_method_perfs_method_event",
             "plan v_first_tower_peals"})

    def test_missing_index_idx_perf_tower_date(self):
        self.break_and_run(
            lambda c: c.execute("DROP INDEX idx_perf_tower_date"),
            "index idx_perf_tower_date")

    def test_missing_index_idx_ringer_name_perf(self):
        self.break_and_run(
            lambda c: c.execute("DROP INDEX idx_ringer_name_perf"),
            "index idx_ringer_name_perf")


class TestRowCountChecks(NegativeTestCase):
    """Row counts per table against known-good ranges.

    The FAIL arm is the empty table: 0 rows where the range says thousands
    means the load never happened -- the failure mode that shipped
    (performance_flags reported 0 for weeks because 0 was inside the range;
    the fix made an empty table a FAIL). A non-empty count outside its range
    is INFO by design: the sources genuinely grow, and a range check that
    FAILs on growth turns every corpus refresh into a red build. That
    asymmetry is recorded in docs/negative_testing_verify_corpus.md.
    """

    def test_empty_dove(self):
        # An empty dove also makes its fan-out vacuously "unique".
        self.break_and_run(
            lambda c: c.execute("DELETE FROM dove"),
            {"rows dove", "fan-out dove.TowerID"})

    def test_empty_bells(self):
        self.break_and_run(
            lambda c: c.execute("DELETE FROM bells"), "rows bells")

    def test_empty_towers(self):
        # Emptying towers orphans the adjudicated link to TowerID 103 (which
        # only towers holds) and makes its fan-out vacuously "unique".
        self.break_and_run(
            lambda c: c.execute("DELETE FROM towers"),
            {"rows towers", "fan-out towers.TowerID",
             "orphans method_performances.dove_tower_id"})

    def test_empty_frames(self):
        self.break_and_run(
            lambda c: c.execute("DELETE FROM frames"), "rows frames")

    def test_empty_founders(self):
        self.break_and_run(
            lambda c: c.execute("DELETE FROM founders"), "rows founders")

    def test_empty_regions(self):
        self.break_and_run(
            lambda c: c.execute("DELETE FROM regions"), "rows regions")

    def test_empty_changes(self):
        self.break_and_run(
            lambda c: c.execute("DELETE FROM changes"), "rows changes")

    def test_empty_methods(self):
        self.break_and_run(
            lambda c: c.execute("DELETE FROM methods"), "rows methods")

    def test_empty_method_performances(self):
        self.break_and_run(
            lambda c: c.execute("DELETE FROM method_performances"),
            "rows method_performances")


class TestCsvAgreementChecks(NegativeTestCase):
    """The replica must hold exactly the rows the committed CSVs hold.

    The one check family that has caught a defect live (a year-stale replica,
    and PR #26's uncommitted CompLib load), and both directions matter:
    fewer rows than the CSVs is a stale replica, more rows is data that
    cannot be rebuilt from the repository.
    """

    def test_performances_missing_rows(self):
        self.break_and_run(
            lambda c: c.execute("DELETE FROM performances WHERE perf_id = 5"),
            "csv agreement performances")

    def test_performances_extra_rows(self):
        def add(conn):
            conn.execute(
                'INSERT INTO performances ("perf_id","bb_id","place","perf_date") '
                "VALUES (999, 'P999', 'Nowhere', '2024-01-06')")
        self.break_and_run(add, "csv agreement performances")

    def test_ringers_missing_rows(self):
        self.break_and_run(
            lambda c: c.execute("DELETE FROM performance_ringers WHERE perf_id = 2"),
            "csv agreement performance_ringers")

    def test_ringers_extra_rows(self):
        def add(conn):
            conn.execute(
                'INSERT INTO performance_ringers ("perf_id","position","bell",'
                '"name","conductor") VALUES (999, 0, \'3\', \'C Ringer\', 0)')
        self.break_and_run(add, "csv agreement performance_ringers")

    def test_footnotes_missing_rows(self):
        self.break_and_run(
            lambda c: c.execute("DELETE FROM performance_footnotes"),
            "csv agreement performance_footnotes")

    def test_footnotes_extra_rows(self):
        def add(conn):
            conn.execute(
                'INSERT INTO performance_footnotes ("perf_id","position","footnote") '
                "VALUES (999, 0, 'Not in the CSV')")
        self.break_and_run(add, "csv agreement performance_footnotes")

    def test_flags_missing_rows(self):
        self.break_and_run(
            lambda c: c.execute("DELETE FROM performance_flags"),
            "csv agreement performance_flags")

    def test_flags_extra_rows(self):
        def add(conn):
            conn.execute(
                'INSERT INTO performance_flags ("perf_id","position","flag_type") '
                "VALUES (999, 0, 'simulator')")
        self.break_and_run(add, "csv agreement performance_flags")

    def test_compositions_missing_rows(self):
        self.break_and_run(
            lambda c: c.execute("DELETE FROM compositions"),
            "csv agreement compositions")

    def test_compositions_extra_rows(self):
        def add(conn):
            conn.execute(
                'INSERT INTO compositions ("composition_id","library","derived_title") '
                "VALUES (999, 'Public', 'Never committed')")
        self.break_and_run(add, "csv agreement compositions")

    def test_composition_methods_missing_rows(self):
        self.break_and_run(
            lambda c: c.execute("DELETE FROM composition_methods"),
            "csv agreement composition_methods")

    def test_composition_methods_extra_rows(self):
        def add(conn):
            conn.execute(
                'INSERT INTO composition_methods ("composition_id","position",'
                '"method_title") VALUES (999, 0, \'Never committed\')')
        self.break_and_run(add, "csv agreement composition_methods")

    def test_compositions_csv_absent_but_rows_loaded(self):
        """PR #26's exact hole: an absent CSV must FAIL when the table holds
        rows, never SKIP -- the old SKIP announced success over 86,054 rows
        that could not be rebuilt from the repository."""
        self.break_repository_and_run(
            lambda root: (root / "data" / "complib" / "compositions.csv").unlink(),
            "csv agreement compositions")


class TestTowerIdFanoutChecks(NegativeTestCase):
    """TowerID is NOT unique in dove or towers; if it ever became unique,
    every join silently changes shape (decision 001)."""

    def test_dove_towerid_becomes_unique(self):
        self.break_and_run(
            lambda c: c.execute("DELETE FROM dove WHERE RingID = 2"),
            "fan-out dove.TowerID")

    def test_towers_towerid_becomes_unique(self):
        self.break_and_run(
            lambda c: c.execute("DELETE FROM towers WHERE RingID = 2"),
            "fan-out towers.TowerID")


class TestOrphanSoftFkChecks(NegativeTestCase):
    """Adjudicated links must resolve; BellBoard drift is bounded."""

    def test_method_performances_orphan_link(self):
        """The R-48 shape as a loader fault: an adjudicated link citing a
        TowerID in neither dove nor towers. This is the check today's fresh
        rebuild fails on for real (9 links cite Dove-removed TowerID 25219),
        so it is the one FAIL the repository currently ships."""
        def orphan(conn):
            conn.execute(
                'UPDATE method_performances SET dove_tower_id = 25219 '
                "WHERE method_id = 'm1' AND position = 0")
        self.break_and_run(orphan, "orphans method_performances.dove_tower_id")

    def test_performances_orphans_above_ceiling(self):
        """Drift is expected but bounded: thousands is never drift. Inserting
        the ceiling plus one orphans into a fixture of five performances is
        the same trip without a 300 MB database -- and the added rows also
        trip csv-agreement, which is correct: they are not in any CSV."""
        def flood(conn):
            conn.executemany(
                'INSERT INTO performances ("perf_id","bb_id","dove_tower_id") '
                "VALUES (?, ?, ?)",
                [(10_000 + i, f"PX{i}", 900_000 + i) for i in range(5001)])
        self.break_and_run(flood, {"orphans performances.dove_tower_id",
                                   "csv agreement performances"})


class TestJoinIdentityChecks(NegativeTestCase):
    """A join cannot create or destroy a linked record (decision 001)."""

    @staticmethod
    def _replaced_view(where):
        return (
            'CREATE VIEW v_towers_unique AS '
            'SELECT "TowerID", MAX("Place") AS "Place", '
            'MAX("Dedicn") AS "Dedicn", MAX("County") AS "County", '
            'MAX("Country") AS "Country", MAX("Lat") AS "Lat", '
            'MAX("Long") AS "Long", COUNT(*) AS "installations" '
            f'FROM "towers" {where} GROUP BY "TowerID"')

    def test_broken_view_drops_linked_records(self):
        """Redefine v_towers_unique so the join returns fewer rows than the
        record count says must join. The check joins the real view -- an
        inline equivalent passing while the view is broken was the bug the
        merge of PR #11 fixed (lesson 20). The replacement keeps every
        column so only the join changes, nothing crashes."""
        def break_view(conn):
            conn.execute("DROP VIEW v_towers_unique")
            conn.execute(self._replaced_view('WHERE "TowerID" = 101'))
        self.break_and_run(break_view, {"join-identity method_performances",
                                        "join-identity performances"})

    def test_duplicate_projection_inflates_join(self):
        """A view that repeats a TowerID fans the join out: more rows joined
        than records carry the link. This is the +19/+227 shape from
        decision 001, on three rows."""
        def break_view(conn):
            conn.execute("DROP VIEW v_towers_unique")
            conn.execute(
                self._replaced_view("") +
                ' UNION ALL SELECT "TowerID", MAX("Place"), MAX("Dedicn"), '
                'MAX("County"), MAX("Country"), MAX("Lat"), MAX("Long"), '
                'COUNT(*) FROM "towers" WHERE "TowerID" = 102 '
                'GROUP BY "TowerID"')
        self.break_and_run(break_view, {"join-identity method_performances",
                                        "join-identity performances"})


class TestNanStringCheck(NegativeTestCase):
    """Literal 'nan' in a text column -- a real past bug that broke every
    IS NULL check downstream."""

    def test_nan_in_bells(self):
        self.break_and_run(
            lambda c: c.execute("UPDATE bells SET Bell_Name = 'nan' "
                                "WHERE Bell_ID = 1"),
            "nan strings")

    def test_nan_in_performances(self):
        self.break_and_run(
            lambda c: c.execute("UPDATE performances SET place = 'nan' "
                                "WHERE perf_id = 1"),
            "nan strings")


class TestQueryPlanChecks(NegativeTestCase):
    """The read-critical indexes must actually serve the shipped views."""

    def test_first_tower_peals_plan_loses_composite_index(self):
        """Drop the composite and leave the single-column ones: the planner
        falls back to driving the inner lookup off event_type, the exact
        396M-rows-read regression schema/004 exists to prevent."""
        self.break_and_run(
            lambda c: c.execute("DROP INDEX idx_method_perfs_method_event"),
            {"plan v_first_tower_peals",
             "index idx_method_perfs_method_event"})

    def test_tower_performances_plan_loses_towerid_indexes(self):
        self.break_and_run(
            lambda c: [c.execute(f"DROP INDEX {ix}") for ix in
                       ("idx_perf_dove_tower", "idx_towers_towerid",
                        "idx_dove_towerid")],
            {"plan v_first_tower_peals (scan)",
             "plan v_tower_performances",
             "plan v_tower_performances (scan)"})


class TestOptionalCorpusArms(NegativeTestCase):
    """The CompLib / performance-methods migrations are optional: a database
    built without them reports SKIP, not FAIL. Those arms are decorations BY
    DESIGN -- a database that never loaded CompLib is not corrupt -- and this
    class pins the contract so nobody "fixes" it into a false failure.

    The measured edge, recorded in docs/negative_testing_verify_corpus.md:
    the SKIP does not distinguish "never applied" from "applied and lost".
    Dropping the optional tables from a POPULATED database still SKIPs; for
    the two CompLib tables the committed CSV means csv-agreement catches the
    loss anyway, and for performance_methods, performance_method_unresolved
    and the two optional views nothing does -- though those hold no committed
    artifact to compare against, so a SKIP is the only honest answer
    available to a checker that sees only the database.
    """

    def _statuses_for(self, mutate_db=None, without_optional=False):
        with fixture_root() as root:
            db_path = root / "fixture.db"
            if without_optional:
                # The shape of a build that never applied schema/005 and
                # /006: everything else, those objects absent.
                conn = sqlite3.connect(str(db_path))
                try:
                    for sql in sorted((root / "schema").glob("*.sql")):
                        if sql.name in ("005_init_performance_methods.sql",
                                        "006_init_complib.sql"):
                            continue
                        conn.executescript(sql.read_text(encoding="utf-8"))
                    conn.commit()
                finally:
                    conn.close()
            else:
                build(db_path, root)
                conn = sqlite3.connect(str(db_path))
                try:
                    mutate_db(conn)
                    conn.commit()
                finally:
                    conn.close()
            checker = _load_checker(root)
            rep = run_checks(checker, db_path)
            return {n: s for n, s, _ in rep.names}

    def test_absent_optional_tables_skip_on_unpopulated_build(self):
        statuses = self._statuses_for(without_optional=True)
        for name in ("table performance_methods",
                     "table performance_method_unresolved",
                     "table compositions", "table composition_methods",
                     "view v_performance_methods", "view v_composition_methods"):
            self.assertEqual(statuses.get(name), "SKIP",
                             f"{name} should SKIP on a build without the migration")

    def test_lost_optional_tables_skip_even_when_corpus_was_loaded(self):
        """The decoration, measured: the fixture POPULATES these tables, so
        dropping them is a loaded corpus losing data -- and the existence
        arms still say SKIP, because nothing in the database says the
        migration was ever applied."""
        def drop_all(conn):
            for stmt in ("DROP TABLE performance_methods",
                         "DROP TABLE performance_method_unresolved",
                         "DROP VIEW v_performance_methods",
                         "DROP TABLE compositions",
                         "DROP TABLE composition_methods",
                         "DROP VIEW v_composition_methods"):
                conn.execute(stmt)
        statuses = self._statuses_for(mutate_db=drop_all, without_optional=False)
        for name in ("table performance_methods",
                     "table performance_method_unresolved",
                     "table compositions", "table composition_methods",
                     "view v_performance_methods", "view v_composition_methods"):
            self.assertEqual(statuses.get(name), "SKIP",
                             f"{name} should SKIP; it cannot FAIL by design")


class TestFailingRunExitsNonZero(NegativeTestCase):
    """The whole point of the checker: a broken database exits non-zero, so
    it can gate. main() is exercised end-to-end, through the fixture."""

    def test_main_returns_one_on_failure(self):
        import os
        import subprocess
        with fixture_root() as root:
            db_path = root / "fixture.db"
            build(db_path, root)
            conn = sqlite3.connect(str(db_path))
            conn.execute("DROP VIEW v_towers_unique")
            conn.commit()
            conn.close()
            result = subprocess.run(
                [sys.executable, str(root / "scripts" / "verify_corpus.py"),
                 "--local-db", str(db_path)],
                capture_output=True, text=True, cwd=str(root),
                env={**os.environ, "PYTHONPATH": str(root / "scripts")})
            self.assertNotEqual(result.returncode, 0,
                                "a broken database must exit non-zero")


if __name__ == "__main__":
    unittest.main()
