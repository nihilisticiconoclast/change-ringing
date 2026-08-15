#!/usr/bin/env python3
"""
A ringing career, from the bell people stand behind. Mistral Vibe Task 7.

    python scripts/analyse_ringing_careers.py --local-db local_corpus.db

Traces three things about a ringer's arc -- apprenticeship, bell progression,
and attrition -- against resolved canonical identities. Identity lives in
data/ringer_identity_candidates.csv (a candidate dataset, accuracy unmeasured),
which is why this is a script and not a query: the resolution is not in a table.
The database-only approximation, which groups raw names, is
queries/findings/ringing_careers.sql.

`performance_ringers.bell` is populated on 1,897,741 rows and nothing else in
this project reads it. Every ringer knows the supposed progression -- learn on
the treble, move to the inside bells, tenor and conducting come later -- and
nobody has watched it happen to real people at scale. The finding below is that
the progression is not what ringers believe: ringers move around the whole ring
over a career but they do not graduate up the bells, and most who conduct do so
early. Attrition is published as a cohort rate, never as a statement about an
individual.
"""
import argparse
import collections
import csv
import sqlite3
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CANDIDATES = ROOT / "data" / "ringer_identity_candidates.csv"

MIN_APPEARANCES = 50   # below this an individual arc is mostly noise
MIN_SPAN_YEARS = 5     # "spanning five or more years" -- enough to trace an arc
ATTRITION_LINE = 2020  # an appearance after this year means the ringer is still active
EARLY_LATE_FRACTION = 0.10   # first/last tenth of a career, for the progression test


def canonical_map():
    """raw name -> canonical ringer id."""
    with CANDIDATES.open(encoding="utf-8") as f:
        return {r["raw_name"]: r["canonical_ringer_id"] for r in csv.DictReader(f)}


def percentile(sorted_vals, pct):
    """Nearest-rank percentile; pct in [0, 100]."""
    if not sorted_vals:
        return None
    k = max(0, min(len(sorted_vals) - 1, int(round(pct / 100.0 * (len(sorted_vals) - 1)))))
    return sorted_vals[k]


def build_careers(conn, ids):
    """Per canonical id, a list of (date, bell_int, n_bells_in_ring, conductor).

    Tower performances only, single bells only. `bell` holds single bells ('1',
    '11') and handbell pairs ('1-2', up to '1-2-...-14'); the pairs are a
    different activity and are excluded. Bell number alone is not comparable
    across towers -- the tenor of a six is the 6, of a twelve the 12 -- so each
    appearance carries the number of bells rung in that performance as the
    normaliser (the count of single-bell rows for that perf is the ring size).
    """
    # Number of bells rung per performance = ring size, counted from the
    # single-bell rows of that performance. A tower peal on eight has eight
    # ringers each on one bell, so the count is eight.
    ring_size = {}
    for perf_id, n in conn.execute(
        "SELECT perf_id, COUNT(*) FROM performance_ringers "
        "WHERE bell IS NOT NULL AND TRIM(bell) != '' AND bell NOT LIKE '%-%' "
        "GROUP BY perf_id"
    ):
        ring_size[perf_id] = n

    careers = collections.defaultdict(list)
    unmapped = 0
    for name, date, bell, conductor, perf_id in conn.execute(
        "SELECT TRIM(r.name), p.perf_date, r.bell, r.conductor, r.perf_id "
        "FROM performance_ringers r JOIN performances p ON p.perf_id = r.perf_id "
        "WHERE r.name IS NOT NULL AND TRIM(r.name) != '' "
        "AND p.perf_date GLOB '[0-9][0-9][0-9][0-9]*' AND p.ring_type = 'tower' "
        "AND r.bell IS NOT NULL AND TRIM(r.bell) != '' AND r.bell NOT LIKE '%-%'"
    ):
        cid = ids.get(name)
        if cid is None:
            unmapped += 1
            continue
        n = ring_size.get(perf_id)
        if not n:
            continue
        try:
            b = int(bell)
        except ValueError:
            continue
        if b < 1 or b > n:        # a bell outside the ring is a parse artefact
            continue
        careers[cid].append((date, b, n, conductor))
    return careers, unmapped


def cohort(careers):
    """Canonical ids with >= MIN_APPEARANCES tower appearances spanning >= MIN_SPAN_YEARS."""
    out = []
    for cid, apps in careers.items():
        if len(apps) < MIN_APPEARANCES:
            continue
        years = [int(a[0][:4]) for a in apps]
        if max(years) - min(years) >= MIN_SPAN_YEARS:
            out.append(cid)
    return out


def q1_apprenticeship(careers, cohort_ids):
    """Appearances before a first conducted peal."""
    first_conduct_at = []
    ever_conducted = 0
    for cid in cohort_ids:
        ordered = sorted(careers[cid], key=lambda a: a[0])
        for i, app in enumerate(ordered):
            if app[3] == 1:        # conductor flag
                first_conduct_at.append(i)
                ever_conducted += 1
                break
    return ever_conducted, first_conduct_at


def q2_progression(careers, cohort_ids):
    """Does the bell position move up the ring over a career?

    Normalised position = bell / ring_size, in (0, 1]: the treble is ~1/n (small)
    and the tenor is 1.0. For each ringer, compare the mean normalised position
    of their first EARLY_LATE_FRACTION of appearances against their last.
    """
    early_pos, late_pos = [], []
    moved_up = stayed = moved_down = 0
    late_single_bell = 0
    within_ranges = []
    for cid in cohort_ids:
        ordered = sorted(careers[cid], key=lambda a: a[0])
        n = len(ordered)
        k = max(1, n // int(1 / EARLY_LATE_FRACTION))
        early = ordered[:k]
        late = ordered[-k:]
        e = [a[1] / a[2] for a in early]
        l = [a[1] / a[2] for a in late]
        em, lm = statistics.mean(e), statistics.mean(l)
        early_pos.append(em)
        late_pos.append(lm)
        diff = lm - em
        if diff > 0.05:
            moved_up += 1
        elif diff < -0.05:
            moved_down += 1
        else:
            stayed += 1
        all_pos = [a[1] / a[2] for a in ordered]
        within_ranges.append(max(all_pos) - min(all_pos))
        if len({a[1] for a in late}) == 1:
            late_single_bell += 1
    return (early_pos, late_pos, moved_up, moved_down, stayed,
            within_ranges, late_single_bell)


def q3_attrition(conn, ids):
    """Cohort attrition: of ringers first seen in year Y, the share with no
    appearance after ATTRITION_LINE. Uses every appearance (tower and hand):
    'leaving' is about any reported ringing, not tower ringing only.
    """
    appearances = collections.Counter()
    first_year, last_year = {}, {}
    for name, date in conn.execute(
        "SELECT TRIM(r.name), p.perf_date FROM performance_ringers r "
        "JOIN performances p ON p.perf_id = r.perf_id "
        "WHERE r.name IS NOT NULL AND TRIM(r.name) != '' "
        "AND p.perf_date GLOB '[0-9][0-9][0-9][0-9]*'"
    ):
        cid = ids.get(name)
        if cid is None:
            continue
        y = int(date[:4])
        appearances[cid] += 1
        if cid not in first_year or y < first_year[cid]:
            first_year[cid] = y
        if cid not in last_year or y > last_year[cid]:
            last_year[cid] = y
    return appearances, first_year, last_year


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--local-db", default=str(ROOT / "data" / "change-ringing.db"))
    args = ap.parse_args()
    conn = sqlite3.connect(args.local_db)

    ids = canonical_map()
    print(f"identity: {len(ids):,} raw names -> {len(set(ids.values())):,} canonical entities")
    print("  (candidate dataset, accuracy unmeasured -- see docs/ringer_identity_resolution.md)\n")

    bell_rows = conn.execute(
        "SELECT COUNT(*) FROM performance_ringers WHERE bell IS NOT NULL AND TRIM(bell) != ''"
    ).fetchone()[0]
    print(f"performance_ringers.bell is populated on {bell_rows:,} rows; nothing else reads it.\n")

    careers, unmapped = build_careers(conn, ids)
    cohort_ids = cohort(careers)
    print(f"{len(careers):,} canonical ringers with a dated, single-bell tower appearance "
          f"({unmapped:,} rows unmapped to a canonical id)")
    print(f"cohort: {len(cohort_ids):,} ringers with >= {MIN_APPEARANCES} appearances "
          f"spanning >= {MIN_SPAN_YEARS} years\n")

    # ---- Q1 ----
    ever, firsts = q1_apprenticeship(careers, cohort_ids)
    fs = sorted(firsts)
    print("1. HOW LONG IS THE APPRENTICESHIP? appearances before a first conducted peal")
    print(f"   {ever:,} of {len(cohort_ids):,} cohort ringers ({100*ever/len(cohort_ids):.1f}%) "
          f"ever conduct a peal in this corpus")
    print(f"   among those who do, appearances before the first conducted peal:")
    print(f"     median {statistics.median(firsts):.0f}, mean {statistics.mean(firsts):.1f}, "
          f"p25 {percentile(fs,25)}, p75 {percentile(fs,75)}")
    print("   Skewed: the mean is pulled up by ringers who conduct late or never, against a\n"
          "   short median. Most who conduct do so within their first dozen appearances.\n")

    # ---- Q2 ----
    (early, late, up, down, stay, ranges, single_late) = q2_progression(careers, cohort_ids)
    print("2. IS THE PROGRESSION REAL? normalised bell position (bell / ring size), first vs last tenth")
    print(f"   mean normalised position: early-career {statistics.mean(early):.3f}, "
          f"late-career {statistics.mean(late):.3f}")
    n = len(cohort_ids)
    print(f"   ringers moving up the ring (late - early > 0.05):  {up:>5} ({100*up/n:.1f}%)")
    print(f"   ringers moving down                               :  {down:>5} ({100*down/n:.1f}%)")
    print(f"   ringers in essentially the same place (|diff|<=0.05): {stay:>5} ({100*stay/n:.1f}%)")
    print(f"   median within-ringer range of bell position: {statistics.median(ranges):.3f}")
    print(f"   ringers whose last tenth is a single bell: {single_late} ({100*single_late/n:.1f}%)")
    print("   The folk model is wrong in both directions. Ringers do not graduate up the bells --\n"
          "   early and late career sit at the same mean position -- but neither do they find a\n"
          "   bell and stay on it: the median ringer rings across nearly the whole ring over a\n"
          "   career. They move around without moving up.\n")

    # ---- Q3 ----
    appearances, first_year, last_year = q3_attrition(conn, ids)
    print(f"3. WHAT DOES LEAVING LOOK LIKE? cohort attrition (no appearance after {ATTRITION_LINE})")
    print("   An absence is an absence, not a death or a resignation -- see the doc.")
    print(f"   {'first seen':>10} {'ringers':>8} {'none after '+str(ATTRITION_LINE):>20} {'% gone':>8}")
    for y in range(2012, 2025):
        c = [cid for cid in first_year if first_year[cid] == y and appearances[cid] >= 1]
        if not c:
            continue
        gone = sum(1 for cid in c if last_year[cid] <= ATTRITION_LINE)
        print(f"   {y:>10} {len(c):>8} {gone:>20} {100*gone/len(c):>7.1f}%")
    print(f"\n   {'first seen':>10} {'>=50 app':>8} {'none after '+str(ATTRITION_LINE):>20} {'% gone':>8}")
    for y in range(2012, 2025):
        c = [cid for cid in first_year if first_year[cid] == y and appearances[cid] >= MIN_APPEARANCES]
        if not c:
            continue
        gone = sum(1 for cid in c if last_year[cid] <= ATTRITION_LINE)
        print(f"   {y:>10} {len(c):>8} {gone:>20} {100*gone/len(c):>7.1f}%")
    print("\n   The 2020 line crosses the COVID discontinuity, when ringing stopped almost\n"
          "   entirely for a year, so the 2013-2020 cohorts are partly a pandemic effect.\n"
          "   Cohorts first seen after 2020 cannot by construction have left before 2020.\n"
          "   Active ringers (50+ appearances) attrite far less than the field.")

    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
