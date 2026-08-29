import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from analyse_composition_demands import parse_calling_string


class TestCompositionDemands(unittest.TestCase):
    """Test calling string parsing, macro expansion, repeat parsing, and token extraction."""

    def test_parse_simple_calling(self):
        """Standard 1-part calling string without repeats."""
        calling = "-W -H -M -B"
        part_count, calls, total_calls = parse_calling_string(calling)
        self.assertEqual(part_count, 1)
        self.assertEqual(len(calls), 4)
        self.assertEqual(total_calls, 4)
        self.assertEqual(calls, [("bob", "W"), ("bob", "H"), ("bob", "M"), ("bob", "B")])

    def test_parse_multi_part_with_repeats(self):
        """Multi-part calling with inner call repeats: 5(2(-M) 2(-W) 3(-H))."""
        calling = "5(2(-M) 2(-W) 3(-H))"
        part_count, calls, total_calls = parse_calling_string(calling)
        self.assertEqual(part_count, 5)
        self.assertEqual(len(calls), 7)  # 2 M + 2 W + 3 H = 7 calls per part
        self.assertEqual(total_calls, 35)  # 7 * 5 = 35 total calls
        expected_part = [
            ("bob", "M"), ("bob", "M"),
            ("bob", "W"), ("bob", "W"),
            ("bob", "H"), ("bob", "H"), ("bob", "H")
        ]
        self.assertEqual(calls, expected_part)

    def test_parse_singles_and_plains(self):
        """Singles (sH), plains (pW), and extremes (xH) classification."""
        calling = "sH -W sM pB xF"
        part_count, calls, total_calls = parse_calling_string(calling)
        self.assertEqual(part_count, 1)
        self.assertEqual(len(calls), 5)
        self.assertEqual(calls[0], ("single", "H"))
        self.assertEqual(calls[1], ("bob", "W"))
        self.assertEqual(calls[2], ("single", "M"))
        self.assertEqual(calls[3], ("plain", "B"))
        self.assertEqual(calls[4], ("extreme", "F"))

    def test_parse_unicode_dashes(self):
        """Calling strings with unicode en-dash, em-dash, and minus signs."""
        calling = "3(\u2013H \u2014W \u2212M -B)"
        part_count, calls, total_calls = parse_calling_string(calling)
        self.assertEqual(part_count, 3)
        self.assertEqual(len(calls), 4)
        self.assertEqual(total_calls, 12)
        self.assertTrue(all(c[0] == "bob" for c in calls))
        self.assertEqual([c[1] for c in calls], ["H", "W", "M", "B"])

    def test_parse_macros_and_variations(self):
        """Macro expansion @A(...) and stripping part variations +2[sH sH]."""
        calling = "@A(-M -W -H) 3(@A +2[sH sH] -B)"
        part_count, calls, total_calls = parse_calling_string(calling)
        self.assertEqual(part_count, 3)
        # @A expands to 3 calls (-M -W -H), + -B = 4 calls per part (variation ignored for baseline count)
        self.assertEqual(len(calls), 4)
        self.assertEqual(total_calls, 12)
        self.assertEqual([c[1] for c in calls], ["M", "W", "H", "B"])

    def test_parse_empty_and_none(self):
        """Handles empty and None strings safely."""
        self.assertEqual(parse_calling_string(""), (1, [], 0))
        self.assertEqual(parse_calling_string(None), (1, [], 0))


if __name__ == "__main__":
    unittest.main()
