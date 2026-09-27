"""The Python predicates and the SQL fragments must agree, on every row (R-53).

`scripts/semantics.py` states each rule twice, because the callers are split:
36 scripts in Python, and recorded queries in `queries/` that run as SQL with no
Python near them. Two statements of one rule is two definitions unless something
binds them.

Sharing the constants binds the numbers. It does not bind the logic -- a `<`
where a `<=` belongs, or a CASE arm in the wrong order, drifts silently and
looks right in review. So this compares them **row for row across all 293,471
performances**, which is the only check that can see that.

This file is the deliverable of R-53. Without it `semantics.py` is a suggestion
and the repository has fifteen definitions instead of fourteen.
"""

import sqlite3
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from semantics import (
    PEAL_MIN_CHANGES,
    PEAL_MIN_CHANGES_LOW_STAGE,
    PEAL_HIGH_STAGE,
    QUARTER_MIN_CHANGES,
    is_peal,
    is_quarter,
    length_class,
    sql_is_peal,
    sql_is_quarter,
    sql_length_class,
)

DB = ROOT / "data" / "change-ringing.db"


class TestPredicates(unittest.TestCase):
    """The rule itself, on cases chosen to sit on every boundary."""

    def test_unknown_length_is_none_not_false(self):
        """The whole reason for the tri-state.

        21,788 performances have no length. A boolean calls them all quarters,
        which is the failure already present in `SUM(changes >= 5000)`.
        """
        self.assertIsNone(is_peal(None))
        self.assertIsNone(is_peal(""))
        self.assertIsNone(is_quarter(None))
        self.assertIsNone(length_class(None))

    def test_long_enough_at_any_stage(self):
        self.assertTrue(is_peal(5040))
        self.assertTrue(is_peal(5040, stage=6))
        self.assertTrue(is_peal(5040, stage=None))
        self.assertTrue(is_peal(10000, stage=5))

    def test_too_short_at_any_stage(self):
        self.assertFalse(is_peal(4999))
        self.assertFalse(is_peal(4999, stage=12))
        self.assertFalse(is_peal(4999, stage=None))

    def test_the_window_depends_on_stage(self):
        """[5000, 5040) is where the CCCBR stage rule actually bites."""
        self.assertTrue(is_peal(5000, stage=8))     # seven or more bells
        self.assertTrue(is_peal(5000, stage=7))
        self.assertFalse(is_peal(5000, stage=6))    # five or six need 5040
        self.assertFalse(is_peal(5039, stage=5))
        self.assertIsNone(is_peal(5000, stage=None))  # genuinely undecidable

    def test_the_boundary_that_848_performances_sit_on(self):
        """'>=' not '>'. conductor_speed_signature.sql is the outlier."""
        self.assertTrue(is_peal(PEAL_MIN_CHANGES, stage=8))

    def test_quarter_is_not_a_peal_and_long_enough(self):
        self.assertTrue(is_quarter(1250, stage=8))
        self.assertTrue(is_quarter(1260, stage=8))
        self.assertFalse(is_quarter(1249, stage=8))
        self.assertFalse(is_quarter(5000, stage=8))    # that is a peal
        self.assertIsNone(is_quarter(5000, stage=None))  # cannot know either way

    def test_length_class(self):
        self.assertEqual(length_class(5040, 8), "peal")
        self.assertEqual(length_class(1260, 8), "quarter")
        self.assertEqual(length_class(720, 6), "short")
        self.assertIsNone(length_class(None))


@unittest.skipUnless(DB.exists(), f"no replica at {DB}; build one first (R-27)")
class TestPythonAndSqlAgree(unittest.TestCase):
    """The binding check: both statements of the rule, on every row.

    Not a sample. A disagreement confined to 800 rows in one corner is exactly
    the kind this is for, and a sample would miss it.
    """

    @classmethod
    def setUpClass(cls):
        cls.conn = sqlite3.connect(str(DB))
        # Every performance with the stage its first method resolves to, which is
        # the shape callers actually use. LEFT JOIN so unresolved stays NULL
        # rather than dropping out -- the NULL cases are the interesting ones.
        cls.rows = cls.conn.execute("""
            SELECT p.perf_id, p.changes, m.stage
            FROM performances p
            LEFT JOIN performance_methods pm
                   ON pm.perf_id = p.perf_id AND pm.ord = 0
            LEFT JOIN methods m ON m.method_id = pm.method_id
        """).fetchall()

    def _compare(self, py_fn, sql_expr, label):
        sql = self.conn.execute(f"""
            SELECT p.perf_id, {sql_expr}
            FROM performances p
            LEFT JOIN performance_methods pm
                   ON pm.perf_id = p.perf_id AND pm.ord = 0
            LEFT JOIN methods m ON m.method_id = pm.method_id
        """).fetchall()
        by_id = dict(sql)
        self.assertEqual(len(by_id), len(self.rows), "row counts differ")

        mismatches = []
        for pid, changes, stage in self.rows:
            want = py_fn(changes, stage)
            got = by_id[pid]
            if isinstance(want, bool):
                want_sql = 1 if want else 0
            else:
                want_sql = want            # None, or a string for length_class
            if got != want_sql:
                mismatches.append((pid, changes, stage, want_sql, got))
                if len(mismatches) >= 5:
                    break
        self.assertEqual(
            mismatches, [],
            f"{label}: Python and SQL disagree. First few "
            f"(perf_id, changes, stage, python, sql): {mismatches}")

    def test_is_peal_agrees_on_every_row(self):
        self._compare(is_peal, sql_is_peal("p.changes", "m.stage"), "is_peal")

    def test_is_quarter_agrees_on_every_row(self):
        self._compare(is_quarter, sql_is_quarter("p.changes", "m.stage"),
                      "is_quarter")

    def test_length_class_agrees_on_every_row(self):
        self._compare(length_class, sql_length_class("p.changes", "m.stage"),
                      "length_class")

    def test_the_generated_view_agrees_with_python_on_every_row(self):
        """The view is what queries/ actually reads, so the view is what matters.

        The fragment tests above check the expressions. This checks the artefact
        built from them -- schema/008, layered into two views so the CASE does not
        nest six deep -- because that layering is a transformation the fragment
        tests cannot see.

        Skips if the view is absent: it is applied by build_local_db.py, and a
        replica built before R-53 will not have it.
        """
        have = self.conn.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='view' "
            "AND name='v_performance_facts'").fetchone()[0]
        if not have:
            self.skipTest("v_performance_facts not applied to this replica")

        view = dict(self.conn.execute(
            "SELECT perf_id, is_peal FROM v_performance_facts").fetchall())
        vq = dict(self.conn.execute(
            "SELECT perf_id, is_quarter FROM v_performance_facts").fetchall())
        vc = dict(self.conn.execute(
            "SELECT perf_id, length_class FROM v_performance_facts").fetchall())

        bad = []
        for pid, changes, stage in self.rows:
            for fn, got, label in ((is_peal, view[pid], "is_peal"),
                                   (is_quarter, vq[pid], "is_quarter"),
                                   (length_class, vc[pid], "length_class")):
                want = fn(changes, stage)
                want = (1 if want else 0) if isinstance(want, bool) else want
                if got != want:
                    bad.append((label, pid, changes, stage, want, got))
            if len(bad) >= 5:
                break
        self.assertEqual(bad, [], f"view disagrees with Python: {bad}")

    def test_the_view_totals_reconcile(self):
        """The four length classes must partition the corpus exactly."""
        have = self.conn.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='view' "
            "AND name='v_performance_facts'").fetchone()[0]
        if not have:
            self.skipTest("v_performance_facts not applied to this replica")
        counts = dict(self.conn.execute(
            "SELECT length_class, COUNT(*) FROM v_performance_facts "
            "GROUP BY 1").fetchall())
        self.assertEqual(counts["peal"], 51_659)
        self.assertEqual(counts["quarter"], 205_292)
        self.assertEqual(counts["short"], 13_897)
        self.assertEqual(counts[None], 22_623)
        self.assertEqual(sum(counts.values()), 293_471)

    def test_the_tri_state_covers_the_population_r52_measured(self):
        """22,623 unknowns: 21,788 with no length, 835 in the stage window.

        Pinned so that a future change quietly collapsing the tri-state to a
        boolean shows up as a number moving rather than as nothing at all.
        """
        unknown = sum(1 for _, c, s in self.rows if is_peal(c, s) is None)
        no_length = sum(1 for _, c, _ in self.rows if c is None)
        self.assertEqual(no_length, 21_788)
        self.assertEqual(unknown - no_length, 835)
        self.assertEqual(unknown, 22_623)

    def test_peal_count_matches_the_convention_r52_recommended(self):
        """`>=` gives 52,499; the rule reclassifies 5 short and 835 unknown.

        This arithmetic is what found the error in R-52's document. It predicted
        52,499 - 4 - 835 and got 51,659 rather than 51,660, because the stage
        rule is "seven or more bells" and the document had filtered `IN (5, 6)`,
        dropping a stage-4 Minimus performance.
        """
        ge = self.conn.execute(
            "SELECT COUNT(*) FROM performances WHERE changes >= 5000").fetchone()[0]
        self.assertEqual(ge, 52_499)
        peals = sum(1 for _, c, s in self.rows if is_peal(c, s) is True)
        # 52,499 by the flat rule, minus the 5 below stage 7 inside the window,
        # minus those in the window whose stage is unknown (now None, not True).
        self.assertEqual(peals, 52_499 - 5 - 835)
        self.assertEqual(peals, 51_659)


if __name__ == "__main__":
    unittest.main()
