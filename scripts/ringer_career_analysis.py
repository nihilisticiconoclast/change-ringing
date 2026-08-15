#!/usr/bin/env python3
"""Ringer career analysis across the 2012-2024 BellBoard corpus.

Built on the canonical identities in data/ringer_identity_candidates.csv
(Gemini Task 3, resolved across 1,969,949 ringer appearances), NOT on raw
names. A career is the trajectory of one resolved person, so every metric
groups on canonical_ringer_id -- joining the alias "Sue Sawyer" onto the raw
name column would split one person into two careers and undercount everyone
who uses initials part of the time.

Four questions:

  1. Career span. How long is a ringing career, and how is the length
     distributed? (first to last performance year, per resolved ringer.)

  2. Productivity trajectory. Is a ringer's output rising, steady, or
     declining over their career? Classified by comparing the first and last
     thirds of their active years.

  3. Conducting as a career stage. IDEAS.md asked whether conducting
     concentrates in a few people and whether it tracks experience -- i.e. do
     ringers conduct later in their career than they ring? Measured two ways:
     concentration (share of all conducted performances held by the top N),
     and the gap, per ringer, between first-rung and first-conducted year.

  4. Career archetypes. The shape of the population: one-appearance ringers,
     short-lived, steady, and prolific.

Window: 2012-01-01 to 2024-12-31, thirteen complete years -- BellBoard's
near-complete era. A figure stated without a window is one waiting to change
size; the same is true here, and the 2021-24 figures this project carried
before the backfill are the same quantities over four years, not different
ones.

Run against a local replica:

    python scripts/build_local_db.py --out local_corpus.db
    python scripts/ringer_career_analysis.py --local-db local_corpus.db
"""

import argparse
import csv
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
CANDIDATES_CSV = ROOT / "data" / "ringer_identity_candidates.csv"
OUT_CSV = ROOT / "data" / "ringer_career_trajectories.csv"

sys.path.insert(0, str(Path(__file__).parent))
import db  # noqa: E402


def load_identity_map(conn):
    """Create a TEMP table mapping raw_name -> canonical_ringer_id/name.

    TEMP so it does not persist into the replica; the map is derived data that
    belongs in the CSV, not the schema. Returns (rows_loaded, primary_count).
    """
    conn.execute("DROP TABLE IF EXISTS rmap")
    conn.execute(
        'CREATE TEMP TABLE rmap ('
        'raw_name TEXT PRIMARY KEY, cid TEXT NOT NULL, '
        'cname TEXT NOT NULL, is_primary INTEGER NOT NULL)'
    )
    rows = []
    with open(CANDIDATES_CSV, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append((
                r["raw_name"],
                r["canonical_ringer_id"],
                r["canonical_name"],
                1 if r["is_primary"] == "true" else 0,
            ))
    conn.executemany("INSERT OR REPLACE INTO rmap VALUES (?, ?, ?, ?)", rows)
    conn.execute("CREATE INDEX tmp_rmap_name ON rmap(raw_name)")
    loaded = conn.execute("SELECT COUNT(*) FROM rmap").fetchone()[0]
    primary = conn.execute("SELECT COUNT(*) FROM rmap WHERE is_primary=1").fetchone()[0]
    return loaded, primary


def coverage(conn):
    """How many ringer appearances resolve to a canonical identity.

    1,969,949 ringer rows; the identity CSV is built from the same corpus, so
    coverage should be near-total. Anything materially below 100% means the
    CSV is stale relative to the DB and the analysis must say so rather than
    report figures that quietly omit a slice of the population.
    """
    total = conn.execute("SELECT COUNT(*) FROM performance_ringers").fetchone()[0]
    mapped = conn.execute(
        "SELECT COUNT(*) FROM performance_ringers r JOIN rmap m ON m.raw_name=r.name"
    ).fetchone()[0]
    return total, mapped


def per_ringer_careers(conn):
    """One row per canonical ringer: span, appearances, conducting, dates.

    Joins performance_ringers -> performances for the date, -> rmap for the
    canonical id. perf_date is ISO 'YYYY-MM-DD' so substr(,1,4) is the year.
    """
    return conn.execute(
        """
        SELECT m.cid,
               m.cname,
               COUNT(*)                          AS appearances,
               MIN(substr(p.perf_date,1,4))      AS first_year,
               MAX(substr(p.perf_date,1,4))      AS last_year,
               SUM(CASE WHEN r.conductor=1 THEN 1 ELSE 0 END) AS conducted,
               MIN(CASE WHEN r.conductor=1
                        THEN substr(p.perf_date,1,4) END)      AS first_conducted_year
        FROM performance_ringers r
        JOIN performances p ON p.perf_id = r.perf_id
        JOIN rmap m          ON m.raw_name = r.name
        WHERE p.perf_date IS NOT NULL
        GROUP BY m.cid, m.cname
        """
    ).fetchall()


def all_yearly_appearances(conn):
    """All (cid, year, count) rows in one pass, as {cid: {year: count}}.

    Replaces one query per ringer (55k round trips) with a single GROUP BY.
    The per-ringer loop was the bottleneck: each query re-scanned
    performance_ringers joined to rmap. One grouped scan is ~100x faster and
    reads the same indexes (idx_ringer_name, idx_perf_date).
    """
    out = {}
    for cid, yr, n in conn.execute(
        """
        SELECT m.cid, substr(p.perf_date,1,4) AS yr, COUNT(*) AS n
        FROM performance_ringers r
        JOIN performances p ON p.perf_id = r.perf_id
        JOIN rmap m          ON m.raw_name = r.name
        WHERE p.perf_date IS NOT NULL
        GROUP BY m.cid, yr
        """
    ).fetchall():
        out.setdefault(cid, {})[yr] = n
    return out


def classify_trajectory(yearly, first_year, last_year):
    """Rising / steady / declining / brief, from the first vs last third.

    'brief' covers careers too short to split into thirds (<= 2 active years):
    classifying those by slope would manufacture a trend from noise. The
    boundary is on distinct active YEARS, not span, because a ringer active in
    2012 and 2024 has a 13-year span but 2 active years and no third to
    compare.

    Threshold of 10% mirrors the project's existing size-signal work: a change
    smaller than that is within year-to-year noise for a single ringer.
    """
    active_years = sorted(int(y) for y in yearly)
    if len(active_years) <= 2:
        return "brief"
    n = len(active_years)
    first_third = active_years[: max(1, n // 3)]
    last_third = active_years[max(1, n - n // 3):]
    first_rate = sum(yearly[str(y)] for y in first_third) / len(first_third)
    last_rate = sum(yearly[str(y)] for y in last_third) / len(last_third)
    if first_rate == 0:
        return "rising" if last_rate > 0 else "steady"
    change = (last_rate - first_rate) / first_rate
    if change >= 0.10:
        return "rising"
    if change <= -0.10:
        return "declining"
    return "steady"


def archetype(appearances, span_years, conducted):
    """Population shape of a career: one-off / short / steady / prolific.

    Boundaries are stated, not tuned: 1 appearance, <=3 years span, and the
    top decile by appearances. A 'prolific' ringer is in the busiest 10%, not
    an arbitrary round number, so the definition moves with the corpus the
    way the figures do.
    """
    if appearances == 1:
        return "one-appearance"
    if span_years <= 3:
        return "short-lived"
    if conducted and appearances >= 100:
        return "conductor"
    return "steady"


def analyze(conn):
    loaded, primary = load_identity_map(conn)
    total, mapped = coverage(conn)
    rows = per_ringer_careers(conn)
    yearly = all_yearly_appearances(conn)

    # Precompute the appearances threshold for the top decile ('prolific').
    app_sorted = sorted(r[2] for r in rows)
    decile_cut = app_sorted[int(len(app_sorted) * 0.9)] if app_sorted else 0

    careers = []
    for cid, cname, appearances, first_year, last_year, conducted, first_cond in rows:
        span = (int(last_year) - int(first_year) + 1) if first_year else 0
        yearly_r = yearly.get(cid, {})
        traj = classify_trajectory(yearly_r, first_year, last_year)
        conducted = conducted or 0
        cond_share = (conducted / appearances) if appearances else 0.0
        years_to_conducting = (
            (int(first_cond) - int(first_year))
            if first_cond and first_year else None
        )
        arch = archetype(appearances, span, conducted)
        # Reclassify into prolific if in the top decile (overrides steady).
        if appearances >= decile_cut and arch == "steady":
            arch = "prolific"
        careers.append({
            "canonical_ringer_id": cid,
            "canonical_name": cname,
            "appearances": appearances,
            "first_year": first_year or "",
            "last_year": last_year or "",
            "span_years": span,
            "active_years": len(yearly_r),
            "conducted": conducted,
            "conductor_share": round(cond_share, 4),
            "first_conducted_year": first_cond or "",
            "years_to_first_conducting": years_to_conducting if years_to_conducting is not None else "",
            "trajectory": traj,
            "archetype": arch,
        })

    careers.sort(key=lambda c: -c["appearances"])
    return {
        "loaded": loaded,
        "primary": primary,
        "total_appearances": total,
        "mapped_appearances": mapped,
        "careers": careers,
        "decile_cut": decile_cut,
    }


def summarize(res):
    careers = res["careers"]
    n = len(careers)
    spans = [c["span_years"] for c in careers]
    apps = [c["appearances"] for c in careers]
    total_apper = sum(apps)
    total_cond = sum(c["conducted"] for c in careers)

    print("=" * 60)
    print("RINGER CAREER ANALYSIS  (2012-2024)")
    print("=" * 60)
    print(f"Identity CSV loaded:        {res['loaded']:,} raw names "
          f"({res['primary']:,} primary)")
    print(f"Ringer appearances mapped:  {res['mapped_appearances']:,} / "
          f"{res['total_appearances']:,} "
          f"({100*res['mapped_appearances']/res['total_appearances']:.2f}%)")
    print(f"Resolved ringers (careers): {n:,}")
    print(f"Total appearances analysed: {total_apper:,}")
    print(f"Total conducted performances: {total_cond:,}")
    print()

    # 1. Career span distribution.
    print("--- 1. CAREER SPAN (first to last performance year) ---")
    buckets = [(1, 1), (2, 3), (4, 5), (6, 10), (11, 13)]
    for lo, hi in buckets:
        c = sum(1 for s in spans if lo <= s <= hi)
        print(f"  {lo:>2}-{hi:<2} years: {c:>6,}  ({100*c/n:.1f}%)")
    print(f"  median span: {sorted(spans)[n//2]} years")
    one_off = sum(1 for s in spans if s == 1)
    print(f"  single-year careers: {one_off:,} ({100*one_off/n:.1f}%)")
    print()

    # 2. Productivity trajectory.
    print("--- 2. PRODUCTIVITY TRAJECTORY ---")
    from collections import Counter
    traj = Counter(c["trajectory"] for c in careers)
    for t in ("rising", "steady", "declining", "brief"):
        print(f"  {t:<10}: {traj.get(t,0):>6,}  ({100*traj.get(t,0)/n:.1f}%)")
    print()

    # 3. Conducting concentration + career-stage test.
    print("--- 3. CONDUCTING AS A CAREER STAGE ---")
    conductors = [c for c in careers if c["conducted"] > 0]
    cond_apps = sorted((c["conducted"] for c in conductors), reverse=True)
    top10_share = (sum(cond_apps[:10]) / total_cond) if total_cond else 0
    top1pct_n = max(1, len(conductors) // 100)
    top1pct_share = (sum(cond_apps[:top1pct_n]) / total_cond) if total_cond else 0
    print(f"  ringers who ever conducted: {len(conductors):,} / {n:,} "
          f"({100*len(conductors)/n:.1f}%)")
    print(f"  top 10 conductors hold {100*top10_share:.1f}% of all "
          f"conducted performances ({total_cond:,})")
    print(f"  top 1% of conductors ({top1pct_n}) hold {100*top1pct_share:.1f}%")
    # Years to first conducting: does conducting come later in a career?
    gaps = [c["years_to_first_conducting"] for c in conductors
            if c["years_to_first_conducting"] != ""]
    if gaps:
        gaps_s = sorted(gaps)
        med = gaps_s[len(gaps_s)//2]
        pos = sum(1 for g in gaps if g > 0)
        zero = sum(1 for g in gaps if g == 0)
        print(f"  years from first-rung to first-conducted (n={len(gaps):,}):")
        print(f"    median {med}, "
              f"{pos:,} ({100*pos/len(gaps):.1f}%) conducted LATER than "
              f"their first appearance, "
              f"{zero:,} ({100*zero/len(gaps):.1f}%) in their first year")
    print()

    # 4. Career archetypes.
    print("--- 4. CAREER ARCHETYPES ---")
    arch = Counter(c["archetype"] for c in careers)
    for a in ("one-appearance", "short-lived", "steady", "prolific", "conductor"):
        cnt = arch.get(a, 0)
        share_app = (sum(c["appearances"] for c in careers if c["archetype"] == a)
                     / total_apper) if total_apper else 0
        print(f"  {a:<14}: {cnt:>6,} ringers ({100*cnt/n:.1f}%)  "
              f"-> {100*share_app:.1f}% of all appearances")
    print()
    print(f"Prolific decile threshold: >= {res['decile_cut']:,} appearances")
    print("Wrote: " + str(OUT_CSV))


def write_csv(res):
    fields = [
        "canonical_ringer_id", "canonical_name", "appearances", "first_year",
        "last_year", "span_years", "active_years", "conducted",
        "conductor_share", "first_conducted_year", "years_to_first_conducting",
        "trajectory", "archetype",
    ]
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for c in res["careers"]:
            w.writerow({k: c[k] for k in fields})


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    db.add_db_args(p)
    args = p.parse_args()
    conn = db.connect(args)
    try:
        res = analyze(conn)
        write_csv(res)
        summarize(res)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
