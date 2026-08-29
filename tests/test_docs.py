"""Unit and regression tests for documentation verification and roadmap consistency (scripts/verify_docs.py)."""

import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from verify_docs import (
    is_row,
    cells,
    check_tables,
    check_ids,
    check_now_holds_only_live_work,
    SETTLED,
    _title,
)


class TestDocsVerification(unittest.TestCase):
    """Test markdown table parsing and cross-roadmap ID consistency."""

    def test_is_row_and_cells_counter(self):
        """is_row and cells accurately count table cells and honour escaped pipes."""
        self.assertTrue(is_row("| a | b | c |"))
        self.assertFalse(is_row("Not a table row"))
        self.assertFalse(is_row("|"))

        self.assertEqual(cells("| a | b | c |"), 3)
        self.assertEqual(cells("| a \\| still a | b |"), 2)

    def test_title_cleaner(self):
        """_title strips links, emphasis, and trailing parentheticals."""
        heading_line = "## G-6 — Practice night: Dove vs BellBoard *(next)*"
        self.assertEqual(_title(heading_line, "G-6"), "practice night: dove vs bellboard")

        table_line = "| G-1 | Method extension lineage from place notation | **Done** |"
        self.assertEqual(_title(table_line, "G-1"), "method extension lineage from place notation")

    def test_title_strips_every_trailing_parenthetical(self):
        """A heading carrying both the delivered item and its status is one name.

        "V-8 — Load CompLib in full (R-20) *(done)*" and the summary row
        "| V-8 | Load CompLib in full (R-20) |" are the same item. Stripping a
        single parenthetical left the heading as "... (r-20)" and reported two
        different items, which is a false positive in the check, not a fault in
        the document.
        """
        heading = "## V-8 — Load CompLib in full (R-20) *(done)*"
        row = "| V-8 | Load CompLib in full (R-20) | **Done** |"
        self.assertEqual(_title(heading, "V-8"), _title(row, "V-8"))
        self.assertEqual(_title(heading, "V-8"), "load complib in full")

    def test_settled_matches_only_the_start_of_a_state_cell(self):
        """A finished row announces itself first; a live one merely mentions it.

        The distinction the check rests on. R-46 opens "Unblocked: R-10 is done"
        and is live work; a row opening "**Done** — PR #27" is not. Matching
        anywhere in the cell would fail both.
        """
        self.assertTrue(SETTLED.match("**Done** — PR #27, 36 unit tests"))
        self.assertTrue(SETTLED.match("Merged 86a00c3 — PR #10"))
        self.assertTrue(SETTLED.match("**Superseded by R-45**, which carries it"))
        self.assertFalse(SETTLED.match("Unblocked: R-10 is done, so there are now"))
        self.assertFalse(SETTLED.match("After R-44. Your CSV check reported SKIP"))
        self.assertFalse(SETTLED.match("The open half of R-26. 36 tests cover"))

    def test_now_section_is_a_queue(self):
        """Every row under "Now" is work still to do.

        Caught seventeen finished rows on its first run, two of which (R-28,
        R-35) had been superseded by rows sitting a few lines above them.
        """
        fails = check_now_holds_only_live_work()
        self.assertEqual(fails, [], f"'Now' holds finished work: {fails}")

    def test_all_markdown_tables_render_correctly(self):
        """All markdown files across repository have valid tables without rogue blank lines."""
        all_failures = []
        md_files = list(ROOT.glob("docs/**/*.md")) + list(ROOT.glob("*.md")) + list(ROOT.glob("data/**/*.md"))
        for md_file in md_files:
            if not md_file.exists():
                continue
            fails = check_tables(md_file)
            if fails:
                all_failures.extend(fails)

        self.assertEqual(all_failures, [], f"Markdown table validation failures: {all_failures}")

    def test_all_roadmap_ids_unique_and_resolvable(self):
        """Roadmap item IDs (R-nn, G-nn, V-nn) are unique, consistently named, and resolvable."""
        fails, defined = check_ids()
        self.assertEqual(fails, [], f"Roadmap ID cross-reference failures: {fails}")
        self.assertGreater(len(defined.get("R", {})), 0)
        self.assertGreater(len(defined.get("G", {})), 0)
        self.assertGreater(len(defined.get("V", {})), 0)


if __name__ == "__main__":
    unittest.main()
