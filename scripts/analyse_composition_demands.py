#!/usr/bin/env python3
"""
Statistical and structural analysis of change ringing compositions (Roadmap Item R-40 / G-11).

Examines what 86,054 compositions in CompLib demand of a band and conductor:
- Calling positions, call types (bobs, singles, plains, extremes)
- Call volume and density distributions (peals, quarters, touches)
- Part structures, symmetry, and memorisation burden
- Call burstiness (consecutive call clusters vs isolated calls)
- Tenor fixation and band work distribution
- Single-method vs spliced composition complexity

Usage:
    python scripts/analyse_composition_demands.py --local-db local_corpus.db
"""

import argparse
import json
import os
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

# Add scripts directory to path for imports
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import db


def parse_calling_string(calling_str: str):
    """
    Parses a CompLib calling string into structured part count, call list, and totals.
    
    Handles:
    - Unicode dashes: en-dash, em-dash, minus
    - Macro definitions and invocations: @A(...) and @A
    - Outer part repeats: N(...)
    - Inner call repeats: 2(-W), 3(-H)
    - Part variations: +2[...], -2|4[...]
    - Lead markers: :1, :22
    """
    if not calling_str:
        return 1, [], 0

    s = calling_str.replace("\u2013", "-").replace("\u2014", "-").replace("\u2212", "-")

    # 1. Extract macros @A(...)
    macros = {}
    while True:
        s_new = re.sub(
            r"@([A-Za-z0-9_]+)\(([^()]+)\)",
            lambda m: macros.setdefault(m.group(1), m.group(2)) and "",
            s
        )
        if s_new == s:
            break
        s = s_new

    # 2. Expand macro invocations @A
    for _ in range(5):
        expanded = False
        for name, body in list(macros.items()):
            pat = r"@" + name + r"\b"
            if re.search(pat, s):
                s = re.sub(pat, " " + body + " ", s)
                expanded = True
        if not expanded:
            break

    # 3. Outer part repeats: e.g. 3( ... ) or 5( ... )
    part_count = 1
    m_outer = re.match(r"^\s*(\d+)\((.*)\)\s*$", s, re.DOTALL)
    if m_outer:
        part_count = int(m_outer.group(1))
        part_body = m_outer.group(2)
    else:
        part_body = s

    # 4. Inner repeats: e.g. 2(-W) -> -W -W, 3(-H) -> -H -H -H
    for _ in range(5):
        s_prev = part_body
        part_body = re.sub(
            r"(\d+)\(([^()]+)\)",
            lambda m: " ".join([m.group(2)] * int(m.group(1))),
            part_body
        )
        if part_body == s_prev:
            break

    # 5. Clean part variations like +2[sH sH] or -2|4[-M]
    part_body = re.sub(r"[+\-]\d+(\|\d+)*\[[^\]]*\]", " ", part_body)
    part_body = re.sub(r":\d+", " ", part_body)

    tokens = part_body.split()
    calls = []
    for tok in tokens:
        tok = tok.strip("(),;")
        if not tok:
            continue
        call_type = "bob"
        pos = tok
        if tok.startswith("-") or tok.startswith("b"):
            call_type = "bob"
            pos = tok[1:]
        elif tok.startswith("s") or tok.startswith("S"):
            call_type = "single"
            pos = tok[1:]
        elif tok.startswith("p") or tok.startswith("P"):
            call_type = "plain"
            pos = tok[1:]
        elif tok.startswith("x") or tok.startswith("X"):
            call_type = "extreme"
            pos = tok[1:]
        else:
            call_type = "bob"
            pos = tok

        if pos:
            calls.append((call_type, pos.upper()))

    total_calls = len(calls) * part_count
    return part_count, calls, total_calls


def analyze_corpus(conn):
    """Runs complete analytical pipeline across all compositions."""
    cur = conn.cursor()

    # 1. Total compositions and stages
    cur.execute("""
        SELECT composition_id, stage, length, calling, partheads, coursehead_masks, date_composed
        FROM compositions
    """)
    rows = cur.fetchall()
    total_compositions = len(rows)

    stage_counts = Counter()
    length_cats = Counter()
    date_populated_count = 0
    calling_populated_count = 0

    # Calling and part analysis
    part_distribution_all = Counter()
    part_distribution_major_peals = Counter()
    calling_positions = Counter()
    call_types = Counter()
    has_singles_by_stage = Counter()
    total_by_stage = Counter()
    major_peal_calls = []
    # A call happens at a lead, and a Major lead is at minimum 16 changes (plain
    # methods; treble-dodging leads are 32). So length/16 is the largest number
    # of calls that can physically exist, and anything above it is a parse
    # failure rather than a busy composition. Kept separate rather than dropped,
    # so the count of failures is reportable: the published maximum was 2,576
    # calls in a peal with at most 322 leads, which nothing flagged.
    believable_calls = []
    quarter_peal_calls = []
    burst_clusters = Counter()
    fixed_tenor_by_stage = Counter()

    for cid, stage, length, calling, partheads, masks, date_comp in rows:
        stage_counts[stage] += 1
        total_by_stage[stage] += 1

        if date_comp:
            date_populated_count += 1

        if length:
            if length < 1000:
                length_cats["touch (<1,000)"] += 1
            elif 1000 <= length < 2000:
                length_cats["quarter peal (1,000-1,999)"] += 1
            elif 2000 <= length < 5000:
                length_cats["half peal (2,000-4,999)"] += 1
            elif 5000 <= length <= 5400:
                length_cats["standard peal (5,000-5,400)"] += 1
            elif 5400 < length < 10000:
                length_cats["long peal (5,401-9,999)"] += 1
            else:
                length_cats["record / long length (10,000+)"] += 1

        # Tenor fixation check
        if masks:
            mask_list = masks.split("|")
            is_fixed = False
            if stage == 6 and all(m.endswith("6") for m in mask_list):
                is_fixed = True
            elif stage == 7 and all(m.endswith("7") for m in mask_list):
                is_fixed = True
            elif stage == 8 and all(m.endswith("8") for m in mask_list):
                is_fixed = True
            elif stage == 10 and all(m.endswith("0") for m in mask_list):
                is_fixed = True
            elif stage == 12 and all(m.endswith(("2", "T", "t")) for m in mask_list):
                is_fixed = True
            if is_fixed:
                fixed_tenor_by_stage[stage] += 1

        if calling and calling.strip():
            calling_populated_count += 1
            p_count, calls, tot_calls = parse_calling_string(calling)
            part_distribution_all[p_count] += 1

            comp_types = set(c[0] for c in calls)
            if "single" in comp_types:
                has_singles_by_stage[stage] += 1

            for ctype, pos in calls:
                call_types[ctype] += p_count
                calling_positions[pos] += p_count

            # Measure consecutive call bursts in calling string
            s_clean = calling.replace("\u2013", "-").replace("\u2014", "-").replace("\u2212", "-")
            inners = re.findall(r"(\d+)\(([-sbp]?[A-Za-z0-9]+)\)", s_clean)
            for cnt_str, _ in inners:
                cnt = int(cnt_str)
                if cnt > 1:
                    burst_clusters[cnt] += 1

            if stage == 8 and length and 5000 <= length <= 5300:
                part_distribution_major_peals[p_count] += 1
                major_peal_calls.append(tot_calls)
                if tot_calls <= length / 16:
                    believable_calls.append(tot_calls)
            elif stage == 8 and length and 1250 <= length <= 1350:
                quarter_peal_calls.append(tot_calls)

    # Spliced analysis
    cur.execute("""
        SELECT c.stage, COUNT(DISTINCT c.composition_id) as total,
               COUNT(DISTINCT CASE WHEN cm_counts.num_m > 1 THEN c.composition_id END) as spliced
        FROM compositions c
        JOIN (
            SELECT composition_id, COUNT(*) as num_m
            FROM composition_methods
            GROUP BY composition_id
        ) cm_counts ON cm_counts.composition_id = c.composition_id
        WHERE c.stage IN (6, 7, 8, 10, 12)
        GROUP BY c.stage
    """)
    spliced_by_stage = {}
    for stage, tot, spl in cur.fetchall():
        spliced_by_stage[stage] = {
            "total": tot,
            "spliced": spl,
            "pct": round(spl / tot * 100.0, 1)
        }

    # Summary dictionary
    results = {
        "total_compositions": total_compositions,
        "calling_populated_count": calling_populated_count,
        "calling_populated_pct": round(calling_populated_count / total_compositions * 100.0, 2),
        "date_populated_count": date_populated_count,
        "date_populated_pct": round(date_populated_count / total_compositions * 100.0, 2),
        "stage_distribution": dict(stage_counts.most_common()),
        "length_categories": dict(length_cats.most_common()),
        "major_peal_parts": dict(part_distribution_major_peals.most_common(10)),
        "major_peal_stats": {
            "count": len(major_peal_calls),
            "mean_calls": round(statistics.mean(major_peal_calls), 1) if major_peal_calls else 0,
            "median_calls": round(statistics.median(major_peal_calls), 1) if major_peal_calls else 0,
            "p25": round(statistics.quantiles(major_peal_calls, n=4)[0], 1) if len(major_peal_calls) >= 4 else 0,
            "p75": round(statistics.quantiles(major_peal_calls, n=4)[2], 1) if len(major_peal_calls) >= 4 else 0,
            "min_calls": min(major_peal_calls) if major_peal_calls else 0,
            "max_calls": max(believable_calls) if believable_calls else 0,
            "unparseable": len(major_peal_calls) - len(believable_calls),
        },
        "quarter_peal_stats": {
            "count": len(quarter_peal_calls),
            "mean_calls": round(statistics.mean(quarter_peal_calls), 1) if quarter_peal_calls else 0,
            "median_calls": round(statistics.median(quarter_peal_calls), 1) if quarter_peal_calls else 0,
        },
        "top_calling_positions": [
            {"position": pos, "count": cnt, "pct": round(cnt / sum(calling_positions.values()) * 100.0, 1)}
            for pos, cnt in calling_positions.most_common(12)
        ],
        "call_types": [
            {"type": ct, "count": cnt, "pct": round(cnt / sum(call_types.values()) * 100.0, 1)}
            for ct, cnt in call_types.most_common()
        ],
        "singles_vs_bobs": {
            s: {
                "total": total_by_stage[s],
                "singles_count": has_singles_by_stage[s],
                "singles_pct": round(has_singles_by_stage[s] / total_by_stage[s] * 100.0, 1),
                "bob_only_pct": round((total_by_stage[s] - has_singles_by_stage[s]) / total_by_stage[s] * 100.0, 1)
            }
            for s in [6, 7, 8, 10, 12]
        },
        "tenor_fixed": {
            s: {
                "total": total_by_stage[s],
                "fixed_count": fixed_tenor_by_stage[s],
                "fixed_pct": round(fixed_tenor_by_stage[s] / total_by_stage[s] * 100.0, 1)
            }
            for s in [6, 7, 8, 10, 12]
        },
        "spliced_by_stage": spliced_by_stage,
        "consecutive_bursts": dict(sorted(burst_clusters.items()))
    }
    return results


def main():
    parser = argparse.ArgumentParser(description="Analyze composition demands across CompLib corpus")
    db.add_db_args(parser)
    parser.add_argument("--json", action="store_true", help="Output raw JSON summary")
    args = parser.parse_args()

    conn = db.connect(args)
    results = analyze_corpus(conn)
    conn.close()

    if args.json:
        print(json.dumps(results, indent=2))
        return

    print("=" * 70)
    print("COMPOSITION CALLING & BAND DEMANDS ANALYSIS (R-40 / G-11)")
    print("=" * 70)
    print(f"Total compositions: {results['total_compositions']:,}")
    print(f"With calling:       {results['calling_populated_count']:,} ({results['calling_populated_pct']}%)")
    print(f"With date composed: {results['date_populated_count']:,} ({results['date_populated_pct']}%) [Caveat: mostly missing!]")
    print()

    print("--- 1. Major Peals (5,000 - 5,300 changes, n = {:,}) ---".format(results['major_peal_stats']['count']))
    print(f"  Mean calls:   {results['major_peal_stats']['mean_calls']}")
    print(f"  Median calls: {results['major_peal_stats']['median_calls']} (IQR: {results['major_peal_stats']['p25']} - {results['major_peal_stats']['p75']})")
    print(f"  Min / Max:    {results['major_peal_stats']['min_calls']} / {results['major_peal_stats']['max_calls']}")
    print()
    print("  Part structure in Major Peals:")
    for p, c in results['major_peal_parts'].items():
        pct = round(c / results['major_peal_stats']['count'] * 100.0, 1)
        print(f"    {p:>2}-part: {c:>6,} ({pct:>5.1f}%)")
    print()

    print("--- 2. Top Calling Positions (Total occurrences across all 86k) ---")
    for row in results['top_calling_positions']:
        print(f"  {row['position']:>4}: {row['count']:>9,} ({row['pct']:>5.1f}%)")
    print()

    print("--- 3. Single vs Bob-Only Share by Stage ---")
    for s, data in results['singles_vs_bobs'].items():
        print(f"  Stage {s:>2}: {data['singles_count']:>6,} / {data['total']:>6,} ({data['singles_pct']:>5.1f}%) contain singles (bob-only: {data['bob_only_pct']:>5.1f}%)")
    print()

    print("--- 4. Tenor Fixed at Home Share by Stage ---")
    for s, data in results['tenor_fixed'].items():
        print(f"  Stage {s:>2}: {data['fixed_count']:>6,} / {data['total']:>6,} ({data['fixed_pct']:>5.1f}%) tenor fixed")
    print()

    print("--- 5. Spliced Rate by Stage ---")
    for s, data in results['spliced_by_stage'].items():
        print(f"  Stage {s:>2}: {data['spliced']:>6,} / {data['total']:>6,} ({data['pct']:>5.1f}%) spliced")
    print()

    print("--- 6. Consecutive Call Bursts in Calling Sequences ---")
    for cnt, occ in results['consecutive_bursts'].items():
        print(f"  {cnt} calls in a row: {occ:>6,} occurrences")
    print("=" * 70)


if __name__ == "__main__":
    main()
