#!/usr/bin/env python3
"""
Measure every contentious definition before choosing it (R-52).

    python scripts/measure_definitions.py --local-db data/change-ringing.db

Why this exists, and why it runs before `semantics.py` is written
----------------------------------------------------------------
There is no shared definition of a peal in this repository. `is_peal` is a local
variable inside one function of `analyse_ringing_careers.py`, and 36 scripts
query the database directly, fourteen of them hardcoding 5000. They disagree.

The temptation is to pick the sensible-looking convention and move on. That is
exactly how the current flat threshold got there, and it is how PR #19 came to
publish "72.5% conduct a peal" when the code measured conducting *anything* --
the real figure being 19.8%, with a median wait of 37 performances rather than
11. A definition error, not a code error, and invisible to every check.

So this script does not choose. For each contentious definition it reports **how
many records the choice moves**, so R-53 picks with the cost in front of it and
the published figures can be checked against the convention they actually used.

Every number printed here is a denominator somebody has already published on.
"""
import argparse
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def one(conn, sql, *args):
    return conn.execute(sql, args).fetchone()[0]


def rule(title):
    print(f"\n{'=' * 74}\n{title}\n{'=' * 74}")


def measure_peal_boundary(conn):
    rule("1. What counts as a peal -- the boundary")
    ge = one(conn, "SELECT COUNT(*) FROM performances WHERE changes >= 5000")
    gt = one(conn, "SELECT COUNT(*) FROM performances WHERE changes > 5000")
    eq = one(conn, "SELECT COUNT(*) FROM performances WHERE changes = 5000")
    print(f"  changes >= 5000 : {ge:>8,} peals")
    print(f"  changes >  5000 : {gt:>8,} peals")
    print(f"  exactly 5000    : {eq:>8,}   = {100 * eq / ge:.2f}% of the peal population")
    print("\n  Call sites using '>=': most_rung_methods.sql, peal_and_quarter_populations.sql,")
    print("  rhythm/01_daily_profile.sql, analyse_ringing_careers.py")
    print("  Call site using '>' : queries/findings/conductor_speed_signature.sql")
    print("  -> that query is behind R-24's published between-conductor result, so it")
    print("     sits on a denominator 1.6% smaller than every other published figure.")


def measure_unknown_length(conn):
    rule("2. What counts as a peal -- unknown length")
    total = one(conn, "SELECT COUNT(*) FROM performances")
    nul = one(conn, "SELECT COUNT(*) FROM performances WHERE changes IS NULL")
    print(f"  performances with no `changes` value: {nul:,} of {total:,} "
          f"({100 * nul / total:.1f}%)")
    print("\n  The three conventions in use, and what each does to these rows:")
    print(f"    practice_night_agreement.sql   `changes IS NULL OR changes < 5000`")
    print(f"      -> counts all {nul:,} as NOT a peal, deliberately and explicitly")
    print(f"    SUM(changes >= 5000)           (most_rung_methods, rhythm)")
    print(f"      -> SQLite skips NULL in SUM, so these leave the NUMERATOR silently")
    print(f"         while a COUNT(*) denominator keeps them: a {100 * nul / total:.1f}% deflation")
    print(f"    analyse_ringing_careers.py     `changes not in (None, '')` else False")
    print(f"      -> counts them as not a peal, same as the first")
    # The size of the silent-deflation error, on a real published shape.
    peals = one(conn, "SELECT COUNT(*) FROM performances WHERE changes >= 5000")
    known = one(conn, "SELECT COUNT(*) FROM performances WHERE changes IS NOT NULL")
    print(f"\n  peal share, denominator = all performances     : {100 * peals / total:.2f}%")
    print(f"  peal share, denominator = known length only    : {100 * peals / known:.2f}%")
    print(f"  the choice moves the headline peal share by      {abs(100*peals/total - 100*peals/known):.2f} points")


def measure_stage_rule(conn):
    rule("3. What counts as a peal -- the stage-dependent minimum")
    print("  The CCCBR framework sets 5000 changes on seven or more bells but 5040 on")
    print("  five or six, a peal at those stages being a whole number of extents.")
    window = one(conn, "SELECT COUNT(*) FROM performances "
                       "WHERE changes >= 5000 AND changes < 5040")
    print(f"\n  performances in [5000, 5040): {window:,}  -- this looked like the big one")
    rows = conn.execute("""
        SELECT m.stage, COUNT(*) FROM performances p
        JOIN performance_methods pm ON pm.perf_id = p.perf_id AND pm.ord = 0
        JOIN methods m ON m.method_id = pm.method_id
        WHERE p.changes >= 5000 AND p.changes < 5040 AND m.stage IS NOT NULL
        GROUP BY m.stage ORDER BY 2 DESC""").fetchall()
    resolved = sum(n for _, n in rows)
    low = sum(n for s, n in rows if s in (5, 6))
    print(f"  of which {resolved:,} have a resolved stage:")
    for s, n in rows[:6]:
        print(f"    stage {s:>2}: {n:>6,}")
    print(f"\n  affected by the rule (stage 5 or 6): {low}")
    print("  -> it is not the big one. Encode the rule because it IS the rule and costs")
    print("     one line, but it is not an argument for this work. The first draft of")
    print("     docs/semantic_layer_design.md cited the window as the population at")
    print("     risk, which was wrong and is corrected there.")


def measure_spliced_double_count(conn):
    rule("4. Method counts -- the spliced double-count")
    links = one(conn, "SELECT COUNT(*) FROM performance_methods")
    perfs = one(conn, "SELECT COUNT(DISTINCT perf_id) FROM performance_methods")
    multi = one(conn, "SELECT COUNT(*) FROM (SELECT perf_id FROM performance_methods "
                      "GROUP BY perf_id HAVING COUNT(*) > 1)")
    print(f"  method links           : {links:,}")
    print(f"  performances linked    : {perfs:,}")
    print(f"  linked to >1 method    : {multi:,} ({100 * multi / perfs:.1f}% of linked)")
    print(f"  inflation if you COUNT(*) after joining: {links - perfs:,} extra rows, "
          f"{100 * (links - perfs) / perfs:.1f}%")
    print("\n  So 'performances of method X' summed across methods exceeds the number of")
    print("  performances by that margin. Whether a spliced performance counts once per")
    print("  method or once in total is a definition, and it is currently implicit at")
    print("  every call site.")
    top = conn.execute("""
        SELECT m.title, COUNT(*) FROM performance_methods pm
        JOIN methods m ON m.method_id = pm.method_id
        GROUP BY m.title ORDER BY 2 DESC LIMIT 3""").fetchall()
    print("\n  most-linked methods (these counts include spliced appearances):")
    for t, n in top:
        print(f"    {n:>7,}  {t}")


def measure_ring_type(conn):
    rule("5. What counts as a performance at all")
    total = one(conn, "SELECT COUNT(*) FROM performances")
    for col, label in (("ring_type", "ring_type"),):
        for v, n in conn.execute(f"SELECT {col}, COUNT(*) FROM performances "
                                 f"GROUP BY 1 ORDER BY 2 DESC"):
            print(f"  {label} = {str(v):<8} {n:>8,}  ({100 * n / total:.1f}%)")
    for col in ("portable", "dumb_bells"):
        n = one(conn, f"SELECT COUNT(*) FROM performances WHERE {col} IS NOT NULL "
                      f"AND TRIM(CAST({col} AS TEXT)) NOT IN ('', '0')")
        print(f"  {col:<10} set on    {n:>8,}  ({100 * n / total:.1f}%)")
    hand = one(conn, "SELECT COUNT(*) FROM performances WHERE ring_type = 'hand'")
    print(f"\n  -> a tower-level count that does not exclude handbells is {hand:,} "
          f"({100 * hand / total:.1f}%) too high.")
    print("     Nothing in the repository records whether any given published tower")
    print("     figure excluded them.")


def measure_date_choice(conn):
    """Which date -- and the answer is not the one the column names suggest.

    This started as "perf_date or bb_timestamp?" and turned into a data-quality
    finding. `bb_timestamp` is not when a band submitted a performance; it is when
    BellBoard's own record was created, and BellBoard bulk-imported historical
    performances in batches. So the column carries spikes that are an artefact of
    somebody else's loading, and using it as a submission date is wrong for about
    a fifth of the corpus.
    """
    rule("6. Which date -- and what bb_timestamp actually is")
    total = one(conn, "SELECT COUNT(*) FROM performances")
    print(f"  perf_date    set on {one(conn, 'SELECT COUNT(*) FROM performances WHERE perf_date IS NOT NULL'):,}"
          f"  -- when it was rung")
    print(f"  bb_timestamp set on {one(conn, 'SELECT COUNT(*) FROM performances WHERE bb_timestamp IS NOT NULL'):,}"
          f"  -- NOT when it was submitted; see below")
    print(f"  ingested_at  set on {one(conn, 'SELECT COUNT(*) FROM performances WHERE ingested_at IS NOT NULL'):,}"
          f"  -- when WE loaded it, and correct for that")

    diff = one(conn, """SELECT COUNT(*) FROM performances
        WHERE SUBSTR(perf_date,1,4) <> SUBSTR(bb_timestamp,1,4)""")
    lag = one(conn, """SELECT COUNT(*) FROM performances
        WHERE julianday(bb_timestamp) - julianday(perf_date) > 365""")
    print(f"\n  rung year <> bb_timestamp year : {diff:,} ({100*diff/total:.1f}%)")
    print(f"  bb_timestamp over a year later : {lag:,} ({100*lag/total:.1f}%)")
    print("\n  That is far too much for submission lag, and the daily counts say why:")
    rows = conn.execute("""SELECT SUBSTR(bb_timestamp,1,10) d, COUNT(*) n
        FROM performances GROUP BY 1 ORDER BY n DESC LIMIT 6""").fetchall()
    for d, n in rows:
        print(f"    {d}  {n:>7,}  ({100*n/total:.1f}%)")
    spike = one(conn, """SELECT COUNT(*) FROM performances WHERE SUBSTR(bb_timestamp,1,10) IN
        (SELECT SUBSTR(bb_timestamp,1,10) FROM performances
         GROUP BY 1 HAVING COUNT(*) > 2000)""")
    print(f"\n  rows on a date carrying more than 2,000 performances: {spike:,} "
          f"({100*spike/total:.1f}%)")
    print("  Those dates -- early January 2017, mid-February 2015 -- are not our ingest")
    print("  runs (ours are 2026-08-09 and 2026-08-15, recorded correctly in")
    print("  `ingested_at`). They are BellBoard's OWN historical bulk imports.")
    print("\n  So bb_timestamp is BellBoard's record-creation time, not the band's")
    print("  submission time. Anyone treating it as a submission date is wrong for")
    print(f"  roughly a fifth of the corpus, and anyone ordering by it to get recency")
    print("  gets those two spikes instead. perf_date is the only date that means what")
    print("  it says; `ingested_at` is the only honest provenance column.")


def measure_ringer_tally(conn):
    rule("7. How a ringer's tally is attributed")
    rows = one(conn, "SELECT COUNT(*) FROM performance_ringers")
    perfs = one(conn, "SELECT COUNT(DISTINCT perf_id) FROM performance_ringers")
    # One person ringing two bells in a handbell peal appears twice for one performance.
    dupes = one(conn, """
        SELECT COUNT(*) FROM (
          SELECT perf_id, name FROM performance_ringers
          WHERE name IS NOT NULL AND TRIM(name) <> ''
          GROUP BY perf_id, name HAVING COUNT(*) > 1)""")
    conductors = one(conn, "SELECT COUNT(*) FROM performance_ringers "
                           "WHERE conductor IS NOT NULL AND TRIM(CAST(conductor AS TEXT)) "
                           "NOT IN ('', '0')")
    print(f"  ringer rows                      : {rows:,}")
    print(f"  distinct performances covered    : {perfs:,}")
    print(f"  (performance, name) pairs with >1 row: {dupes:,}")
    print(f"    -> one person on two bells, mostly handbells. 'appearances' counted per")
    print(f"       ROW is that many higher than counted per PERFORMANCE.")
    print(f"  rows flagged conductor           : {conductors:,}")
    print(f"    -> is the conductor counted as a ringer as well? Every call site decides.")
    print("\n  And the deeper caveat: a 'ringer' here is a resolved CLUSTER, not a person.")
    print("  70,032 raw names resolve to 56,340 canonical entities and that resolution's")
    print("  accuracy is UNMEASURED (the open half of R-9). Every per-ringer figure")
    print("  inherits it, and semantics.py should say so rather than let it be forgotten.")


def measure_active_thresholds(conn):
    rule("8. What makes a ringer 'active'")
    print("  analyse_ringing_careers.py uses MIN_APPEARANCES = 50 and MIN_SPAN_YEARS = 5.")
    print("  Defensible and arbitrary, and buried in one script's constants. The cohort")
    print("  size at nearby thresholds, so the sensitivity is visible:\n")
    print("    min appearances   ringers qualifying")
    for t in (10, 25, 50, 100, 200):
        n = one(conn, """
            SELECT COUNT(*) FROM (
              SELECT name FROM performance_ringers
              WHERE name IS NOT NULL AND TRIM(name) <> ''
              GROUP BY name HAVING COUNT(*) >= ?)""", t)
        mark = "   <- the published choice" if t == 50 else ""
        print(f"    {t:>13,}   {n:>17,}{mark}")
    print("\n  -> raw names, not resolved clusters, so these are upper bounds on the")
    print("     number of people. The point is the shape: the cohort roughly halves")
    print("     with each doubling of the threshold, so the choice is load-bearing.")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[1].strip())
    ap.add_argument("--local-db", default="data/change-ringing.db")
    args = ap.parse_args()
    db = Path(args.local_db)
    if not db.exists():
        sys.exit(f"ERROR: no replica at {db}. Build one with "
                 f"scripts/build_local_db.py --out {db}")
    conn = sqlite3.connect(str(db))

    print(__doc__.split("----\n")[1].strip()[:0] or "", end="")
    print("R-52 -- the size of each contentious definition, measured before choosing")

    measure_peal_boundary(conn)
    measure_unknown_length(conn)
    measure_stage_rule(conn)
    measure_spliced_double_count(conn)
    measure_ring_type(conn)
    measure_date_choice(conn)
    measure_ringer_tally(conn)
    measure_active_thresholds(conn)

    print(f"\n{'=' * 74}")
    print("Nothing here chooses. R-53 chooses, with these numbers in front of it.")
    print(f"{'=' * 74}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
