import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from sqlfile import strip_comments, statements, statement


class TestSqlFileParser(unittest.TestCase):
    """Test comment stripping and statement splitting in SQL files."""

    def test_strip_comments_basic(self):
        """Standard whole-line and trailing comment stripping."""
        sql = "-- Leading comment\nSELECT 1; -- Trailing comment\nSELECT 2;"
        stripped = strip_comments(sql)
        self.assertNotIn("Leading comment", stripped)
        self.assertNotIn("Trailing comment", stripped)
        self.assertIn("SELECT 1;", stripped)
        self.assertIn("SELECT 2;", stripped)

    def test_strip_comments_preserves_strings_with_dashes(self):
        """String literals containing dashes must not be stripped."""
        sql = "SELECT 'a--b' AS note, 'c--d--e' AS text;"
        stripped = strip_comments(sql)
        self.assertEqual(stripped.strip(), "SELECT 'a--b' AS note, 'c--d--e' AS text;")

    def test_strip_comments_handles_escaped_quotes(self):
        """Doubled single quotes inside strings toggle state properly."""
        sql = "SELECT 'it''s a test' AS note; -- comment with 'quote'\nSELECT 2;"
        stripped = strip_comments(sql)
        self.assertIn("'it''s a test'", stripped)
        self.assertNotIn("comment with 'quote'", stripped)
        self.assertIn("SELECT 2;", stripped)

    def test_statements_splitting(self):
        """Statement extraction from a SQL file."""
        cases = [
            ("SELECT 1; -- trailing; with a semicolon\nSELECT 2;", 2),
            ("-- 81% of things don't work\nSELECT 1;", 1),
            ("SELECT 'a--b' AS x;", 1),
            ("SELECT 'it''s fine' AS x; -- and; this\nSELECT 2;", 2),
        ]
        for text, expected_count in cases:
            with tempfile.NamedTemporaryFile("w", suffix=".sql", delete=False, encoding="utf-8") as f:
                f.write(text)
                temp_path = f.name
            try:
                stmts = statements(temp_path)
                self.assertEqual(len(stmts), expected_count, f"Failed on input: {text!r}")
            finally:
                Path(temp_path).unlink(missing_ok=True)

    def test_statement_by_index(self):
        """Index-based single statement retrieval."""
        text = "SELECT 1;\nSELECT 2;\nSELECT 3;"
        with tempfile.NamedTemporaryFile("w", suffix=".sql", delete=False, encoding="utf-8") as f:
            f.write(text)
            temp_path = f.name
        try:
            self.assertEqual(statement(temp_path, 0), "SELECT 1")
            self.assertEqual(statement(temp_path, 1), "SELECT 2")
            self.assertEqual(statement(temp_path, 2), "SELECT 3")
        finally:
            Path(temp_path).unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
