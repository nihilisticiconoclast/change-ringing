"""Unit and regression tests for footnote occasion classification and civic precision (R-43 / G-14)."""

import csv
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from classify_footnote_occasions import classify_footnote

ORACLE_CSV = ROOT / "data" / "footnote_occasion_labels.csv"


class TestFootnoteClassifier(unittest.TestCase):
    """Test suite asserting occasion classification accuracy and royal memorial precision."""

    def test_royal_memorials_and_funerals_not_swallowed_by_civic(self):
        """Royal death tributes and muffled ringing are classified as memorial or funeral, not civic."""
        muffled_queen = "Tolled for 15mins 1/2 muffled for the Civic Service in Memory of Her Majesty Queen Elizabeth II"
        occ, subj, conf, ev = classify_footnote(muffled_queen)
        self.assertEqual(occ, "memorial")

        funeral_queen = "Rung before the funeral of HM Queen Elizabeth II"
        occ, subj, conf, ev = classify_footnote(funeral_queen)
        self.assertEqual(occ, "funeral")

        philip_mem = "In memoriam HRH The Prince Philip, Duke of Edinburgh."
        occ, subj, conf, ev = classify_footnote(philip_mem)
        self.assertEqual(occ, "memorial")

    def test_stage_royal_not_classified_as_civic(self):
        """Method stage name 'Royal' (10 bells) is not misclassified as royal family civic event."""
        stage_first = "1st Royal - 7."
        occ, subj, conf, ev = classify_footnote(stage_first)
        self.assertEqual(occ, "first-performance")

        first_royal_cond = "First Royal as conductor and first in method: 2."
        occ, subj, conf, ev = classify_footnote(first_royal_cond)
        self.assertEqual(occ, "first-performance")

    def test_legitimate_civic_occasions_classified(self):
        """Coronations, proclamations, jubilees, and mayor civic events are classified as civic."""
        coronation = "Rung to celebrate the Coronation of King Charles III"
        occ, subj, conf, ev = classify_footnote(coronation)
        self.assertEqual(occ, "civic")

        jubilee = "Rung for the Platinum Jubilee of Her Majesty Queen Elizabeth II"
        occ, subj, conf, ev = classify_footnote(jubilee)
        self.assertEqual(occ, "civic")

        mayor = "Rung for the installation of the Lord Mayor"
        occ, subj, conf, ev = classify_footnote(mayor)
        self.assertEqual(occ, "civic")


if __name__ == "__main__":
    unittest.main()
