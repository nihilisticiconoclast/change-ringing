#!/usr/bin/env python3
"""
Are quarter ringers and peal ringers two populations? Roadmap item 23.

    python scripts/analyse_peal_populations.py --local-db data/change-ringing.db

Prints the four measurements behind docs/two_populations.md. Reads the recorded
SQL from queries/findings/ where it can, and resolves identities through
data/ringer_identity_candidates.csv, which is why this is a script and not a
query: the resolution lives in a CSV rather than a table.

The claim under test is the folk model -- that the Sunday band and the peal
circuit are different people sharing buildings. It is not supported. The
distribution of peal involvement is a single steep decay, not two humps, and the
same is true of towers. See the doc for the full account.
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
PEAL = 5000          # changes; the conventional peal minimum on most stages
MIN_APPEARANCES = 50  # below this, a ringer's peal share is mostly noise


def canonical_map():
    """raw name -> canonical ringer id."""
    with CANDIDATES.open(encoding="utf-8") as f:
        return {r["raw_name"]: r["canonical_ringer_id"] for r in csv.DictReader(f)}


def histogram(fractions, width=46):
    hist = collections.Counter(min(int(v * 10), 9) for v in fractions)
    top = max(hist.values()) if hist else 1
    for b in range(10):
        print(f"    {b*10:>3}-{b*10+9:<3}% peals {hist[b]:>6,}  "
              f"{'#' * int(width * hist[b] / top)}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--local-db", default=str(ROOT / "data" / "change-ringing.db"))
    args = ap.parse_args()
    conn = sqlite3.connect(args.local_db)

    ids = canonical_map()
    print(f"identity: {len(ids):,} raw names -> {len(set(ids.values())):,} canonical entities")
    print("  (candidate dataset, accuracy unmeasured -- see docs/footnote_occasions.md "
          "for why that phrase is used carefully here)\n")

    peals, shorts = collections.Counter(), collections.Counter()
    unmapped = 0
    for name, changes in conn.execute(
        "SELECT TRIM(r.name), p.changes FROM performance_ringers r "
        "JOIN performances p ON p.perf_id = r.perf_id "
        "WHERE r.name IS NOT NULL AND p.changes IS NOT NULL"
    ):
        cid = ids.get(name)
        if cid is None:
            unmapped += 1
            continue
        (peals if changes >= PEAL else shorts)[cid] += 1
    everyone = set(peals) | set(shorts)
    print(f"{len(everyone):,} canonical ringers with a dated, length-bearing performance "
          f"({unmapped:,} rows unmapped)\n")

    print(f"1. PEAL SHARE PER RINGER, by activity threshold")
    print(f"   {'min appearances':>16} {'ringers':>8}   {'no peals':>9} {'some':>7} {'all peals':>10}")
    for thresh in (1, 10, 25, 50, 100, 250):
        n = none = allp = 0
        for cid in everyone:
            tot = peals[cid] + shorts[cid]
            if tot < thresh:
                continue
            n += 1
            if peals[cid] == 0:
                none += 1
            elif shorts[cid] == 0:
                allp += 1
        if n:
            print(f"   {thresh:>16} {n:>8,}   {100*none/n:>8.1f}% "
                  f"{100*(n-none-allp)/n:>6.1f}% {100*allp/n:>9.1f}%")

    active = [(peals[c] / (peals[c] + shorts[c]))
              for c in everyone if peals[c] + shorts[c] >= MIN_APPEARANCES]
    print(f"\n2. IS IT BIMODAL? ringers with >= {MIN_APPEARANCES} appearances")
    histogram(active)
    print(f"    n = {len(active):,}, median peal share {statistics.median(active)*100:.1f}%")
    print("    One mode with a long thin tail. Two populations would show two humps.")

    print("\n3. THE SAME QUESTION FOR TOWERS")
    tvals = []
    for _tid, p, s in conn.execute(
        "SELECT dove_tower_id, "
        "SUM(CASE WHEN changes >= ? THEN 1 ELSE 0 END), "
        "SUM(CASE WHEN changes <  ? THEN 1 ELSE 0 END) "
        "FROM performances WHERE dove_tower_id IS NOT NULL AND changes IS NOT NULL "
        "AND ring_type = 'tower' GROUP BY 1 HAVING COUNT(*) >= 50", (PEAL, PEAL)
    ):
        tvals.append(p / (p + s))
    histogram(tvals)
    print(f"    n = {len(tvals):,} towers, median peal share {statistics.median(tvals)*100:.1f}%")
    print("    Same shape. There is no peal-tower / quarter-tower split either.")

    print("\n4. DOES PEAL INVOLVEMENT GROW WITH EXPERIENCE?")
    span = {}
    for name, lo, hi in conn.execute(
        "SELECT TRIM(r.name), MIN(p.perf_date), MAX(p.perf_date) "
        "FROM performance_ringers r JOIN performances p ON p.perf_id = r.perf_id "
        "WHERE r.name IS NOT NULL AND p.perf_date IS NOT NULL GROUP BY 1"
    ):
        cid = ids.get(name)
        if cid and lo and hi:
            yrs = int(hi[:4]) - int(lo[:4])
            span[cid] = max(span.get(cid, 0), yrs)
    by = collections.defaultdict(list)
    for cid in everyone:
        tot = peals[cid] + shorts[cid]
        if tot >= MIN_APPEARANCES and cid in span:
            by[span[cid]].append(peals[cid] / tot)
    print(f"   {'years active':>13} {'ringers':>8} {'mean peal share':>16} {'ever rang a peal':>18}")
    for yrs in sorted(by):
        v = by[yrs]
        if len(v) < 30:
            continue
        note = "  <- corpus width; means 'present throughout'" if yrs >= 12 else ""
        print(f"   {yrs:>13} {len(v):>8,} {statistics.mean(v)*100:>15.1f}% "
              f"{100*sum(1 for x in v if x > 0)/len(v):>17.1f}%{note}")
    print("    Flat. Peal involvement does not climb with years ringing, so the")
    print("    'graduation to peals' reading is not supported either.")

    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
