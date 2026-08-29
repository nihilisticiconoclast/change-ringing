"""Unit and regression tests asserting structural golden-file integrity across all page builders (R-42 / G-13)."""

import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import site_chrome
from page_structure import extract_structure, PageStructureExtractor

DOCS_DIR = ROOT / "docs"
GOLDEN_DIR = ROOT / "tests" / "golden"


class TestPageBuilderGoldenFiles(unittest.TestCase):
    """Test suite asserting that page builders preserve structural integrity across builds."""

    def test_all_pages_have_golden_snapshots(self):
        """Every registered page in site_chrome.PAGES has a corresponding committed golden snapshot."""
        self.assertTrue(GOLDEN_DIR.exists(), f"Golden directory missing: {GOLDEN_DIR}")

        for href, label, desc in site_chrome.PAGES:
            stem = href.replace(".html", "")
            golden_path = GOLDEN_DIR / f"{stem}.json"
            self.assertTrue(
                golden_path.exists(),
                f"Missing golden snapshot for {href} at {golden_path}. "
                f"Run `python scripts/generate_golden_snapshots.py` to generate it."
            )

    def test_published_pages_match_golden_structure(self):
        """Every published page in docs/ matches its committed golden structure exactly."""
        mismatches = []

        for href, label, desc in site_chrome.PAGES:
            html_path = DOCS_DIR / href
            if not html_path.exists():
                self.fail(f"Registered page {href} missing in {DOCS_DIR}")

            stem = href.replace(".html", "")
            golden_path = GOLDEN_DIR / f"{stem}.json"

            raw_html = html_path.read_text(encoding="utf-8", errors="ignore")
            current_struct = extract_structure(raw_html)

            saved_struct = json.loads(golden_path.read_text(encoding="utf-8"))

            if current_struct != saved_struct:
                # Identify specific mismatched components for a helpful error message
                diffs = []
                for k in saved_struct:
                    if current_struct.get(k) != saved_struct.get(k):
                        diffs.append(k)
                mismatches.append(f"{href} (drifted keys: {', '.join(diffs)})")

        self.assertEqual(
            mismatches,
            [],
            f"Structural drift detected in {len(mismatches)} page(s):\n"
            + "\n".join(f"  - {m}" for m in mismatches)
            + "\nIf this change was intentional, bless it with `python scripts/generate_golden_snapshots.py`."
        )

    def test_data_invariance_property(self):
        """Changes to internal numeric statistics do not alter page structural fingerprints."""
        sample_html = """<!doctype html>
        <html>
        <head><title>Test Page</title></head>
        <body>
            <nav class="nav-bar"><a href="index.html">Home</a></nav>
            <h1>Total Performances: 293,471</h1>
            <section id="stats">
                <p>Found 51,451 bells across 12,635 towers.</p>
                <table>
                    <thead><tr><th>Stage</th><th>Count</th></tr></thead>
                    <tbody><tr><td>Major</td><td>44,040</td></tr></tbody>
                </table>
            </section>
            <footer class="site-footer"><a href="licence.html">CC BY-SA 4.0</a></footer>
        </body>
        </html>"""

        drifted_data_html = """<!doctype html>
        <html>
        <head><title>Test Page</title></head>
        <body>
            <nav class="nav-bar"><a href="index.html">Home</a></nav>
            <h1>Total Performances: 999,999</h1>
            <section id="stats">
                <p>Found 88,888 bells across 99,999 towers.</p>
                <table>
                    <thead><tr><th>Stage</th><th>Count</th></tr></thead>
                    <tbody><tr><td>Major</td><td>77,777</td></tr></tbody>
                </table>
            </section>
            <footer class="site-footer"><a href="licence.html">CC BY-SA 4.0</a></footer>
        </body>
        </html>"""

        struct1 = extract_structure(sample_html)
        struct2 = extract_structure(drifted_data_html)
        self.assertEqual(struct1, struct2, "Structural extractor should be invariant to numeric data changes.")

    def test_negative_structural_drift_fails_loudly(self):
        """Removing sections, tables, or altering heading levels causes a structural mismatch."""
        base_html = """<!doctype html>
        <html>
        <head><title>Test Page</title></head>
        <body>
            <nav class="nav-bar"><a href="index.html">Home</a></nav>
            <h1>Page Heading</h1>
            <section id="main-sec">
                <table><thead><tr><th>Col A</th><th>Col B</th></tr></thead></table>
            </section>
            <footer class="site-footer"></footer>
        </body>
        </html>"""

        base_struct = extract_structure(base_html)

        # 1. Dropping a table
        broken_html_1 = base_html.replace("<table><thead><tr><th>Col A</th><th>Col B</th></tr></thead></table>", "")
        self.assertNotEqual(base_struct, extract_structure(broken_html_1))

        # 2. Altering heading level from h1 to h2
        broken_html_2 = base_html.replace("<h1>Page Heading</h1>", "<h2>Page Heading</h2>")
        self.assertNotEqual(base_struct, extract_structure(broken_html_2))

        # 3. Dropping a section container
        broken_html_3 = base_html.replace('<section id="main-sec">', '<div id="main-sec">').replace('</section>', '</div>')
        self.assertNotEqual(base_struct, extract_structure(broken_html_3))


if __name__ == "__main__":
    unittest.main()
