#!/usr/bin/env python3
"""
Build the Two Populations page -- roadmap item 23.

    python scripts/build_populations_page.py --local-db data/change-ringing.db

Writes docs/populations.html from scripts/templates/populations.html, one
self-contained file with no external requests. Reads a local SQLite/libSQL file,
never Turso.

The page publishes a NEGATIVE result, which is unusual enough to say why it is
worth a page. Ringers describe two worlds -- the Sunday band and the peal circuit
-- as different people sharing buildings. The corpus says otherwise, and the
shape of the distribution is the whole argument: two populations would show two
humps, and there is one. That is a thing to look at rather than a number to
quote, which is what makes it a page instead of a paragraph.

The full account, including everything the corpus cannot see, is in
docs/two_populations.md. The numbers here come from the same code path as
scripts/analyse_peal_populations.py.
"""
import argparse
import collections
import csv
import json
import sqlite3
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from site_chrome import apply_chrome  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "scripts" / "templates" / "populations.html"
CANDIDATES = ROOT / "data" / "ringer_identity_candidates.csv"
OUT = ROOT / "docs" / "populations.html"

PEAL = 5000
MIN_APPEARANCES = 50


def bands(fractions):
    """Ten deciles of peal share. 100% lands in the top band, not an 11th."""
    h = collections.Counter(min(int(v * 10), 9) for v in fractions)
    return [h[b] for b in range(10)]


def collect(conn):
    with CANDIDATES.open(encoding="utf-8") as f:
        ids = {r["raw_name"]: r["canonical_ringer_id"] for r in csv.DictReader(f)}

    canon_p, canon_s = collections.Counter(), collections.Counter()
    raw_p, raw_s = collections.Counter(), collections.Counter()
    for name, changes in conn.execute(
        "SELECT TRIM(r.name), p.changes FROM performance_ringers r "
        "JOIN performances p ON p.perf_id = r.perf_id "
        "WHERE r.name IS NOT NULL AND p.changes IS NOT NULL"
    ):
        try:
            peal = int(changes) >= PEAL
        except (ValueError, TypeError):
            continue
        (raw_p if peal else raw_s)[name] += 1
        cid = ids.get(name)
        if cid:
            (canon_p if peal else canon_s)[cid] += 1

    def shares(pc, sc):
        return [pc[k] / (pc[k] + sc[k]) for k in set(pc) | set(sc)
                if pc[k] + sc[k] >= MIN_APPEARANCES]

    canon = shares(canon_p, canon_s)
    raw = shares(raw_p, raw_s)

    # Activity ladder: how the no-peal share falls as you demand more ringing.
    ladder = []
    everyone = set(canon_p) | set(canon_s)
    for thresh in (1, 10, 25, 50, 100, 250):
        n = none = allp = 0
        for cid in everyone:
            tot = canon_p[cid] + canon_s[cid]
            if tot < thresh:
                continue
            n += 1
            if canon_p[cid] == 0:
                none += 1
            elif canon_s[cid] == 0:
                allp += 1
        if n:
            ladder.append({"threshold": thresh, "ringers": n,
                           "no_peals_pct": round(100 * none / n, 1),
                           "all_peals_pct": round(100 * allp / n, 1)})

    towers = [p / (p + s) for _t, p, s in conn.execute(
        "SELECT dove_tower_id, SUM(CASE WHEN changes >= ? THEN 1 ELSE 0 END), "
        "SUM(CASE WHEN changes < ? THEN 1 ELSE 0 END) FROM performances "
        "WHERE dove_tower_id IS NOT NULL AND changes IS NOT NULL AND ring_type = 'tower' "
        "GROUP BY 1 HAVING COUNT(*) >= 50", (PEAL, PEAL))]

    # Experience: does peal share climb with years ringing?
    span = {}
    for name, lo, hi in conn.execute(
        "SELECT TRIM(r.name), MIN(p.perf_date), MAX(p.perf_date) "
        "FROM performance_ringers r JOIN performances p ON p.perf_id = r.perf_id "
        "WHERE r.name IS NOT NULL AND p.perf_date IS NOT NULL GROUP BY 1"
    ):
        cid = ids.get(name)
        if cid and lo and hi:
            span[cid] = max(span.get(cid, 0), int(hi[:4]) - int(lo[:4]))
    by_years = collections.defaultdict(list)
    for cid in everyone:
        tot = canon_p[cid] + canon_s[cid]
        if tot >= MIN_APPEARANCES and cid in span:
            by_years[span[cid]].append(canon_p[cid] / tot)
    experience = [
        {"years": y, "ringers": len(v),
         "mean_pct": round(100 * statistics.mean(v), 1),
         "ever_pct": round(100 * sum(1 for x in v if x > 0) / len(v), 1),
         "corpus_width": y >= 12}
        for y, v in sorted(by_years.items()) if len(v) >= 30
    ]

    lengths = {}
    for lo, hi, key in ((0, 999, "under1000"), (1000, 1399, "quarters"),
                        (1400, 4999, "middling"), (5000, 999999, "peals")):
        lengths[key] = conn.execute(
            "SELECT COUNT(*) FROM performances WHERE changes BETWEEN ? AND ?", (lo, hi)
        ).fetchone()[0]

    return {
        "canonical": bands(canon), "raw": bands(raw),
        "canonicalN": len(canon), "rawN": len(raw),
        "medianPct": round(100 * statistics.median(canon), 1),
        "everRangPct": round(100 - ladder[[l["threshold"] for l in ladder].index(50)]["no_peals_pct"], 1),
        "ladder": ladder,
        "towers": bands(towers), "towersN": len(towers),
        "towerMedianPct": round(100 * statistics.median(towers), 1),
        "experience": experience,
        "lengths": lengths,
        "entities": len(set(ids.values())), "rawNames": len(ids),
        "pealThreshold": PEAL, "minAppearances": MIN_APPEARANCES,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--local-db", default=str(ROOT / "data" / "change-ringing.db"))
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()

    conn = sqlite3.connect(args.local_db)
    data = collect(conn)
    conn.close()

    html = TEMPLATE.read_text(encoding="utf-8")
    if "/*__DATA__*/" not in html:
        sys.exit(f"ERROR: {TEMPLATE} has no /*__DATA__*/ placeholder")
    html = apply_chrome(html.replace("/*__DATA__*/", json.dumps(data, separators=(",", ":"))))
    Path(args.out).write_text(html, encoding="utf-8")

    print(f"Wrote {args.out}  ({len(html)/1024:.0f} KB)")
    print(f"  {data['canonicalN']:,} ringers with {MIN_APPEARANCES}+ appearances; "
          f"median peal share {data['medianPct']}%")
    print(f"  lowest band holds {data['canonical'][0]:,} of them "
          f"({100*data['canonical'][0]/data['canonicalN']:.0f}%)")
    print(f"  {data['towersN']:,} towers, median {data['towerMedianPct']}%")
    return 0


if __name__ == "__main__":
    sys.exit(main())
