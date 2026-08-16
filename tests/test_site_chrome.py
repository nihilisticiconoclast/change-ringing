import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from site_chrome import (
    PAGES,
    HREFS,
    BASE_CSS,
    CHROME_CSS,
    apply_chrome,
    nav_html,
    footer_html,
)


class TestSiteChrome(unittest.TestCase):
    """Test site chrome generation, CSS consolidation, and template expansion."""

    def test_pages_registry_integrity(self):
        """PAGES defines exactly 13 pages with unique hrefs and valid metadata."""
        self.assertEqual(len(PAGES), 13)
        self.assertEqual(len(set(HREFS)), 13)

        for href, label, desc in PAGES:
            self.assertTrue(href.endswith(".html"), f"Invalid page href: {href}")
            self.assertTrue(len(label) > 0, f"Missing label for {href}")
            self.assertTrue(len(desc) > 0, f"Missing description for {href}")
            # Every registered page must physically exist in docs/
            doc_path = ROOT / "docs" / href
            self.assertTrue(doc_path.exists(), f"Registered page missing in docs/: {doc_path}")

    def test_apply_chrome_standard(self):
        """apply_chrome expands NAV and FOOTER and injects BASE_CSS + CHROME_CSS."""
        sample_template = """<!doctype html>
<html>
<head>
  <title>Test Page</title>
  <style>
    .custom-widget { color: red; }
  </style>
</head>
<body>
  <!--NAV:index.html-->
  <main>
    <h1>Test Content</h1>
  </main>
  <!--FOOTER:index.html-->
</body>
</html>"""
        result = apply_chrome(sample_template, dark=False)

        # Markers replaced
        self.assertNotIn("<!--NAV:", result)
        self.assertNotIn("<!--FOOTER:", result)

        # Nav and footer elements present
        self.assertIn("class=\"nav-bar", result)
        self.assertIn("class=\"site-footer\"", result)

        # CSS injection
        self.assertIn(":root", result)  # from BASE_CSS
        self.assertIn(".nav-bar", result)  # from CHROME_CSS
        self.assertIn(".custom-widget { color: red; }", result)  # custom styles preserved

    def test_apply_chrome_dark_mode(self):
        """apply_chrome with dark=True omits BASE_CSS but includes CHROME_CSS."""
        sample_template = """<!doctype html>
<html>
<head>
  <title>3D Canvas</title>
  <style>
    body { margin: 0; }
  </style>
</head>
<body>
  <!--NAV:nexus.html-->
  <!--FOOTER:nexus.html-->
</body>
</html>"""
        result = apply_chrome(sample_template, dark=True)

        self.assertNotIn("<!--NAV:", result)
        self.assertNotIn("<!--FOOTER:", result)
        self.assertIn(".nav-bar", result)
        self.assertIn("class=\"nav-bar nav-over\"", result)

    def test_apply_chrome_missing_marker_raises(self):
        """apply_chrome raises ValueError when required markers are missing."""
        missing_footer = "<html><head><style></style></head><body><!--NAV:index.html--></body></html>"
        with self.assertRaises(ValueError):
            apply_chrome(missing_footer)

        missing_nav = "<html><head><style></style></head><body><!--FOOTER:index.html--></body></html>"
        with self.assertRaises(ValueError):
            apply_chrome(missing_nav)


if __name__ == "__main__":
    unittest.main()
