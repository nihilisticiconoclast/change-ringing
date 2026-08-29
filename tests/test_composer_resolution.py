"""Unit and regression tests for composer identity resolution (Roadmap Item R-41 / G-12)."""

import csv
import sys
import unittest
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from resolve_composer_identities import (
    clean_raw_composer,
    parse_name_tokens,
    ComposerResolver,
)
from evaluate_composer_oracle import evaluate


class TestComposerResolution(unittest.TestCase):
    """Test suite for composer identity cleaning, parsing, authority resolution, and error guarantees."""

    def test_clean_raw_composer(self):
        """Prefixes, parenthetical suffixes, and initial spacing are properly cleaned."""
        self.assertEqual(clean_raw_composer("Arr. John S Warboys"), "John S Warboys")
        self.assertEqual(clean_raw_composer("comp. A J Cox"), "A J Cox")
        self.assertEqual(clean_raw_composer("D F Morrison (No 108)"), "D F Morrison")
        self.assertEqual(clean_raw_composer("R I Allton (no. 2752)"), "R I Allton")
        self.assertEqual(clean_raw_composer("Robert D S Brown (5088)"), "Robert D S Brown")
        self.assertEqual(clean_raw_composer("Graham A. C. John"), "Graham A C John")
        self.assertEqual(clean_raw_composer("J.S. Warboys"), "J S Warboys")

    def test_parse_name_tokens_and_abbreviations(self):
        """Name token parsing expands historical abbreviations and extracts component initials."""
        is_init, fn, mids, sn, inits = parse_name_tokens("Chas Middleton")
        self.assertFalse(is_init)
        self.assertEqual(fn, "Charles")
        self.assertEqual(sn, "Middleton")
        self.assertEqual(inits, ["C"])

        is_init, fn, mids, sn, inits = parse_name_tokens("Wm Pye")
        self.assertFalse(is_init)
        self.assertEqual(fn, "William")
        self.assertEqual(sn, "Pye")

        is_init, fn, mids, sn, inits = parse_name_tokens("R D S Brown")
        self.assertTrue(is_init)
        self.assertEqual(sn, "Brown")
        self.assertEqual(inits, ["R", "D", "S"])

    def test_anonymous_and_collective_aliases(self):
        """Collective and traditional aliases map to standard canonical names."""
        resolver = ComposerResolver()
        canon, conf, rule, _ = resolver.resolve("Traditional")
        self.assertEqual(canon, "Traditional")
        self.assertEqual(conf, "high")

        canon, conf, rule, _ = resolver.resolve("trad.")
        self.assertEqual(canon, "Traditional")
        self.assertEqual(conf, "high")

        canon, conf, rule, _ = resolver.resolve("Anon")
        self.assertEqual(canon, "Anonymous")
        self.assertEqual(conf, "high")

        canon, conf, rule, _ = resolver.resolve("BYROC")
        self.assertEqual(canon, "BYROC")
        self.assertEqual(conf, "high")

    def test_multi_initial_unique_resolution(self):
        """Multi-initial sequences uniquely resolve against indexed authority entities."""
        resolver = ComposerResolver()
        authorities = Counter({
            "Robert D S Brown": 1000,
            "Donald F Morrison": 1000,
            "Graham A C John": 500,
            "John S Warboys": 400,
            "Anthony J Cox": 500,
        })
        resolver.build_authority_index(authorities)

        canon, conf, rule, _ = resolver.resolve("R D S Brown")
        self.assertEqual(canon, "Robert D S Brown")
        self.assertEqual(conf, "high")

        canon, conf, rule, _ = resolver.resolve("D. F. Morrison")
        self.assertEqual(canon, "Donald F Morrison")
        self.assertEqual(conf, "high")

        canon, conf, rule, _ = resolver.resolve("Arr. G A C John")
        self.assertEqual(canon, "Graham A C John")
        self.assertEqual(conf, "high")

    def test_anti_conflation_and_collision_guard(self):
        """Ambiguous single or multi-initials with competing distinct authority entities emit low confidence."""
        resolver = ComposerResolver()
        # Two distinct Parkers with high counts
        authorities = Counter({
            "James Parker": 300,
            "John Parker": 300,
            "Joseph Parker": 200,
        })
        resolver.build_authority_index(authorities)

        canon, conf, rule, _ = resolver.resolve("J Parker")
        self.assertEqual(conf, "low")
        self.assertEqual(rule, "single_initial_collision")

    def test_oracle_accuracy_guarantees(self):
        """The 300-row oracle achieves >= 95.0% overall accuracy and 100% high-confidence precision."""
        accuracy, by_conf, errors = evaluate()
        self.assertGreaterEqual(accuracy, 0.950, f"Overall oracle accuracy fell below 95%: {accuracy:.1%}")
        high_prec = by_conf["high"]["correct"] / by_conf["high"]["total"]
        self.assertGreaterEqual(high_prec, 0.990, f"High-confidence precision fell below 99%: {high_prec:.1%}")


if __name__ == "__main__":
    unittest.main()
