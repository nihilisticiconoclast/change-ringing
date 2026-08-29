"""Unit tests for the composer bridge parser (scripts/resolve_composer_bridge.py).

Every case here is a real string from `performances.composer` or a real CompLib
`derived_title`, and most of them are regressions: they are the bugs the residual
disagreement list exposed, which the code passed before they were found.
"""

import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from resolve_composer_bridge import (
    people,
    key,
    compatible,
    is_initials,
    edit_distance_le_1,
    load_adjudication,
)


class TestCreditParser(unittest.TestCase):
    """Turning a free-text credit into the people it names."""

    def test_plain_name(self):
        self.assertEqual(people("Donald F Morrison"), ["Donald F Morrison"])

    def test_qualifier_is_stripped_before_splitting(self):
        """'(SU0308 and SU0403)' must not split one man into two.

        The parenthetical carries an ' and ', so stripping it after the split
        rather than before yields ['J S Warboys (SU0308', 'SU0403)'].
        """
        self.assertEqual(people("J S Warboys (SU0308 and SU0403)"),
                         ["J S Warboys"])
        self.assertEqual(people("D F Morrison No. 108 (2 parts)"),
                         ["D F Morrison"])
        self.assertEqual(people("J J Parker (12 part, 7th obs)"),
                         ["J J Parker"])

    def test_joint_credit_splits_into_people(self):
        self.assertEqual(people("Charles Middleton and Henry Johnson"),
                         ["Charles Middleton", "Henry Johnson"])
        self.assertEqual(
            people("David W Beard, Robert D S Brown and Donald F Morrison"),
            ["David W Beard", "Robert D S Brown", "Donald F Morrison"])

    def test_slash_separates_people(self):
        """Found in the residual list: the credit reached only the second name."""
        self.assertEqual(people("John S. Warboys / Julian Morgan"),
                         ["John S. Warboys", "Julian Morgan"])

    def test_leading_verb_is_not_a_forename(self):
        """'Composed by Charles Middleton' made 'Composed' the forename."""
        self.assertEqual(people("Composed by Charles Middleton"),
                         ["Charles Middleton"])
        self.assertEqual(people("Comp. C Adams"), ["C Adams"])
        self.assertEqual(people("Arranged by John Pladdys (No 14)"),
                         ["John Pladdys"])

    def test_leading_qualifier_leaves_an_unkeyable_surname(self):
        """'Trad Thurstans' and 'n/a Williams' must not key on the surname.

        Stripping the qualifier leaves a bare surname, which cannot carry a
        first initial and is correctly dropped -- better than keying 'Williams'
        against whichever W-surname CompLib holds most of.
        """
        self.assertEqual(people("Trad Thurstans"), [])
        self.assertEqual(people("n/a Williams"), [])

    def test_names_nobody(self):
        for s in ("Traditional", "trad", "Trad.", "Anon", "unknown", "", "  "):
            self.assertEqual(people(s), [], f"{s!r} should name nobody")

    def test_possessive_reference_is_not_an_attribution(self):
        self.assertEqual(people("Johnson's variation of Middleton's"), [])

    def test_complib_composer_is_after_the_LAST_by(self):
        """Seven CompLib titles contain ' by ' themselves.

        The composer is Holland; Whiting wrote the thing that was shortened.
        Splitting on the first ' by ' returns the wrong man for all seven.
        """
        t = "5024 Bristol Surprise Major Op. 5184 shortened by Brian E Whiting by Ian M Holland"
        self.assertEqual(people(t.rsplit(" by ", 1)[1]), ["Ian M Holland"])
        t2 = "240 Death by Chocolate Bob Minor by Ryan J Faulkner-Hatt"
        self.assertEqual(people(t2.rsplit(" by ", 1)[1]), ["Ryan J Faulkner-Hatt"])


class TestKeyAndCompatibility(unittest.TestCase):

    def test_key_is_first_initial_plus_surname(self):
        self.assertEqual(key("Anthony J Cox"), "a-cox")
        self.assertEqual(key("A J Cox"), "a-cox")
        self.assertEqual(key("Donald F Morrison"), "d-morrison")

    def test_key_needs_two_tokens(self):
        for s in ("Elf", "Monument", "BEW", ""):
            self.assertIsNone(key(s), f"{s!r} should have no key")

    def test_compatible_compares_initials_positionally(self):
        self.assertTrue(compatible("A J Cox", "Anthony J Cox"))
        self.assertTrue(compatible("Robin Daw", "Robin A Daw"))   # shorter says less
        self.assertFalse(compatible("Andrew N Tyler", "Albert M Tyler"))
        self.assertFalse(compatible("Raymond H Daw", "Robin A Daw"))


class TestInitialDetection(unittest.TestCase):
    """Both bugs here put correct matches into the error column."""

    def test_bare_and_dotted_initials(self):
        for t in ("J", "J.", "A.J.", "G.A.C.", "DF", "RDS"):
            self.assertTrue(is_initials(t), f"{t!r} is an initial")

    def test_forenames_are_not_initials(self):
        for t in ("Don", "Mike", "Anthony", "Lucy", "Jim"):
            self.assertFalse(is_initials(t), f"{t!r} is a forename")

    def test_edit_distance(self):
        self.assertTrue(edit_distance_le_1("glen", "glenn"))    # insertion
        self.assertTrue(edit_distance_le_1("glenn", "glen"))    # deletion
        self.assertTrue(edit_distance_le_1("gary", "garv"))     # substitution
        self.assertFalse(edit_distance_le_1("stephen", "samuel"))
        self.assertFalse(edit_distance_le_1("george", "graham"))

    def test_edit_distance_does_not_reach_every_variant(self):
        """Deliberately narrow, and the adjudication covers the rest.

        'Lesley'/'Leslie' and 'Stephen'/'Steven' are the same name two edits
        apart; 'Dainel'/'Daniel' is a transposition, which this metric also
        scores as two. None are caught here -- they are labelled by hand in
        data/composer_bridge_adjudication.csv instead. Widening the rule to
        reach them would also reach 'Martin'/'Marvin', which are two people.
        The rule stays narrow and the hard cases get read.
        """
        self.assertFalse(edit_distance_le_1("lesley", "leslie"))
        self.assertFalse(edit_distance_le_1("stephen", "steven"))
        self.assertFalse(edit_distance_le_1("dainel", "daniel"))
        labels = load_adjudication()
        for credit in ("Lesley F Bailey", "Steven J Ivin", "Dainel Brady"):
            self.assertEqual(labels.get(credit), "same", credit)


class TestAdjudication(unittest.TestCase):

    def test_labels_are_committed_and_well_formed(self):
        """The published precision is computed from this file, so it must exist.

        Only two verdicts are allowed: a third spelling would be silently
        counted as 'not different', which is the generous direction.
        """
        labels = load_adjudication()
        self.assertIsNotNone(labels, "data/composer_bridge_adjudication.csv missing")
        self.assertGreater(len(labels), 0)
        self.assertEqual(set(labels.values()), {"same", "different"})


if __name__ == "__main__":
    unittest.main()
