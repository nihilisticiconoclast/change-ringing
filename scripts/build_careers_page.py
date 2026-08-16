#!/usr/bin/env python3
"""
Build docs/careers.html -- the ringing-career page. Roadmap item 22, Vibe Task 7.

    python scripts/build_careers_page.py --local-db data/change-ringing.db

Every figure on the page is computed by importing `analyse_ringing_careers`
rather than by restating its output. That module is what `docs/ringing_careers.md`
was written from, so the page and the document cannot drift apart: there is one
implementation of "the cohort", one of "normalised bell position", and one of
"appearances before a first conducted performance".

That mattered here. The prose in the merged submission described the
apprenticeship figure as conducting a PEAL when the code measured conducting
anything, and the corpus is mostly quarters -- 72.5% against 20.0%, a median
wait of 11 appearances against 37. A page that restated the prose would have
carried the error onto the site; a page that calls the function cannot.
"""
import argparse
import json
import statistics
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from analyse_ringing_careers import (  # noqa: E402
    ATTRITION_LINE, MIN_APPEARANCES, MIN_SPAN_YEARS,
    build_careers, canonical_map, cohort, percentile,
    q1_apprenticeship, q2_progression, q3_attrition,
)
from site_chrome import apply_chrome  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = Path(__file__).parent / "templates" / "careers.html"
OUT = ROOT / "docs" / "careers.html"

# Drift bins for (late-career position - early-career position). Symmetric about
# zero on purpose: the whole claim is about whether the mass sits to the right of
# it, so the chart must be able to show that it does not.
DRIFT_EDGES = [-0.6, -0.45, -0.3, -0.2, -0.1, -0.05, 0.05, 0.1, 0.2, 0.3, 0.45, 0.6]
CURVE_MAX = 120          # appearances plotted on the conducting curve


def bin_counts(values, edges):
    """Counts in (-inf, e0], (e0, e1], ..., (elast, +inf) -- ends absorb the tails."""
    counts = [0] * (len(edges) + 1)
    for v in values:
        placed = False
        for i, e in enumerate(edges):
            if v <= e:
                counts[i] += 1
                placed = True
                break
        if not placed:
            counts[-1] += 1
    return counts


def deciles(values):
    """Ten bins over [0, 1]; anything at exactly 1.0 lands in the last."""
    counts = [0] * 10
    for v in values:
        counts[min(9, int(v * 10))] += 1
    return counts


def conducting_curve(careers, cohort_ids, peals_only):
    """Cumulative share of the cohort who have conducted by their Nth appearance."""
    _, firsts = q1_apprenticeship(careers, cohort_ids, peals_only=peals_only)
    n = len(cohort_ids)
    firsts_sorted = sorted(firsts)
    curve, j = [], 0
    for k in range(CURVE_MAX + 1):
        while j < len(firsts_sorted) and firsts_sorted[j] <= k:
            j += 1
        curve.append(round(100.0 * j / n, 2))
    return curve


def apprenticeship_rows(careers, cohort_ids):
    rows = []
    for label, peals_only in (("Any performance", False),
                              ("A peal (≥5,000 changes)", True)):
        ever, firsts = q1_apprenticeship(careers, cohort_ids, peals_only=peals_only)
        fs = sorted(firsts)
        rows.append({
            "label": label,
            "ever": ever,
            "pct": round(100.0 * ever / len(cohort_ids), 1),
            "median": int(statistics.median(firsts)),
            "mean": round(statistics.mean(firsts)),
            "p25": percentile(fs, 25),
            "p75": percentile(fs, 75),
        })
    return rows


def attrition_rows(conn, ids, cohort_ids):
    """Two cohort tables: everybody, and the 50+ active cohort.

    Years after ATTRITION_LINE are omitted rather than shown as 0% -- a ringer
    first seen in 2022 cannot have stopped appearing before 2020, so the zero is
    a definition, not a measurement, and printing it invites the reader to
    average it in.
    """
    appearances, first_year, last_year = q3_attrition(conn, ids)
    active = set(cohort_ids)
    out = {"all": [], "active": []}
    for key, members in (("all", None), ("active", active)):
        for y in range(2012, ATTRITION_LINE + 1):
            group = [c for c in first_year
                     if first_year[c] == y and (members is None or c in members)]
            if not group:
                continue
            gone = sum(1 for c in group if last_year[c] <= ATTRITION_LINE)
            out[key].append({"year": y, "n": len(group), "gone": gone,
                             "pct": round(100.0 * gone / len(group), 1)})
    return out


def collect(db_path):
    conn = sqlite3.connect(db_path)
    ids = canonical_map()
    careers, unmapped = build_careers(conn, ids)
    cohort_ids = cohort(careers)
    (early, late, up, down, stay, ranges, single_late) = q2_progression(careers, cohort_ids)

    n = len(cohort_ids)
    drift = [l - e for e, l in zip(early, late)]
    bell_rows = conn.execute(
        "SELECT COUNT(*) FROM performance_ringers "
        "WHERE bell IS NOT NULL AND TRIM(bell) != ''").fetchone()[0]

    data = {
        "cohort": n,
        "tracedRingers": len(careers),
        "unmapped": unmapped,
        "bellRows": bell_rows,
        "minAppearances": MIN_APPEARANCES,
        "minSpanYears": MIN_SPAN_YEARS,
        "attritionLine": ATTRITION_LINE,
        "earlyMean": round(statistics.mean(early), 3),
        "lateMean": round(statistics.mean(late), 3),
        "drift": round(statistics.mean(late) - statistics.mean(early), 3),
        "up": up, "down": down, "stayed": stay,
        "upPct": round(100.0 * up / n, 1),
        "downPct": round(100.0 * down / n, 1),
        "stayedPct": round(100.0 * stay / n, 1),
        "medianRange": round(statistics.median(ranges), 3),
        "singleBellLate": single_late,
        "singleBellLatePct": round(100.0 * single_late / n, 1),
        "driftEdges": DRIFT_EDGES,
        "driftCounts": bin_counts(drift, DRIFT_EDGES),
        "rangeDeciles": deciles(ranges),
        "curveAny": conducting_curve(careers, cohort_ids, False),
        "curvePeal": conducting_curve(careers, cohort_ids, True),
        "curveMax": CURVE_MAX,
        "apprenticeship": apprenticeship_rows(careers, cohort_ids),
        "attrition": attrition_rows(conn, ids, cohort_ids),
    }
    conn.close()
    return data


def build(db_path, out_path):
    html = TEMPLATE.read_text(encoding="utf-8")
    if "/*__DATA__*/" not in html:
        sys.exit(f"ERROR: {TEMPLATE} has no /*__DATA__*/ placeholder")
    data = collect(db_path)
    html = html.replace("/*__DATA__*/", json.dumps(data, separators=(",", ":")))
    out_path.write_text(apply_chrome(html), encoding="utf-8")
    print(f"Wrote {out_path}  ({out_path.stat().st_size / 1024:.0f} KB)")
    print(f"  cohort {data['cohort']:,}; early {data['earlyMean']}, late {data['lateMean']}, "
          f"drift {data['drift']}")
    for r in data["apprenticeship"]:
        print(f"  conduct {r['label']:26s} {r['pct']:>5}%  median wait {r['median']}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--local-db", default=str(ROOT / "data" / "change-ringing.db"))
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()
    build(args.local_db, Path(args.out))


if __name__ == "__main__":
    main()
