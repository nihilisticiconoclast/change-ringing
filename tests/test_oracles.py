"""Regression tests asserting oracle benchmarks and accuracy guarantees."""

import csv
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from classify_regional_traditions import classify
from audit_privacy_and_licences import (
    check_licence_files,
    check_html_page_licence_footers,
    check_privacy_disclaimed_pages,
    check_documentation_privacy,
)


class TestOraclesAndCompliance(unittest.TestCase):
    """Assert ground-truth oracle benchmarks and licence/privacy compliance."""

    def test_regional_traditions_oracle_accuracy(self):
        """Regional traditions classifier achieves >= 98.0% accuracy on ground-truth oracle."""
        oracle_path = ROOT / "data" / "regional_traditions_oracle.csv"
        self.assertTrue(oracle_path.exists(), f"Oracle file missing: {oracle_path}")

        with open(oracle_path, encoding="utf-8") as f:
            oracle_rows = list(csv.DictReader(f))

        self.assertGreaterEqual(len(oracle_rows), 200, "Expected at least 200 ground-truth rows")

        correct = 0
        total = len(oracle_rows)
        mismatches = []

        for row in oracle_rows:
            raw_text = row["method_text"]
            expected = row["label"]
            predicted = classify(raw_text)
            if predicted == expected:
                correct += 1
            else:
                mismatches.append((raw_text, expected, predicted))

        accuracy = correct / total
        self.assertGreaterEqual(
            accuracy,
            0.980,
            f"Regional traditions accuracy dropped below 98%: {correct}/{total} ({accuracy:.1%}). Mismatches: {mismatches[:5]}"
        )

    def test_licence_files_compliance(self):
        """All upstream licences and data notices are present and unmodified."""
        failures = check_licence_files()
        self.assertEqual(failures, [], f"Licence files compliance failure: {failures}")

    def test_html_page_footers_compliance(self):
        """All 13 documentation pages contain CC BY-SA 4.0 licence footers."""
        failures = check_html_page_licence_footers()
        self.assertEqual(failures, [], f"Page footers compliance failure: {failures}")

    def test_privacy_disclaimed_pages_compliance(self):
        """Analytical pages state their privacy disclaimers explicitly."""
        failures = check_privacy_disclaimed_pages()
        self.assertEqual(failures, [], f"Privacy disclaimers compliance failure: {failures}")

    def test_documentation_privacy_compliance(self):
        """Documentation prose does not create individual ringer appearance tables."""
        failures = check_documentation_privacy()
        self.assertEqual(failures, [], f"Documentation privacy failure: {failures}")


if __name__ == "__main__":
    unittest.main()
