"""Regression tests for the measured definitions (R-52, scripts/measure_definitions.py).

`docs/definitions_measured.md` publishes eight figures, and R-53 chooses its
conventions from them. If the corpus moves and those figures move with it, the
published recommendations are being justified by numbers that no longer hold.

These tests are deliberately EXACT, not ranged. Every other range check in this
repository exists because an upstream is live and drifts; these read committed
CSVs loaded into the replica, so there is no drift to forgive. A change here means
either the corpus was reloaded differently or a definition changed underneath the
document, and both should fail loudly rather than be absorbed.

They skip rather than fail when no replica is present, because CI has no database
-- that gap is R-27.
"""

import sqlite3
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

DB = ROOT / "data" / "change-ringing.db"


@unittest.skipUnless(DB.exists(), f"no replica at {DB}; build one first (R-27)")
class TestMeasuredDefinitions(unittest.TestCase):
    """The figures docs/definitions_measured.md publishes."""

    @classmethod
    def setUpClass(cls):
        cls.conn = sqlite3.connect(str(DB))

    def one(self, sql):
        return self.conn.execute(sql).fetchone()[0]

    def test_peal_boundary_costs_848_performances(self):
        """The '>' vs '>=' divergence, and it touches a published finding.

        conductor_speed_signature.sql uses '> 5000' while five other call sites
        use '>= 5000'. R-24's published between-conductor result rests on the
        former, so it sits on a denominator 1.6% smaller than everything else.
        """
        ge = self.one("SELECT COUNT(*) FROM performances WHERE changes >= 5000")
        gt = self.one("SELECT COUNT(*) FROM performances WHERE changes > 5000")
        self.assertEqual(ge, 52_499)
        self.assertEqual(gt, 51_651)
        self.assertEqual(ge - gt, 848)
        self.assertAlmostEqual(100 * (ge - gt) / ge, 1.62, places=2)

    def test_unknown_length_moves_peal_share_by_1_43_points(self):
        """21,788 performances have no length, and the denominator choice matters.

        SUM(changes >= 5000) drops them from the numerator while COUNT(*) keeps
        them in the denominator. That is why semantics.py must return None here
        rather than False.
        """
        total = self.one("SELECT COUNT(*) FROM performances")
        nul = self.one("SELECT COUNT(*) FROM performances WHERE changes IS NULL")
        known = self.one("SELECT COUNT(*) FROM performances WHERE changes IS NOT NULL")
        peals = self.one("SELECT COUNT(*) FROM performances WHERE changes >= 5000")
        self.assertEqual(nul, 21_788)
        self.assertEqual(total, 293_471)
        self.assertAlmostEqual(100 * peals / total, 17.89, places=2)
        self.assertAlmostEqual(100 * peals / known, 19.32, places=2)
        self.assertAlmostEqual(100 * peals / known - 100 * peals / total, 1.43, places=2)

    def test_stage_rule_affects_five_performances(self):
        """The rule is real; its reach is 4 rows.

        Pinned because the first draft of the design document led on the 7,001
        performances in [5000, 5040) as though they were all at risk. They are
        not: nearly all are Major and above, where 5000 is correct.
        """
        window = self.one("SELECT COUNT(*) FROM performances "
                          "WHERE changes >= 5000 AND changes < 5040")
        self.assertEqual(window, 7_001)
        # Below SEVEN, not "five or six". The first version of this test filtered
        # `stage IN (5, 6)` and asserted 4, missing the single stage-4 Minimus
        # performance -- the same too-narrow filter that put 4 in the document.
        low = self.one("""
            SELECT COUNT(*) FROM performances p
            JOIN performance_methods pm ON pm.perf_id = p.perf_id AND pm.ord = 0
            JOIN methods m ON m.method_id = pm.method_id
            WHERE p.changes >= 5000 AND p.changes < 5040 AND m.stage < 7""")
        self.assertEqual(low, 5)

    def test_spliced_double_count_is_the_largest_choice(self):
        """+66.0%, and the reason two named measures are needed rather than one.

        'performances of method X' summed across methods exceeds the number of
        performances by 150,701 rows. Either count is defensible; the ambiguity
        is the bug.
        """
        links = self.one("SELECT COUNT(*) FROM performance_methods")
        perfs = self.one("SELECT COUNT(DISTINCT perf_id) FROM performance_methods")
        self.assertEqual(links, 379_180)
        self.assertEqual(perfs, 228_479)
        self.assertEqual(links - perfs, 150_701)
        self.assertAlmostEqual(100 * (links - perfs) / perfs, 66.0, places=1)

    def test_handbells_are_a_tenth_of_the_corpus(self):
        """A tower count that does not exclude them is 10.2% too high."""
        self.assertEqual(self.one("SELECT COUNT(*) FROM performances "
                                  "WHERE ring_type = 'tower'"), 263_417)
        self.assertEqual(self.one("SELECT COUNT(*) FROM performances "
                                  "WHERE ring_type = 'hand'"), 30_054)

    def test_bb_timestamp_is_not_a_submission_date(self):
        """It is BellBoard's record-creation time, carrying their bulk imports.

        57,295 rows sit on a date holding more than 2,000 performances. A real
        submission day carries a few hundred. Those dates -- early January 2017,
        mid-February 2015 -- are not our ingest runs; ours are in `ingested_at`.
        """
        spike = self.one("""
            SELECT COUNT(*) FROM performances WHERE SUBSTR(bb_timestamp, 1, 10) IN (
              SELECT SUBSTR(bb_timestamp, 1, 10) FROM performances
              GROUP BY 1 HAVING COUNT(*) > 2000)""")
        self.assertEqual(spike, 57_295)
        lag = self.one("SELECT COUNT(*) FROM performances "
                       "WHERE julianday(bb_timestamp) - julianday(perf_date) > 365")
        self.assertEqual(lag, 69_856)
        # Our own loads are recorded separately and correctly.
        ours = self.one("SELECT COUNT(DISTINCT SUBSTR(ingested_at, 1, 10)) "
                        "FROM performances")
        self.assertEqual(ours, 2, "two ingest runs: 2026-08-09 and 2026-08-15")

    def test_ringer_tally_attribution(self):
        """Per row or per performance, and 1,333 performances have no band."""
        rows = self.one("SELECT COUNT(*) FROM performance_ringers")
        covered = self.one("SELECT COUNT(DISTINCT perf_id) FROM performance_ringers")
        self.assertEqual(rows, 1_969_949)
        self.assertEqual(covered, 292_138)
        self.assertEqual(293_471 - covered, 1_333)
        dupes = self.one("""
            SELECT COUNT(*) FROM (
              SELECT perf_id, name FROM performance_ringers
              WHERE name IS NOT NULL AND TRIM(name) <> ''
              GROUP BY perf_id, name HAVING COUNT(*) > 1)""")
        self.assertEqual(dupes, 3_414)

    def test_active_ringer_threshold_is_load_bearing(self):
        """The cohort roughly halves with each doubling, so 50 is a real choice."""
        def cohort(n):
            return self.one(f"""
                SELECT COUNT(*) FROM (
                  SELECT name FROM performance_ringers
                  WHERE name IS NOT NULL AND TRIM(name) <> ''
                  GROUP BY name HAVING COUNT(*) >= {n})""")
        self.assertEqual(cohort(50), 6_902)
        self.assertEqual(cohort(100), 4_194)
        self.assertGreater(cohort(25), cohort(50))
        self.assertGreater(cohort(50), cohort(100))


if __name__ == "__main__":
    unittest.main()
