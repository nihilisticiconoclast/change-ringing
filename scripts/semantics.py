#!/usr/bin/env python3
"""
The definitions. One place, and the only place.

    from semantics import is_peal, SQL_IS_PEAL, PEAL_MIN_CHANGES

Why this module exists
----------------------
Before it, there was no shared definition of a peal in this repository.
`is_peal` was a local variable inside one function of
`analyse_ringing_careers.py`, and 36 scripts queried the database directly,
fourteen of them hardcoding 5000. They disagreed: five call sites used
`>= 5000` and `queries/findings/conductor_speed_signature.sql` used `> 5000`,
which is 848 performances -- 1.62% of the peal population -- and that query is
behind R-24's published result.

This class of error has cost a published figure here already. PR #19 reported
"72.5% conduct a peal" when the code measured conducting *anything*; the real
figure is 19.8%, with a median wait of 37 performances rather than 11. A
definition error, not a code error, and invisible to every check in the
repository. A number cannot be wrong in that way if there is nowhere to write
it down twice.

Every choice below was measured before it was made. `docs/definitions_measured.md`
gives the record count each one moves; `scripts/measure_definitions.py`
reproduces them.

Python and SQL, and why both
----------------------------
Callers are split: 36 scripts in Python, and recorded queries in
`queries/` that must run as SQL with no Python anywhere near them. So each rule
appears twice, as a predicate and as a SQL fragment.

That is two definitions unless something binds them, so two things do. The
**constants are shared** -- the SQL fragments are built from the same names, so a
threshold cannot drift numerically. And `tests/test_semantics.py` runs both
against **every row of the corpus** and asserts they agree, which catches a
structural divergence the shared constants cannot. That test is the real
deliverable of this module; without it this file is a suggestion.

The tri-state, which is the part worth reading
----------------------------------------------
`is_peal` returns `None`, not `False`, when the answer is unknown. 22,623
performances (7.7%) are unknown, and a boolean would silently call all of them
quarters -- which is exactly the failure already present in
`SUM(changes >= 5000)`, where SQLite drops NULL from the numerator while a
`COUNT(*)` denominator keeps it, moving the headline peal share by 1.43 points.

Two ways to be unknown, and the second falls out of the rule rather than being
bolted on:

  * `changes` is NULL -- 21,788 performances.
  * `changes` is in [5000, 5040) and the stage is unknown -- 835 performances.
    The CCCBR framework requires 5000 changes on seven or more bells but 5040 on
    five or six, so inside that window the answer genuinely depends on the stage.
    Outside it, it does not: 5040 and above is a peal at any stage, below 5000 is
    a peal at none. The two thresholds bracket the ambiguity exactly.

In SQL the tri-state is free, because NULL already means this.
"""

# --- lengths -----------------------------------------------------------------

#: Minimum changes for a peal on seven or more bells.
PEAL_MIN_CHANGES = 5000
#: Minimum changes for a peal on five or six bells -- a whole number of extents.
#: Also the length at or above which a performance is a peal at ANY stage.
PEAL_MIN_CHANGES_LOW_STAGE = 5040
#: The stage at and above which PEAL_MIN_CHANGES applies.
PEAL_HIGH_STAGE = 7
#: Minimum changes for a quarter peal.
QUARTER_MIN_CHANGES = 1250

# --- cohort ------------------------------------------------------------------

#: Appearances before a ringer counts as "active". Arbitrary and load-bearing:
#: the cohort is 18,764 at 10, 6,902 at 50, 4,194 at 100 -- roughly halving with
#: each doubling. Kept at the published value so existing figures do not move for
#: no reason; named here so the sensitivity is visible rather than buried.
MIN_APPEARANCES = 50
#: Years between first and last appearance before a ringer counts as "active".
MIN_SPAN_YEARS = 5

# --- which records count -----------------------------------------------------

#: Ring types in the corpus: 263,417 tower (89.8%) and 30,054 hand (10.2%).
#: A tower-level count that does not exclude handbells is 10.2% too high.
TOWER_RING_TYPE = "tower"
HAND_RING_TYPE = "hand"

#: The only date column that means what its name says. `bb_timestamp` is
#: BellBoard's RECORD-CREATION time, not the band's submission time: 57,295 rows
#: (19.5%) sit on dates carrying more than 2,000 performances, which are
#: BellBoard's own historical bulk imports in January 2017 and February 2015, not
#: real submission days. `ingested_at` is when WE loaded it and is correct for
#: that. Do not use bb_timestamp for recency or for "submitted in year N".
PERFORMANCE_DATE_COLUMN = "perf_date"
PROVENANCE_DATE_COLUMN = "ingested_at"
UNRELIABLE_DATE_COLUMN = "bb_timestamp"


# --- predicates --------------------------------------------------------------

def is_peal(changes, stage=None):
    """Is this performance a peal? True, False, or None when unknowable.

    `stage` may be omitted, and usually can be: it only changes the answer for
    lengths in [5000, 5040), which is 7,001 performances, of which 5 are at a
    stage where it matters.
    """
    if changes is None or changes == "":
        return None
    changes = int(changes)
    if changes >= PEAL_MIN_CHANGES_LOW_STAGE:
        return True                      # long enough at any stage
    if changes < PEAL_MIN_CHANGES:
        return False                     # too short at any stage
    if stage is None or stage == "":     # inside the window, and it depends
        return None
    return int(stage) >= PEAL_HIGH_STAGE


def is_quarter(changes, stage=None):
    """Is this a quarter peal -- at least 1250 changes and not a peal?

    Returns None when `is_peal` cannot decide, because "not a peal" is not
    knowable then either.
    """
    if changes is None or changes == "":
        return None
    peal = is_peal(changes, stage)
    if peal is None:
        return None
    return (not peal) and int(changes) >= QUARTER_MIN_CHANGES


def length_class(changes, stage=None):
    """'peal' | 'quarter' | 'short' | None."""
    if is_peal(changes, stage) is None:
        return None
    if is_peal(changes, stage):
        return "peal"
    return "quarter" if is_quarter(changes, stage) else "short"


# --- the same rules, as SQL --------------------------------------------------
#
# Built from the constants above so a threshold cannot drift between the two,
# and asserted row-for-row against the predicates by tests/test_semantics.py.
#
# `c` and `s` are the changes and stage expressions the caller wants tested, so
# these compose against a join or a subquery rather than assuming column names.

def sql_is_peal(c="changes", s="stage"):
    """SQL yielding 1, 0 or NULL, matching is_peal() exactly."""
    return (
        f"CASE WHEN {c} IS NULL THEN NULL"
        f" WHEN {c} >= {PEAL_MIN_CHANGES_LOW_STAGE} THEN 1"
        f" WHEN {c} < {PEAL_MIN_CHANGES} THEN 0"
        f" WHEN {s} IS NULL THEN NULL"
        f" ELSE ({s} >= {PEAL_HIGH_STAGE}) END"
    )


def sql_is_quarter(c="changes", s="stage"):
    """SQL yielding 1, 0 or NULL, matching is_quarter() exactly."""
    return (
        f"CASE WHEN {c} IS NULL THEN NULL"
        f" WHEN ({sql_is_peal(c, s)}) IS NULL THEN NULL"
        f" WHEN ({sql_is_peal(c, s)}) = 1 THEN 0"
        f" ELSE ({c} >= {QUARTER_MIN_CHANGES}) END"
    )


def sql_length_class(c="changes", s="stage"):
    """SQL yielding 'peal', 'quarter', 'short' or NULL."""
    return (
        f"CASE WHEN ({sql_is_peal(c, s)}) IS NULL THEN NULL"
        f" WHEN ({sql_is_peal(c, s)}) = 1 THEN 'peal'"
        f" WHEN ({sql_is_quarter(c, s)}) = 1 THEN 'quarter'"
        f" ELSE 'short' END"
    )


# Composed forms, for when `is_peal` has already been computed as a column.
#
# Inlining sql_is_peal() inside sql_is_quarter() and again inside
# sql_length_class() is correct but expands exponentially: the length_class
# expression alone came out as six nested copies of the peal CASE, which is
# unreadable and unreviewable. A view computes is_peal once and these read it.

def sql_is_quarter_from_peal(peal="is_peal", c="changes"):
    """is_quarter, given an already-computed is_peal column."""
    return (
        f"CASE WHEN {peal} IS NULL THEN NULL"
        f" WHEN {peal} = 1 THEN 0"
        f" ELSE ({c} >= {QUARTER_MIN_CHANGES}) END"
    )


def sql_length_class_from_peal(peal="is_peal", c="changes"):
    """length_class, given an already-computed is_peal column."""
    return (
        f"CASE WHEN {peal} IS NULL THEN NULL"
        f" WHEN {peal} = 1 THEN 'peal'"
        f" WHEN {c} >= {QUARTER_MIN_CHANGES} THEN 'quarter'"
        f" ELSE 'short' END"
    )


#: Convenience forms for the common case: querying `performances` joined to
#: `methods` through `performance_methods`, where the columns are named plainly.
SQL_IS_PEAL = sql_is_peal()
SQL_IS_QUARTER = sql_is_quarter()
SQL_LENGTH_CLASS = sql_length_class()


# --- the two method measures -------------------------------------------------
#
# Not one measure with a caveat. 379,180 method links sit on 228,479
# performances, so counting rows after joining through performance_methods
# overstates by 150,701 -- 66.0% -- because a spliced peal is one performance and
# eight or more methods. Both counts are legitimate and they answer different
# questions, so both are named. An unnamed count is the bug.

#: How many PERFORMANCES included this method, spliced or not. Counts a spliced
#: peal once however many methods it contains.
SQL_PERFORMANCES_OF_METHOD = "COUNT(DISTINCT pm.perf_id)"

#: How many times this method APPEARED, counting each method in a spliced peal
#: separately. Sums across methods to more than the number of performances, by
#: design.
SQL_METHOD_APPEARANCES = "COUNT(*)"


# --- how a ringer's tally is attributed --------------------------------------
#
# Per performance, not per row: 3,414 (performance, name) pairs carry more than
# one row, one person ringing two bells, mostly handbells. Counting rows makes
# those people look busier than they were. The conductor IS counted as a ringer,
# because they rang.
#
# The caveat that outlives the choice: a "ringer" here is a resolved CLUSTER, not
# a person. 70,032 raw names resolve to 56,340 canonical entities and that
# resolution's accuracy is UNMEASURED -- the open half of R-9. Every per-ringer
# figure inherits it. Say so wherever one is published.

SQL_RINGER_APPEARANCES = "COUNT(DISTINCT pr.perf_id)"

RINGER_RESOLUTION_CAVEAT = (
    "Ringers are resolved name clusters, not verified people: 70,032 raw names "
    "resolve to 56,340 canonical entities and the resolution's accuracy is not "
    "yet measured (R-9)."
)
