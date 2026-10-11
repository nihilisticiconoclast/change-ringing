"""Tests for the dashboard dataset builder (scripts/build_dashboard_data.py).

The builder makes one substitution into semantics.py -- the stage for lengths in
[5000, 5040) is read from BellBoard's method name, not from the resolved CCCBR
method -- and it reads the figures the docs state by pattern rather than holding
them as constants. Both are pinned here on fixed strings, so a regression shows
without the 150 MB corpus, and on a bare Python as CI runs it.
"""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from build_dashboard_data import (  # noqa: E402
    find_claim,
    parse_hypotheses,
    parse_roadmap,
    parse_stages,
    stage_for_rule,
    stage_group,
    words_to_int,
)
from semantics import length_class  # noqa: E402


class TestStageFromName(unittest.TestCase):
    """The stage is the last word, unless the name ends by naming two."""

    def test_last_word_is_the_stage(self):
        self.assertEqual(parse_stages("Cambridge Surprise Minor"), [6])
        self.assertEqual(parse_stages("Grandsire Triples"), [7])
        self.assertEqual(parse_stages("Bristol Surprise Maximus"), [12])

    def test_trailing_counts_in_brackets_are_ignored(self):
        self.assertEqual(parse_stages("Spliced Surprise Major (8m)"), [8])
        self.assertEqual(parse_stages("Spliced Surprise Major (4 Methods)"), [8])
        self.assertEqual(parse_stages("Spliced Cinques and Maximus (2m/p)"), [11, 12])

    def test_two_stages_named_at_the_end(self):
        self.assertEqual(parse_stages("Doubles and Minor"), [5, 6])
        self.assertEqual(parse_stages("Plain Bob Doubles and Minor"), [5, 6])

    def test_a_stage_word_inside_the_name_is_not_a_second_stage(self):
        # "Royal" belongs to the method's name; the stage is still the last word.
        self.assertEqual(parse_stages("Royal Wedding Surprise Major"), [8])

    def test_non_methods_name_no_stage(self):
        self.assertEqual(parse_stages("Tolling"), [])
        self.assertEqual(parse_stages("Rounds and Call Changes"), [])
        self.assertEqual(parse_stages(""), [])

    def test_stage_groups(self):
        self.assertEqual(stage_group(None, [6]), "Minor")
        self.assertEqual(stage_group(None, [14]), "13+ bells")
        self.assertEqual(stage_group(None, [5, 6]), "Mixed stages")
        self.assertEqual(stage_group(None, []), "Stage not named")
        self.assertEqual(stage_group("tolling", []), "Non-method ringing")


class TestStageSubstitution(unittest.TestCase):
    """The stage changes the answer only in [5000, 5040), and only when resolved."""

    def test_outside_the_window_no_stage_is_passed(self):
        self.assertEqual(stage_for_rule(5040, True, [6]), (None, None))
        self.assertEqual(stage_for_rule(1260, True, [5]), (None, None))
        self.assertEqual(stage_for_rule(None, True, [8]), (None, None))

    def test_unresolved_in_the_window_stays_unknown(self):
        # v_performance_length has no stage for these, so NULL -- not a guess.
        stage, problem = stage_for_rule(5000, False, [8])
        self.assertIsNone(stage)
        self.assertIsNone(problem)
        self.assertIsNone(length_class(5000, stage))

    def test_resolved_in_the_window_is_decided_by_the_stage(self):
        stage, _ = stage_for_rule(5024, True, [8])
        self.assertEqual(length_class(5024, stage), "peal")
        stage, _ = stage_for_rule(5000, True, [6])
        self.assertEqual(length_class(5000, stage), "quarter")

    def test_cases_that_could_disagree_with_the_views_are_flagged(self):
        self.assertIsNotNone(stage_for_rule(5000, True, [])[1])
        self.assertIsNotNone(stage_for_rule(5000, True, [6, 8])[1])
        # Two stages on the same side of seven cannot change the answer.
        self.assertIsNone(stage_for_rule(5000, True, [11, 12])[1])


class TestDocClaims(unittest.TestCase):
    """A stated figure is read from the sentence that states it, words or digits."""

    def test_number_words(self):
        self.assertEqual(words_to_int("Thirteen"), 13)
        self.assertEqual(words_to_int("twenty-three"), 23)
        self.assertEqual(words_to_int("Twenty-four"), 24)
        self.assertEqual(words_to_int("293,471"), 293471)
        self.assertIsNone(words_to_int("several"))

    def test_a_claim_that_wraps_across_lines(self):
        text = "intro\n**Three of\ntwenty-three predictions held intact.** More."
        pattern = r"\*\*(\w+) of\s+([\w-]+) predictions held intact"
        value, line, quote = find_claim(text, pattern, 1)
        self.assertEqual((value, line), (3, 2))
        self.assertEqual(quote, "Three of twenty-three predictions held intact")
        self.assertEqual(find_claim(text, pattern, 2)[0], 23)

    def test_a_reworded_claim_is_not_found_rather_than_an_error(self):
        self.assertEqual(find_claim("Fourteen pages now.", r"\*\*(\w+) pages\*\*"), (None, None, None))

    def test_a_decimal_stays_a_decimal(self):
        self.assertEqual(find_claim("**95.6% of the 186,464 method rows**", r"\*\*([\d.]+)% of the")[0], 95.6)


class TestRegisters(unittest.TestCase):
    """Roadmap state comes from the section a row sits in; one verdict per entry."""

    def test_roadmap_state_type_and_owner(self):
        text = "\n".join([
            "## Now",
            "| # | Item | Owner | State |",
            "| --- | --- | --- | --- |",
            "| R-50 | **TEST** — nothing catches a stale page | **Claude Code** | Live |",
            "### Done",
            "| # | Item | Owner | Where it landed |",
            "| --- | --- | --- | --- |",
            "| R-1 | Backfill gate | Vibe | **Merged** |",
            "| R-28 | One access path | **Vibe** | **Superseded by R-45** |",
            "## Held",
            "| # | Item | Why held |",
            "| --- | --- | --- |",
            "| R-11 | Acoustic Landscape | Needs a review |",
        ])
        problems = []
        rows = {r["id"]: r for r in parse_roadmap(text, problems)}
        self.assertEqual(problems, [])
        self.assertEqual((rows["R-50"]["state"], rows["R-50"]["type"], rows["R-50"]["owner"]),
                         ("Open", "Test", "Claude Code"))
        self.assertEqual(rows["R-1"]["state"], "Done")
        self.assertEqual(rows["R-28"]["state"], "Superseded")
        self.assertEqual((rows["R-11"]["state"], rows["R-11"]["owner"]), ("Held", None))

    def test_one_verdict_per_hypothesis(self):
        text = ("## About the data\n\n### H1. A claim\n**Expected:** x\n**❌ Wrong** — because.\n\n"
                "### H2. Another\n**✅ Held**\n")
        problems = []
        rows = parse_hypotheses(text, problems)
        self.assertEqual([(r["id"], r["verdict"], r["section"]) for r in rows],
                         [("H1", "Wrong", "Data"), ("H2", "Held", "Data")])
        self.assertEqual(problems, [])

    def test_two_verdicts_under_one_entry_is_a_problem(self):
        problems = []
        parse_hypotheses("## About the data\n### H1. A claim\n**❌ Wrong** then **✅ Held**\n", problems)
        self.assertEqual(len(problems), 1)


if __name__ == "__main__":
    unittest.main()
