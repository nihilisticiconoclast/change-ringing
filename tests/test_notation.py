"""Unit tests for place-notation parser and lead-head calculations (scripts/notation.py)."""

import unittest
import sys
from pathlib import Path

# Ensure scripts directory is on sys.path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from notation import (
    sym_to_place,
    split_changes,
    apply_change,
    expand,
    lead_rows,
    lead_head,
    BELL_ORDER,
)


class TestNotationParser(unittest.TestCase):
    """Test individual components of place notation parsing and execution."""

    def test_sym_to_place(self):
        """Symbol to 0-indexed place conversion across all stages (1..16)."""
        # Standard numeric bells
        self.assertEqual(sym_to_place("1"), 0)
        self.assertEqual(sym_to_place("2"), 1)
        self.assertEqual(sym_to_place("9"), 8)
        self.assertEqual(sym_to_place("0"), 9)

        # Extended bell symbols
        self.assertEqual(sym_to_place("E"), 10)
        self.assertEqual(sym_to_place("e"), 10)  # case-insensitive
        self.assertEqual(sym_to_place("T"), 11)
        self.assertEqual(sym_to_place("t"), 11)
        self.assertEqual(sym_to_place("A"), 12)
        self.assertEqual(sym_to_place("B"), 13)
        self.assertEqual(sym_to_place("C"), 14)
        self.assertEqual(sym_to_place("D"), 15)

        # Invalid symbols return None
        self.assertIsNone(sym_to_place("Z"))
        self.assertIsNone(sym_to_place("-"))
        self.assertIsNone(sym_to_place(" "))

    def test_split_changes(self):
        """Parsing change blocks into discrete changes."""
        # Self-delimiting cross notation (-)
        self.assertEqual(split_changes("-36-14"), ["-", "36", "-", "14"])
        # Self-delimiting x notation
        self.assertEqual(split_changes("x16x16"), ["-", "16", "-", "16"])
        # Dot-delimited notation
        self.assertEqual(split_changes("3.1.5.1.5"), ["3", "1", "5", "1", "5"])
        # Mixed self-delimiting and dot notation
        self.assertEqual(split_changes("-58-14.58-58.36"), ["-", "58", "-", "14", "58", "-", "58", "36"])
        # Empty input
        self.assertEqual(split_changes(""), [])

    def test_apply_change_cross(self):
        """Cross changes (-) swap all pairs on even stages."""
        # 6 bells
        rounds6 = list("123456")
        self.assertEqual(apply_change(rounds6, "-"), list("214365"))

        # 8 bells
        rounds8 = list("12345678")
        self.assertEqual(apply_change(rounds8, "-"), list("21436587"))

    def test_apply_change_places(self):
        """Place changes hold specified bells and swap remaining pairs."""
        rounds6 = list("123456")

        # 12: Lead and 2nds place made, 3-4 and 5-6 swap
        self.assertEqual(apply_change(rounds6, "12"), list("124365"))

        # 14: Lead and 4ths place made, 2-3 and 5-6 swap
        self.assertEqual(apply_change(rounds6, "14"), list("132465"))

        # 36: 3rds and 6ths place made, 1-2 and 4-5 swap
        self.assertEqual(apply_change(rounds6, "36"), list("213546"))

        # 16: Lead and Lie made, 2-3 and 4-5 swap
        self.assertEqual(apply_change(rounds6, "16"), list("132546"))

    def test_apply_change_odd_stage_gap(self):
        """Odd stage change handling where unpartnered bells stay put."""
        rounds5 = list("12345")
        # 3 on 5 bells: 1-2 swap, 3 makes place, 4-5 swap
        self.assertEqual(apply_change(rounds5, "3"), list("21354"))
        # 1 on 5 bells: 1 makes place, 2-3 swap, 4-5 swap
        self.assertEqual(apply_change(rounds5, "1"), list("13254"))

    def test_expand_symmetry(self):
        """Expansion of abbreviated palindromic notation."""
        # Standard mirror_drop_last (A,B format)
        # "-36-14,12" -> a is ["-","36","-","14"], b is ["12"]
        # reverse drop last is ["-","36","-"]
        # result: ["-","36","-","14","-","36","-","12"]
        expanded = expand("-36-14,12", rule="mirror_drop_last")
        self.assertEqual(expanded, ["-", "36", "-", "14", "-", "36", "-", "12"])

        # Asymmetric method (no comma)
        asym = expand("3.1.5.1.5.1")
        self.assertEqual(asym, ["3", "1", "5", "1", "5", "1"])


class TestCanonicalMethodsLeadHead(unittest.TestCase):
    """Verify lead head computation against ground-truth change ringing methods."""

    def test_plain_bob_minor(self):
        """Plain Bob Minor: &-16-16-16,12 (stage 6) -> 135264"""
        nt = "-16-16-16,12"
        lh = lead_head(nt, 6)
        self.assertEqual(lh, "135264")
        rows = lead_rows(nt, 6)
        self.assertEqual(len(rows), 13)  # 12 changes + initial rounds

    def test_cambridge_surprise_minor(self):
        """Cambridge Surprise Minor: &-36-14-12-36-14-56,12 (stage 6) -> 156342"""
        nt = "-36-14-12-36-14-56,12"
        lh = lead_head(nt, 6)
        self.assertEqual(lh, "156342")
        rows = lead_rows(nt, 6)
        self.assertEqual(len(rows), 25)  # 24 changes + initial rounds

    def test_london_surprise_minor(self):
        """London Surprise Minor: 36-36.14-12-36.14-14.36,12 (stage 6) -> 142635"""
        nt = "36-36.14-12-36.14-14.36,12"
        lh = lead_head(nt, 6)
        self.assertEqual(lh, "142635")

    def test_grandsire_doubles(self):
        """Grandsire Doubles: 3.1.5.1.5.1.5.1.5.1 (stage 5) -> 12534"""
        nt = "3.1.5.1.5.1.5.1.5.1"
        lh = lead_head(nt, 5)
        self.assertEqual(lh, "12534")

    def test_plain_bob_major(self):
        """Plain Bob Major: &-18-18-18-18,12 (stage 8) -> 13527486"""
        nt = "-18-18-18-18,12"
        lh = lead_head(nt, 8)
        self.assertEqual(lh, "13527486")

    def test_cambridge_surprise_major(self):
        """Cambridge Surprise Major: &-38-14-1258-36-14-58-16-78,12 (stage 8) -> 15738264"""
        nt = "-38-14-1258-36-14-58-16-78,12"
        lh = lead_head(nt, 8)
        self.assertEqual(lh, "15738264")

    def test_bristol_surprise_major(self):
        """Bristol Surprise Major: &-58-14.58-58.36.14-14.58-14-18,18 (stage 8) -> 14263857"""
        nt = "-58-14.58-58.36.14-14.58-14-18,18"
        lh = lead_head(nt, 8)
        self.assertEqual(lh, "14263857")

    def test_superlative_surprise_major(self):
        """Superlative Surprise Major: &-36-14-58-36-14-58-36-78,12 (stage 8) -> 15738264"""
        nt = "-36-14-58-36-14-58-36-78,12"
        lh = lead_head(nt, 8)
        self.assertEqual(lh, "15738264")

    def test_yorkshire_surprise_major(self):
        """Yorkshire Surprise Major: &-38-14-58-16-12-38-14-78,12 (stage 8) -> 15738264"""
        nt = "-38-14-58-16-12-38-14-78,12"
        lh = lead_head(nt, 8)
        self.assertEqual(lh, "15738264")

    def test_multi_stage_benchmark_methods(self):
        """Parameterized test over diverse canonical methods from Minimus (4) to Sextuples (16)."""
        benchmark_cases = [
            ("Plain Bob Minimus", 4, "-14-14,12", "1342"),
            ("Reverse Bob Minimus", 4, "-14-34,14", "1342"),
            ("Stedman Doubles", 5, "3.1.5.3.1.3,1", "53412"),
            ("Stedman Triples", 7, "3.1.7.3.1.3,1", "6347251"),
            ("Kent Treble Bob Minor", 6, "34-34.16-12-16-12-16,16", "142635"),
            ("Oxford Treble Bob Minor", 6, "-34-16-12-16-12-16,16", "142635"),
            ("Double Norwich Court Bob Major", 8, "-14-36-58-18,18", "18674523"),
            ("Lincolnshire Surprise Major", 8, "-38-14-58-16-14-58-36-78,12", "15738264"),
            ("Pudsey Surprise Major", 8, "-58-16-12-38-14-58-16-78,12", "15738264"),
            ("Rutland Surprise Major", 8, "-38-14-58-16-14-38-34-18,12", "14263857"),
            ("Yorkshire Surprise Royal", 10, "-30-14-50-16-1270-38-14-50-16-90,12", "1573920486"),
            ("Bristol Surprise Royal", 10, "-50-14.50-50.36.14-70.58.16-16.70-16-10,10", "1352749608"),
            ("Stedman Caters", 9, "3.1.9.3.1.3,1", "634829175"),
            ("Stedman Cinques", 11, "3.1.E.3.1.3,1", "6348201E597"),
            ("Bristol Surprise Maximus", 12, "-5T-14.5T-5T.36.14-7T.58.16-9T.70.18-18.9T-18-1T,1T", "1795E3T20486"),
        ]

        for title, stage, nt, expected_lh in benchmark_cases:
            with self.subTest(method=title, stage=stage):
                actual_lh = lead_head(nt, stage)
                self.assertEqual(
                    actual_lh,
                    expected_lh,
                    f"{title} (stage {stage}, notation {nt}): expected {expected_lh}, got {actual_lh}"
                )

    def test_plain_bob_royal(self):
        """Plain Bob Royal: &-10-10-10-10-10,12 (stage 10) -> 1352749608"""
        nt = "-10-10-10-10-10,12"
        lh = lead_head(nt, 10)
        self.assertEqual(lh, "1352749608")

    def test_cambridge_surprise_maximus(self):
        """Cambridge Surprise Maximus (stage 12) -> 157392E4T608"""
        nt = "-3T-14-125T-36-147T-58-169T-70-18-9T-10-ET,12"
        lh = lead_head(nt, 12)
        self.assertEqual(lh, "157392E4T608")


if __name__ == "__main__":
    unittest.main()
