"""Regression tests for the dead-paper analysis (R-37).

The published figures, and the two properties the argument rests on: that the
matching works in both directions, and that controlling for composer credit
barely moves the answer. If either stops being true the conclusion changes, so
both are pinned rather than just the headline.
"""

import sqlite3
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from analyse_dead_paper import (  # noqa: E402
    askable_compositions,
    composer_key_of,
    performance_signatures,
)

DB = ROOT / "data" / "change-ringing.db"


class TestComposerKeying(unittest.TestCase):
    """The key comes from R-36, and these are the cases that broke it there."""

    def test_plain_and_qualified_credits(self):
        self.assertEqual(composer_key_of("Donald F Morrison"), "d-morrison")
        self.assertEqual(composer_key_of("D F Morrison No. 108 (2 parts)"),
                         "d-morrison")
        self.assertEqual(composer_key_of("Composed by Charles Middleton"),
                         "c-middleton")

    def test_credits_that_name_nobody(self):
        for s in ("Traditional", "trad", "BEW", "n/a Williams", ""):
            self.assertIsNone(composer_key_of(s), f"{s!r} should have no key")


@unittest.skipUnless(DB.exists(), f"no replica at {DB}; build one first (R-27)")
class TestDeadPaperFigures(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.conn = sqlite3.connect(str(DB))
        cls.sigs, cls.seen, _, _ = performance_signatures(cls.conn)
        cls.asks = askable_compositions(cls.conn)

    def test_askable_population(self):
        self.assertEqual(len(self.asks), 55_358)
        self.assertEqual(len(self.sigs), 19_704)

    def test_the_headline_is_the_controlled_figure(self):
        ctrl = [a for a in self.asks if a[0] in self.seen]
        un = [a for a in ctrl if (a[0], a[1], a[2]) not in self.sigs]
        self.assertEqual(len(ctrl), 53_598)
        self.assertEqual(len(un), 34_576)
        self.assertAlmostEqual(100 * len(un) / len(ctrl), 64.5, places=1)

    def test_controlling_for_composer_credit_barely_moves_it(self):
        """The control is what makes the figure defensible, and it must be small.

        If restricting to known composers moved the answer a lot, the result
        would be about missing credits rather than about unrung compositions.
        It moves it by 1.1 points.
        """
        raw = [a for a in self.asks if (a[0], a[1], a[2]) not in self.sigs]
        raw_pct = 100 * len(raw) / len(self.asks)
        ctrl = [a for a in self.asks if a[0] in self.seen]
        ctrl_pct = 100 * len([a for a in ctrl
                              if (a[0], a[1], a[2]) not in self.sigs]) / len(ctrl)
        self.assertLess(abs(raw_pct - ctrl_pct), 2.0,
                        "the control should barely move the figure")

    def test_the_match_works_in_reverse(self):
        """Validation, not decoration: a broken join shows near zero here.

        61.8% of usable performances find a library composition with the same
        signature. That is what licenses reading the 64.5% as a library that is
        not rung rather than a join that does not work.
        """
        comp_sigs = {(k, mt, ln) for k, mt, ln, _, _ in self.asks}
        hit = miss = 0
        for credit, title, changes in self.conn.execute("""
                SELECT p.composer, m.title, p.changes FROM performances p
                JOIN performance_methods pm ON pm.perf_id = p.perf_id AND pm.ord = 0
                JOIN methods m ON m.method_id = pm.method_id
                WHERE p.composer IS NOT NULL AND TRIM(p.composer) <> ''
                  AND p.changes IS NOT NULL"""):
            k = composer_key_of(credit)
            if not k:
                continue
            if (k, title, int(changes)) in comp_sigs:
                hit += 1
            else:
                miss += 1
        self.assertEqual(hit, 34_580)
        self.assertEqual(miss, 21_349)
        self.assertGreater(100 * hit / (hit + miss), 50,
                           "a hit rate this low would mean the join is broken, "
                           "not that the library is dead")


if __name__ == "__main__":
    unittest.main()
