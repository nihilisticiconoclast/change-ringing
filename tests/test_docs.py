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
