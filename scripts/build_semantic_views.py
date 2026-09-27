#!/usr/bin/env python3
"""
Generate schema/008_init_semantic_views.sql from scripts/semantics.py (R-53).

    python scripts/build_semantic_views.py            # write the file
    python scripts/build_semantic_views.py --check     # fail if it is stale

Why generate rather than hand-write
-----------------------------------
Recorded queries in `queries/` run as SQL with no Python near them, so the rules
have to exist as SQL. Hand-writing them beside the Python predicates is how this
repository ended up with fourteen scattered thresholds and a `>` where five other
call sites had `>=`.

So the SQL is emitted from the same functions the predicates use, the file says
plainly that it is generated, and `--check` fails the build if someone edits it
by hand or changes `semantics.py` without regenerating. That check is wired into
`rebuild_all.py`; without it, "generated" is a comment rather than a fact.
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from semantics import (  # noqa: E402
    PEAL_MIN_CHANGES,
    PEAL_MIN_CHANGES_LOW_STAGE,
    PEAL_HIGH_STAGE,
    QUARTER_MIN_CHANGES,
    TOWER_RING_TYPE,
    sql_is_peal,
    sql_is_quarter_from_peal,
    sql_length_class_from_peal,
)

OUT = ROOT / "schema" / "008_init_semantic_views.sql"


def render():
    peal = sql_is_peal("p.changes", "m.stage")
    return f"""-- 008_init_semantic_views.sql -- the definitions, as SQL (R-53)
--
-- GENERATED from scripts/semantics.py by scripts/build_semantic_views.py.
-- Do NOT edit by hand. The point of this schema is that the rule lives in one
-- place; a hand-edit here recreates exactly the divergence it exists to end.
-- `scripts/build_semantic_views.py --check` fails the build if you do.
--
-- Recorded queries under queries/ cannot import Python, so they read these views
-- and get is_peal, is_quarter and length_class without restating a threshold.
-- tests/test_semantics.py asserts the view and the Python predicates agree on
-- every row of the corpus.
--
-- In force: a peal is {PEAL_MIN_CHANGES} changes on {PEAL_HIGH_STAGE} or more bells and
-- {PEAL_MIN_CHANGES_LOW_STAGE} below that; a quarter is {QUARTER_MIN_CHANGES}.
--
-- All three derived columns are NULL where the answer is genuinely unknown --
-- 22,623 performances, 7.7% -- and NOT false. 21,788 have no length at all; 835
-- sit in [{PEAL_MIN_CHANGES}, {PEAL_MIN_CHANGES_LOW_STAGE}) with no resolved stage, where the answer
-- depends on a stage nobody knows. Treating those as false is the live bug this
-- replaces: SUM(changes >= {PEAL_MIN_CHANGES}) drops them from a numerator while COUNT(*)
-- keeps them in the denominator, worth 1.43 points on the headline peal share.
-- See docs/definitions_measured.md.

DROP VIEW IF EXISTS "v_performance_facts";
DROP VIEW IF EXISTS "v_performance_length";

-- Layer one: the peal rule, computed once.
CREATE VIEW "v_performance_length" AS
SELECT
    p.perf_id,
    p.perf_date,
    p.changes,
    m.stage,
    {peal} AS is_peal
FROM performances p
LEFT JOIN performance_methods pm ON pm.perf_id = p.perf_id AND pm.ord = 0
LEFT JOIN methods m ON m.method_id = pm.method_id;

-- Layer two: everything that derives from it. Split in two because inlining the
-- peal CASE into the quarter and class expressions expands it to six nested
-- copies -- correct, and unreviewable.
CREATE VIEW "v_performance_facts" AS
SELECT
    l.perf_id,
    l.perf_date,
    l.changes,
    l.stage,
    l.is_peal,
    {sql_is_quarter_from_peal("l.is_peal", "l.changes")} AS is_quarter,
    {sql_length_class_from_peal("l.is_peal", "l.changes")} AS length_class,
    p.ring_type,
    (p.ring_type = '{TOWER_RING_TYPE}') AS is_tower,
    p.dove_tower_id,
    p.dove_ring_id,
    p.composer
FROM v_performance_length l
JOIN performances p ON p.perf_id = l.perf_id;
"""


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[1].strip())
    ap.add_argument("--check", action="store_true",
                    help="exit non-zero if the committed file is stale")
    args = ap.parse_args()

    want = render()
    if args.check:
        if not OUT.exists():
            sys.exit(f"ERROR: {OUT.relative_to(ROOT)} is missing. Run "
                     f"scripts/build_semantic_views.py")
        if OUT.read_text(encoding="utf-8") != want:
            sys.exit(
                f"ERROR: {OUT.relative_to(ROOT)} does not match what "
                f"scripts/semantics.py generates.\n"
                f"  Either semantics.py changed and the schema was not "
                f"regenerated, or the schema was edited by hand.\n"
                f"  Both leave two definitions of the same rule, which is what "
                f"this module exists to prevent.\n"
                f"  Fix: python scripts/build_semantic_views.py")
        print(f"  ok    {OUT.relative_to(ROOT)} matches scripts/semantics.py")
        return 0

    OUT.write_text(want, encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)} ({len(want.splitlines())} lines) "
          f"from scripts/semantics.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
