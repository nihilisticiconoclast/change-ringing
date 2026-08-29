#!/usr/bin/env python3
"""
Composer Identity Resolution Engine (Roadmap Item R-41 / G-12).

Cross-references and normalises composer names across:
- CompLib compositions (86,054 records, 1,456 distinct extracted composers)
- BellBoard performances (71,959 records with composer, 13,333 distinct raw strings)

Emits a calibrated candidate dataset with full confidence scale (high, medium, low)
and verified match rules to prevent middle-initial and common-surname conflations.

Usage:
    python scripts/resolve_composer_identities.py --local-db local_corpus.db --out data/composer_identity_candidates.csv
"""

import argparse
import csv
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

# Add scripts directory to path for imports
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import db

# Historical abbreviation dictionary for change ringing composers
ABBREVIATIONS = {
    "chas": "Charles",
    "chas.": "Charles",
    "wm": "William",
    "wm.": "William",
    "jas": "James",
    "jas.": "James",
    "geo": "George",
    "geo.": "George",
    "thos": "Thomas",
    "thos.": "Thomas",
    "edw": "Edward",
    "edw.": "Edward",
    "robt": "Robert",
    "robt.": "Robert",
    "saml": "Samuel",
    "saml.": "Samuel",
    "jno": "John",
    "jno.": "John",
    "benj": "Benjamin",
    "benj.": "Benjamin",
    "fredk": "Frederick",
    "fredk.": "Frederick",
    "richd": "Richard",
    "richd.": "Richard",
    "alfd": "Alfred",
    "alfd.": "Alfred",
    "arth": "Arthur",
    "arth.": "Arthur",
    "danl": "Daniel",
    "danl.": "Daniel",
    "steph": "Stephen",
    "steph.": "Stephen",
}

# Standardized collective / anonymous aliases
ANON_ALIASES = {
    "traditional": "Traditional",
    "trad": "Traditional",
    "trad.": "Traditional",
    "traditionel": "Traditional",
    "traditional.": "Traditional",
    "anonymous": "Anonymous",
    "anon": "Anonymous",
    "anon.": "Anonymous",
    "unknown": "Unknown",
    "none": "None",
    "byroc": "BYROC",
    "elf": "Elf",
    "bew": "BEW",
}


def clean_raw_composer(raw_str: str) -> str:
    """Strips common prefixes, suffixes, and noise from a raw composer string."""
    if not raw_str:
        return ""
    s = raw_str.strip()

    # Strip prefixes (including abbreviations with periods: Arr., Comp., Ed., etc.)
    s = re.sub(
        r"^(?:arr(?:\.|(?:anged)?)(?:\s+by)?|comp(?:\.|(?:osed)?)(?:\s+by)?|joint(?:ly)?(?:\s+with)?|rung\s+by|ed(?:\.|(?:ited)?)(?:\s+by)?|adapted\s+by|transposed\s+by|conductor:?|composer:?)\s+",
        "",
        s,
        flags=re.IGNORECASE,
    )

    # Strip parenthetical suffixes: (arr.), (comp), (5088), (quarter), (no. 123), etc.
    s = re.sub(
        r"\s*\((?:arr\.?|comp\.?|conductor|tenor|peal|quarter|no\.?\s*[\w\d\s,\-\./]+|\d+|op\.?\s*[\w\d\s]+)\)$",
        "",
        s,
        flags=re.IGNORECASE,
    )
    s = re.sub(
        r"\s*\[(?:arr\.?|comp\.?|conductor|no\.?\s*[\w\d\s,\-\./]+|\d+)\]$",
        "",
        s,
        flags=re.IGNORECASE,
    )

    # Clean whitespace and periods between initials: J. S. -> J S, J.S. -> J S
    s = re.sub(r"\b([A-Z])\.", r"\1 ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def parse_name_tokens(cleaned_name: str):
    """
    Parses a cleaned name into forename/initials and surname.
    Returns: (is_initials_only, forename, middle_initials, surname, full_initials)
    """
    tokens = cleaned_name.split()
    if not tokens:
        return True, "", [], "", []

    if len(tokens) == 1:
        return False, tokens[0], [], tokens[0], [tokens[0][0].upper()]

    surname = tokens[-1]
    given_tokens = tokens[:-1]

    # Expand historical abbreviations
    expanded_given = []
    for t in given_tokens:
        lower_t = t.lower()
        if lower_t in ABBREVIATIONS:
            expanded_given.append(ABBREVIATIONS[lower_t])
        else:
            expanded_given.append(t)

    initials = [t[0].upper() for t in expanded_given]
    is_initials_only = all(len(t) == 1 for t in expanded_given)

    forename = expanded_given[0]
    middle_initials = [t[0].upper() for t in expanded_given[1:]]

    return is_initials_only, forename, middle_initials, surname, initials


class ComposerResolver:
    """Multi-tiered authority resolver for change ringing composers."""

    def __init__(self):
        self.authority_full = {}          # canonical_name.lower() -> canonical_name
        self.authority_by_surname = defaultdict(list)  # surname.lower() -> list of canonical_name
        self.authority_by_initials = defaultdict(list) # (initials_tuple, surname.lower()) -> list of canonical_name
        self.authority_by_fn_sn = defaultdict(list)    # (forename.lower(), surname.lower()) -> list of canonical_name
        self.entity_frequencies = Counter()

    def build_authority_index(self, authority_names: Counter):
        """Builds multi-index lookups from rich full names across CompLib and BellBoard."""
        for name, count in authority_names.items():
            cleaned = clean_raw_composer(name)
            if not cleaned or len(cleaned) < 3:
                continue

            lower_clean = cleaned.lower()
            if lower_clean in ANON_ALIASES:
                continue

            tokens = cleaned.split()
            if len(tokens) < 2:
                continue

            # Only index as authority if the forename is a FULL forename (len > 1)
            if len(tokens[0]) <= 1:
                continue

            canonical_name = cleaned
            self.authority_full[lower_clean] = canonical_name
            self.entity_frequencies[canonical_name] += count

            is_init, forename, mid_inits, surname, initials = parse_name_tokens(cleaned)
            sn_lower = surname.lower()
            fn_lower = forename.lower()

            self.authority_by_surname[sn_lower].append(canonical_name)
            self.authority_by_initials[(tuple(initials), sn_lower)].append(canonical_name)
            self.authority_by_fn_sn[(fn_lower, sn_lower)].append(canonical_name)

        # Deduplicate indexed authority lists
        for k in self.authority_by_surname:
            self.authority_by_surname[k] = list(set(self.authority_by_surname[k]))
        for k in self.authority_by_initials:
            self.authority_by_initials[k] = list(set(self.authority_by_initials[k]))
        for k in self.authority_by_fn_sn:
            self.authority_by_fn_sn[k] = list(set(self.authority_by_fn_sn[k]))

    def resolve(self, raw_str: str):
        """
        Resolves a raw composer string into (canonical_name, confidence, rule, evidence).
        """
        if not raw_str or not raw_str.strip():
            return "None", "high", "empty_string", "No composer name supplied"

        raw_trimmed = raw_str.strip()
        lower_raw = raw_trimmed.lower()

        # 1. Check anonymous / collective aliases
        if lower_raw in ANON_ALIASES:
            canon = ANON_ALIASES[lower_raw]
            return canon, "high", "anonymous_collective_norm", f"Standardized collective/alias {raw_str!r} -> {canon}"

        cleaned = clean_raw_composer(raw_trimmed)
        lower_clean = cleaned.lower()

        if lower_clean in ANON_ALIASES:
            canon = ANON_ALIASES[lower_clean]
            return canon, "high", "anonymous_collective_norm", f"Cleaned collective/alias {raw_str!r} -> {canon}"

        # 2. Exact match against authority full name
        if lower_clean in self.authority_full:
            canon = self.authority_full[lower_clean]
            return canon, "high", "exact_authority_match", f"Exact match with canonical authority {canon}"

        is_init, forename, mid_inits, surname, initials = parse_name_tokens(cleaned)
        sn_lower = surname.lower()
        fn_lower = forename.lower()

        # 3. Multi-initial exact match (e.g. D F Morrison -> Donald F Morrison, R D S Brown -> Robert D S Brown)
        init_key = (tuple(initials), sn_lower)
        if init_key in self.authority_by_initials:
            candidates = self.authority_by_initials[init_key]
            if len(candidates) == 1:
                canon = candidates[0]
                conf = "high" if len(initials) >= 2 else "medium"
                rule_name = "multi_initial_unique_match" if len(initials) >= 2 else "single_initial_unique_match"
                return canon, conf, rule_name, f"Initials {' '.join(initials)} {surname} uniquely matches {canon}"
            elif len(candidates) > 1:
                # Rank candidates by frequency
                candidates.sort(key=lambda c: self.entity_frequencies[c], reverse=True)
                top_cand = candidates[0]
                top_count = self.entity_frequencies[top_cand]
                other_counts = sum(self.entity_frequencies[c] for c in candidates[1:])

                # If the top candidate is overwhelmingly dominant (>80% share)
                if top_count >= 10 and top_count >= 4 * max(1, other_counts):
                    conf = "high" if len(initials) >= 2 else "medium"
                    rule_name = "multi_initial_dominant_match" if len(initials) >= 2 else "single_initial_dominant_match"
                    return top_cand, conf, rule_name, f"Dominant match {top_cand} ({top_count} vs {other_counts} across {len(candidates)} variants)"
                else:
                    rule_name = "multi_initial_collision" if len(initials) >= 2 else "single_initial_collision"
                    return top_cand, "low", rule_name, f"Initials match {len(candidates)} distinct candidates ({', '.join(candidates[:3])}); mapped to most frequent {top_cand}"

        # 4. Forename + Surname match (e.g. Daniel Brady -> Daniel W Brady)
        fn_sn_key = (fn_lower, sn_lower)
        if fn_sn_key in self.authority_by_fn_sn:
            candidates = self.authority_by_fn_sn[fn_sn_key]
            if len(candidates) == 1:
                canon = candidates[0]
                return canon, "high", "forename_surname_unique_match", f"{forename} {surname} uniquely matches {canon}"
            elif len(candidates) > 1:
                candidates.sort(key=lambda c: self.entity_frequencies[c], reverse=True)
                top_cand = candidates[0]
                return top_cand, "medium", "forename_surname_collision", f"Forename+Surname matches {len(candidates)} candidates ({', '.join(candidates[:3])}); mapped to {top_cand}"

        # 5. Single initial + Surname matching (e.g. C Middleton -> Charles Middleton, N Smith -> Norman Smith)
        if is_init and len(initials) == 1:
            init_letter = initials[0]
            if sn_lower in self.authority_by_surname:
                cands = [c for c in self.authority_by_surname[sn_lower] if c.startswith(init_letter)]
                if len(cands) == 1:
                    canon = cands[0]
                    conf = "medium" if self.entity_frequencies[canon] >= 10 else "low"
                    return canon, conf, "single_initial_dominant_match", f"Single initial {init_letter} {surname} uniquely matched to authority {canon}"
                elif len(cands) > 1:
                    cands.sort(key=lambda c: self.entity_frequencies[c], reverse=True)
                    top_cand = cands[0]
                    top_count = self.entity_frequencies[top_cand]
                    other_counts = sum(self.entity_frequencies[c] for c in cands[1:])
                    if top_count >= 20 and top_count >= 5 * max(1, other_counts):
                        return top_cand, "medium", "single_initial_dominant_match", f"Dominant single initial {top_cand} ({top_count} vs {other_counts})"
                    return top_cand, "low", "single_initial_collision", f"Ambiguous initial {init_letter} {surname} collides across {len(cands)} authority entities ({', '.join(cands[:3])})"

        # 6. Fallback: Preserved cleaned title-case name
        if len(cleaned.split()) >= 2:
            return cleaned.title(), "medium", "cleaned_name_fallback", f"No authority entity found; preserved cleaned name {cleaned.title()}"
        else:
            return cleaned.title() if cleaned else "Unknown", "low", "unresolved_fragment", f"Single token / bare surname / unresolved {raw_str!r}"


def extract_all_raw_composers(conn):
    """Extracts all raw composer strings and counts from CompLib and BellBoard."""
    cur = conn.cursor()

    # 1. CompLib extracted composers from derived_title
    cur.execute("SELECT derived_title FROM compositions WHERE derived_title IS NOT NULL")
    complib_raw = Counter()
    for (t,) in cur.fetchall():
        m = re.search(r"\bby\s+(.+)$", t, re.IGNORECASE)
        if m:
            c_str = m.group(1).strip()
            for part in re.split(r"\s+and\s+|\s*&\s*", c_str):
                part = part.strip()
                if part and len(part) > 1:
                    complib_raw[part] += 1

    # 2. BellBoard composers from performances.composer
    cur.execute("SELECT composer, COUNT(*) FROM performances WHERE composer IS NOT NULL AND composer != '' GROUP BY composer")
    bb_raw = dict(cur.fetchall())

    all_raw = Counter()
    sources = {}

    for k, v in bb_raw.items():
        all_raw[k] += v
        sources[k] = "bellboard"

    for k, v in complib_raw.items():
        all_raw[k] += v
        sources[k] = "both" if k in sources else "complib"

    return all_raw, sources, complib_raw, bb_raw


def run_resolution(conn, out_csv: str):
    """Runs complete resolution pipeline and outputs candidates CSV."""
    all_raw, sources, complib_raw, bb_raw = extract_all_raw_composers(conn)
    total_raw_strings = len(all_raw)
    total_instances = sum(all_raw.values())

    print(f"Loaded {total_raw_strings:,} distinct raw composer strings ({total_instances:,} total instances).")

    # Build authority dictionary from rich names
    authority_candidates = Counter()
    for name, cnt in complib_raw.items():
        cleaned = clean_raw_composer(name)
        tokens = cleaned.split()
        if len(tokens) >= 2 and len(tokens[0]) > 1:
            authority_candidates[cleaned] += cnt * 10  # CompLib weighting

    for name, cnt in bb_raw.items():
        cleaned = clean_raw_composer(name)
        tokens = cleaned.split()
        if len(tokens) >= 2 and len(tokens[0]) > 1:
            if cnt >= 3 or cleaned in authority_candidates:
                authority_candidates[cleaned] += cnt

    resolver = ComposerResolver()
    resolver.build_authority_index(authority_candidates)
    print(f"Indexed {len(resolver.authority_full):,} authority entities.")

    # Resolve all raw strings
    conf_dist = Counter()
    rule_dist = Counter()
    resolved_rows = []

    for raw_str, freq in all_raw.most_common():
        canon, conf, rule, evidence = resolver.resolve(raw_str)
        src = sources.get(raw_str, "unknown")
        resolved_rows.append({
            "raw_composer": raw_str,
            "canonical_composer": canon,
            "confidence": conf,
            "match_rule": rule,
            "source": src,
            "frequency": freq,
            "evidence": evidence
        })
        conf_dist[conf] += 1
        rule_dist[rule] += 1

    # Write output CSV
    os.makedirs(os.path.dirname(os.path.abspath(out_csv)), exist_ok=True)
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["raw_composer", "canonical_composer", "confidence", "match_rule", "source", "frequency", "evidence"],
            lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(resolved_rows)

    print(f"Wrote {out_csv} ({total_raw_strings:,} rows).")
    print()
    print("=" * 60)
    print("COMPOSER RESOLUTION SUMMARY:")
    print("=" * 60)
    print("Confidence Breakdown:")
    for conf, cnt in conf_dist.most_common():
        pct = (cnt / total_raw_strings) * 100.0
        print(f"  {conf:<10}: {cnt:>6,} ({pct:>5.1f}%)")
    print()
    print("Match Rules Breakdown:")
    for rule, cnt in rule_dist.most_common():
        pct = (cnt / total_raw_strings) * 100.0
        print(f"  {rule:<32}: {cnt:>6,} ({pct:>5.1f}%)")
    print("=" * 60)

    return resolved_rows


def main():
    parser = argparse.ArgumentParser(description="Resolve composer identities across CompLib and BellBoard")
    db.add_db_args(parser)
    parser.add_argument("--out", default="data/composer_identity_candidates.csv", help="Output candidates CSV path")
    args = parser.parse_args()

    conn = db.connect(args)
    run_resolution(conn, args.out)
    conn.close()


if __name__ == "__main__":
    main()
