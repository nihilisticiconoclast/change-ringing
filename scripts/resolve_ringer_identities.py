#!/usr/bin/env python3
"""
Ringer Identity Resolution Engine for Change Ringing Corpus (Gemini Task 3).

Resolves naming variations, initials, and diminutives across 355,550 ringer performance
records (51,126 peals) using multi-signal orthographic matching and band co-occurrence networks.

Outputs:
    data/ringer_identity_candidates.csv
    docs/ringer_identity_resolution.md

Usage:
    python scripts/resolve_ringer_identities.py --db data/change-ringing.db --out data/ringer_identity_candidates.csv
"""
import argparse
import collections
import csv
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
DEFAULT_DB = ROOT / "data" / "change-ringing.db"
DEFAULT_OUT = ROOT / "data" / "ringer_identity_candidates.csv"

# ----------------------------------------------------------------------
# 1. Hagiographical and English Diminutives Mapping
# ----------------------------------------------------------------------
DIMINUTIVES = {
    "bob": "robert", "rob": "robert", "robin": "robert", "bobby": "robert",
    "bill": "william", "billy": "william", "will": "william", "willie": "william", "liam": "william",
    "jim": "james", "jimmy": "james", "jamie": "james",
    "dave": "david", "davy": "david",
    "mike": "michael", "mick": "michael", "mickey": "michael",
    "chris": "christopher",
    "andy": "andrew", "drew": "andrew",
    "tom": "thomas", "tommy": "thomas",
    "dan": "daniel", "danny": "daniel",
    "dick": "richard", "rich": "richard", "rick": "richard", "ricky": "richard",
    "pete": "peter",
    "steve": "stephen", "steven": "stephen",
    "phil": "philip", "phillip": "philip",
    "tony": "anthony",
    "ken": "kenneth", "kenny": "kenneth",
    "geoff": "geoffrey", "jeff": "geoffrey",
    "ed": "edward", "eddie": "edward", "ted": "edward", "teddy": "edward",
    "alex": "alexander", "alec": "alexander",
    "matt": "matthew", "mat": "matthew",
    "sam": "samuel", "sammy": "samuel",
    "ben": "benjamin", "benny": "benjamin",
    "joe": "joseph", "joey": "joseph",
    "charlie": "charles", "charley": "charles", "chas": "charles",
    "fred": "frederick", "freddie": "frederick",
    "arthur": "arthur", "art": "arthur",
    "sue": "susan", "susie": "susan", "su": "susan", "suzy": "susan",
    "liz": "elizabeth", "beth": "elizabeth", "betty": "elizabeth", "lizzie": "elizabeth", "eliza": "elizabeth",
    "jenny": "jennifer", "jen": "jennifer",
    "kate": "katherine", "katie": "katherine", "cathy": "katherine", "kathy": "katherine", "cath": "katherine",
    "maggie": "margaret", "meg": "margaret", "peggy": "margaret",
    "nicky": "nicola", "nicki": "nicola",
    "nick": "nicholas",
    "becky": "rebecca", "becca": "rebecca",
    "jo": "joanna",
    "ali": "alison",
    "val": "valerie",
    "pat": "patricia",
}

TITLES_RE = re.compile(r"^(?:rev|revd|reverend|dr|canon|fr|father|sir|lord|lady|prof|professor|capt|captain|major|col|colonel|miss|mrs|ms|mr)\b\.?\s*", re.IGNORECASE)


def clean_name(raw: str) -> str:
    """Strip titles, fix extra spaces and common encoding artifacts."""
    if not raw:
        return ""
    s = raw.strip()
    s = TITLES_RE.sub("", s).strip()
    # Repair UTF-8 encoding glitched strings like Bjrn -> Björn
    s = s.replace("Bjrn", "Björn").replace("Bj?rn", "Björn")
    s = re.sub(r"\s+", " ", s)
    return s


def parse_name(name_str: str):
    """
    Parse a clean name into:
    (first_token, middle_initials, surname, canonical_first)
    """
    parts = name_str.split()
    if not parts:
        return "", [], "", ""
    if len(parts) == 1:
        return "", [], parts[0], ""

    surname = parts[-1]
    given_parts = parts[:-1]

    first_token = given_parts[0]
    middle_initials = []

    for p in given_parts[1:]:
        # If it's an initial like "A" or "A."
        initial = p.rstrip(".")[0].upper() if p.rstrip(".") else ""
        if initial:
            middle_initials.append(initial)

    first_lower = first_token.lower().rstrip(".")
    canonical_first = DIMINUTIVES.get(first_lower, first_lower)

    return first_token, middle_initials, surname, canonical_first


def name_compatibility(n1: str, n2: str) -> float:
    """
    Compute linguistic compatibility between two ringer names with identical surnames.
    Returns score between 0.0 and 1.0.
    """
    f1, m1, s1, c1 = parse_name(n1)
    f2, m2, s2, c2 = parse_name(n2)

    if s1.lower() != s2.lower():
        return 0.0

    # 1. Exact string match
    if n1.lower() == n2.lower():
        return 1.0

    # 2. Both are single initials only (e.g. "J" vs "J")
    if len(f1) == 1 and len(f2) == 1:
        if f1.upper() == f2.upper():
            return 0.60 if m1 == m2 else 0.40
        return 0.0

    # 3. Diminutive match (e.g. "Bob" vs "Robert")
    if c1 and c2 and c1 == c2 and len(c1) > 1:
        if m1 and m2:
            return 0.95 if m1 == m2 else 0.10
        return 0.90

    # 4. One is an initial, other is full name (e.g. "J" vs "James")
    if f1 and f2 and (len(f1) == 1 or len(f2) == 1):
        init1 = f1[0].upper()
        init2 = f2[0].upper()
        if init1 == init2:
            # Check middle initials
            if m1 and m2:
                if m1 == m2:
                    return 0.85
                return 0.10  # conflicting middle initials (e.g. J A Smith vs J B Smith)
            return 0.70  # one initial, no conflicting middle
        return 0.0

    # 5. One has no first name at all (e.g. single surname like "Wheatley" vs "Paul Wheatley")
    if not f1 or not f2:
        return 0.40  # neutral surname-only match

    # 5. Full first names that differ (e.g. "James" vs "Barry")
    return 0.0


def jaccard(set1: set, set2: set) -> float:
    if not set1 or not set2:
        return 0.0
    intersection = len(set1.intersection(set2))
    union = len(set1.union(set2))
    return intersection / union if union else 0.0


def resolve_identities(db_path: Path, out_path: Path):
    print(f"Reading ringer performance records from {db_path} ...", flush=True)
    conn = sqlite3.connect(db_path)

    # 1. Fetch performances and bands.
    # The SQL is read from queries/, not held here: a recorded query that is only
    # a copy of the real one drifts, and this pair had already drifted (see the
    # header of that file).
    sql = (Path(__file__).resolve().parent.parent / "queries"
           / "extract_ringer_performances.sql").read_text()
    cursor = conn.cursor()
    records = cursor.execute(sql).fetchall()
    conn.close()

    print(f"  Loaded {len(records):,} ringer performance instances.", flush=True)

    # 2. Build performance bands & profile for each ringer name
    perf_bands = collections.defaultdict(set)
    name_perf_count = collections.Counter()
    name_towers = collections.defaultdict(set)
    name_assocs = collections.defaultdict(set)
    name_co_ringers = collections.defaultdict(set)
    name_dates = collections.defaultdict(list)
    name_places = collections.defaultdict(set)

    # First pass: map performance bands
    for perf_id, pos, raw_name, p_date, assoc, tower_id, place in records:
        clean = clean_name(raw_name)
        if clean:
            perf_bands[perf_id].add(clean)

    # Second pass: compute ringer profiles
    for perf_id, pos, raw_name, p_date, assoc, tower_id, place in records:
        clean = clean_name(raw_name)
        if not clean:
            continue
        name_perf_count[clean] += 1
        if tower_id:
            name_towers[clean].add(int(tower_id))
        if assoc:
            name_assocs[clean].add(assoc.strip())
        if place:
            name_places[clean].add(place.strip())
        if p_date:
            name_dates[clean].append(p_date)
        
        # Co-ringers in this band (excluding self)
        band = perf_bands[perf_id]
        name_co_ringers[clean].update(band - {clean})

    all_names = sorted(name_perf_count.keys())
    print(f"  Distinct cleaned ringer name strings: {len(all_names):,}", flush=True)

    # 3. Group by surname for candidate clustering
    surname_groups = collections.defaultdict(list)
    for name in all_names:
        _, _, surname, _ = parse_name(name)
        if surname:
            surname_groups[surname.lower()].append(name)

    print(f"  Grouped into {len(surname_groups):,} surname cohorts.", flush=True)

    # 4. Cluster compatible names within each surname cohort with strict anti-conflation
    # Disjoint-Set / Union-Find for entity clustering with name-conflict checks
    parent = {n: n for n in all_names}
    cluster_members = {n: {n} for n in all_names}
    match_evidence = collections.defaultdict(dict)

    def find(i):
        if parent[i] == i:
            return i
        parent[i] = find(parent[i])
        return parent[i]

    def has_first_name_conflict(c_members1, c_members2):
        """Check if merging two clusters would place two mutually conflicting full first names together."""
        for m1 in c_members1:
            f1, _, _, can1 = parse_name(m1)
            if len(f1) <= 1:
                continue  # Initial only, not a hard conflict
            for m2 in c_members2:
                f2, _, _, can2 = parse_name(m2)
                if len(f2) <= 1:
                    continue  # Initial only
                # Both are full first names: check if they are compatible
                if can1 != can2 and f1.lower() != f2.lower():
                    return True  # Hard conflict (e.g. Derek vs Dylan, John vs James)
        return False

    def union(i, j, score, rationale):
        root_i = find(i)
        root_j = find(j)
        if root_i == root_j:
            return

        # Check if merging would violate full first-name incompatibility
        if has_first_name_conflict(cluster_members[root_i], cluster_members[root_j]):
            return  # Block merge: prevent ambiguous initial from bridging two distinct people

        parent[root_i] = root_j
        cluster_members[root_j].update(cluster_members[root_i])
        cluster_members[root_i].clear()

        pair_key = tuple(sorted([i, j]))
        match_evidence[pair_key] = {"score": score, "rationale": rationale}

    total_pairs_evaluated = 0
    total_matches_found = 0

    for s_lower, names in surname_groups.items():
        if len(names) <= 1:
            continue

        n_len = len(names)
        for i in range(n_len):
            n1 = names[i]
            for j in range(i + 1, n_len):
                n2 = names[j]
                total_pairs_evaluated += 1

                name_score = name_compatibility(n1, n2)
                if name_score <= 0.0:
                    continue  # Incompatible names (e.g. John vs James)

                # Compute network overlap
                tower_sim = jaccard(name_towers[n1], name_towers[n2])
                assoc_sim = jaccard(name_assocs[n1], name_assocs[n2])
                band_sim = jaccard(name_co_ringers[n1], name_co_ringers[n2])

                # Evidence weighting
                # If high band co-occurrence or shared towers, strong reinforcement
                combined_score = (name_score * 0.45) + (band_sim * 0.30) + (tower_sim * 0.15) + (assoc_sim * 0.10)

                # Match threshold
                # 1. High name similarity + at least one network link
                # 2. OR very high diminutive/name match (>0.85) when one variant has low peal count (<3)
                is_match = False
                rationale = []

                if name_score >= 0.85:
                    if band_sim > 0.05 or tower_sim > 0.05 or assoc_sim > 0.10 or name_perf_count[n1] <= 3 or name_perf_count[n2] <= 3:
                        is_match = True
                        rationale.append(f"High name match ({name_score:.2f})")
                        if band_sim > 0: rationale.append(f"Band Jaccard {band_sim:.2f}")
                        if tower_sim > 0: rationale.append(f"Tower Jaccard {tower_sim:.2f}")
                elif name_score >= 0.65:
                    if band_sim >= 0.10 or tower_sim >= 0.10 or (assoc_sim >= 0.25 and (band_sim > 0 or tower_sim > 0)):
                        is_match = True
                        rationale.append(f"Initial/name match ({name_score:.2f}) + Network (Band {band_sim:.2f}, Tower {tower_sim:.2f})")

                if is_match:
                    union(n1, n2, combined_score, "; ".join(rationale))
                    total_matches_found += 1

    print(f"  Evaluated {total_pairs_evaluated:,} candidate pairs. Formed {total_matches_found:,} identity links.", flush=True)

    # 5. Extract clusters and select canonical name
    clusters = collections.defaultdict(list)
    for name in all_names:
        root = find(name)
        clusters[root].append(name)

    print(f"  Clustered {len(all_names):,} raw names into {len(clusters):,} canonical ringer entities.", flush=True)

    # 6. Build Master Candidate Rows
    candidate_rows = []
    cluster_idx = 1

    for root, members in sorted(clusters.items(), key=lambda x: -sum(name_perf_count[m] for m in x[1])):
        ringer_id = f"RINGER_{cluster_idx:06d}"
        cluster_idx += 1

        # Select canonical representation: longest full name with highest peal count
        def name_richness(n):
            f, m, s, _ = parse_name(n)
            has_full_first = 1 if len(f) > 1 else 0
            has_middle = 1 if m else 0
            return (has_full_first, has_middle, name_perf_count[n], len(n))

        canonical_name = max(members, key=name_richness)
        cluster_total_peals = sum(name_perf_count[m] for m in members)

        # Aggregate primary towers & associations for canonical ringer
        cluster_towers = set()
        cluster_assocs = set()
        cluster_dates = []
        for m in members:
            cluster_towers.update(name_towers[m])
            cluster_assocs.update(name_assocs[m])
            cluster_dates.extend(name_dates[m])

        first_year = min(cluster_dates)[:4] if cluster_dates else ""
        last_year = max(cluster_dates)[:4] if cluster_dates else ""

        for m in members:
            is_canon = (m == canonical_name)
            pair_key = tuple(sorted([m, canonical_name]))
            ev_info = match_evidence.get(pair_key, {})
            score = ev_info.get("score", 1.0 if is_canon else 0.75)
            rationale = ev_info.get("rationale", "Canonical identity" if is_canon else "Clustered alias")

            conf = "high" if (is_canon or score >= 0.70) else ("medium" if score >= 0.50 else "low")

            candidate_rows.append({
                "raw_name": m,
                "canonical_ringer_id": ringer_id,
                "canonical_name": canonical_name,
                "is_primary": "true" if is_canon else "false",
                "variant_peal_count": name_perf_count[m],
                "cluster_total_peals": cluster_total_peals,
                "confidence": conf,
                "evidence_score": f"{score:.3f}",
                "active_years": f"{first_year}–{last_year}" if first_year else "",
                "primary_towers_count": len(cluster_towers),
                "primary_assocs_count": len(cluster_assocs),
                "match_rationale": rationale
            })

    # Sort rows by cluster_total_peals desc, then ringer_id, then is_primary desc
    candidate_rows.sort(key=lambda x: (-x["cluster_total_peals"], x["canonical_ringer_id"], x["is_primary"] != "true", -x["variant_peal_count"]))

    # 7. Write data/ringer_identity_candidates.csv
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "raw_name", "canonical_ringer_id", "canonical_name", "is_primary",
        "variant_peal_count", "cluster_total_peals", "confidence", "evidence_score",
        "active_years", "primary_towers_count", "primary_assocs_count", "match_rationale"
    ]
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(candidate_rows)

    print(f"\nWrote {len(candidate_rows):,} ringer candidate mappings to {out_path} ({out_path.stat().st_size / 1024:.1f} KB)", flush=True)

    # Multi-variant clusters count
    multi_variant = sum(1 for members in clusters.values() if len(members) > 1)
    print(f"\nResolution Summary:")
    print(f"  • Total raw names: {len(all_names):,}")
    print(f"  • Resolved canonical ringers: {len(clusters):,}")
    print(f"  • Multi-name variant clusters unified: {multi_variant:,}")
    print(f"  • Single-name clusters: {len(clusters) - multi_variant:,}")


def main():
    parser = argparse.ArgumentParser(description="Resolve ringer identities across BellBoard corpus.")
    parser.add_argument("--db", default=str(DEFAULT_DB), help="SQLite database path")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="Output CSV path")
    args = parser.parse_args()

    db_path = Path(args.db)
    out_path = Path(args.out)
    resolve_identities(db_path, out_path)


if __name__ == "__main__":
    main()
