#!/usr/bin/env python3
"""
Build the Canonical Dedication and Place-Name Lexicon for the Change Ringing Corpus.

Generates data/name_lexicon.csv: a comprehensive, authoritative mapping of
Anglican/Catholic church dedication abbreviations, spelling variants, saint aliases,
and English toponymic variations across 7,262 Dove towers, 15,720 tower records,
and 30,734 method performances.

Usage:
    python scripts/build_name_lexicon.py --db data/change-ringing.db --out data/name_lexicon.csv
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
DEFAULT_OUT = ROOT / "data" / "name_lexicon.csv"
QUERIES_DIR = ROOT / "queries"

# ----------------------------------------------------------------------
# 1. High-Precision Normalization Rules
# ----------------------------------------------------------------------

# Honorific titles and prefixes
PREFIX_EXPANSIONS = [
    (r"^Cath & Abbey Ch of\b", "Cathedral and Abbey Church of", "abbreviation_expansion"),
    (r"^Cath & Abbey Ch\b", "Cathedral and Abbey Church", "abbreviation_expansion"),
    (r"^Cath Ch of\b", "Cathedral Church of", "abbreviation_expansion"),
    (r"^Cath Ch\b", "Cathedral Church", "abbreviation_expansion"),
    (r"^Cath of\b", "Cathedral of", "abbreviation_expansion"),
    (r"^Cath\b", "Cathedral", "abbreviation_expansion"),
    (r"^Abbey Ch of\b", "Abbey Church of", "abbreviation_expansion"),
    (r"^Priory Ch of\b", "Priory Church of", "abbreviation_expansion"),
    (r"^Collegiate Ch of\b", "Collegiate Church of", "abbreviation_expansion"),
    (r"^Minster Ch of\b", "Minster Church of", "abbreviation_expansion"),
    (r"^Parish Ch of\b", "Parish Church of", "abbreviation_expansion"),
    (r"^Ch of\b", "Church of", "abbreviation_expansion"),
    (r"^H Trinity\b", "Holy Trinity", "abbreviation_expansion"),
    (r"^H Cross\b", "Holy Cross", "abbreviation_expansion"),
    (r"^H Innocents\b", "Holy Innocents", "abbreviation_expansion"),
    (r"^H Ghost\b", "Holy Ghost", "abbreviation_expansion"),
    (r"^H Rood\b", "Holy Rood", "abbreviation_expansion"),
    (r"^H Name\b", "Holy Name", "abbreviation_expansion"),
    (r"^H Family\b", "Holy Family", "abbreviation_expansion"),
    (r"^H Apostles\b", "Holy Apostles", "abbreviation_expansion"),
    (r"^All SS\b", "All Saints", "abbreviation_expansion"),
    (r"^Christ Ch\b", "Christ Church", "abbreviation_expansion"),
    (r"^BVM\b", "Blessed Virgin Mary", "abbreviation_expansion"),
    (r"^Assumption of BVM\b", "Assumption of the Blessed Virgin Mary", "abbreviation_expansion"),
    (r"^Annunciation BVM\b", "Annunciation of the Blessed Virgin Mary", "abbreviation_expansion"),
    (r"^Nativity of BVM\b", "Nativity of the Blessed Virgin Mary", "abbreviation_expansion"),
]

# Dedication qualifiers & suffixes
QUALIFIER_EXPANSIONS = [
    (r"\bS Mary V\b", "Saint Mary the Virgin", "abbreviation_expansion"),
    (r"\bS Mary the V\b", "Saint Mary the Virgin", "abbreviation_expansion"),
    (r"\bSt Mary V\b", "Saint Mary the Virgin", "abbreviation_expansion"),
    (r"\bSt Mary the V\b", "Saint Mary the Virgin", "abbreviation_expansion"),
    (r"\bS Mary Magd\b", "Saint Mary Magdalene", "abbreviation_expansion"),
    (r"\bSt Mary Magd\b", "Saint Mary Magdalene", "abbreviation_expansion"),
    (r"\bS Mary Mag\b", "Saint Mary Magdalene", "abbreviation_expansion"),
    (r"\bS John Bapt\b", "Saint John the Baptist", "abbreviation_expansion"),
    (r"\bSt John Bapt\b", "Saint John the Baptist", "abbreviation_expansion"),
    (r"\bS John B\b", "Saint John the Baptist", "abbreviation_expansion"),
    (r"\bSt John B\b", "Saint John the Baptist", "abbreviation_expansion"),
    (r"\bS John Div\b", "Saint John the Divine", "abbreviation_expansion"),
    (r"\bSt John Div\b", "Saint John the Divine", "abbreviation_expansion"),
    (r"\bS John the Div\b", "Saint John the Divine", "abbreviation_expansion"),
    (r"\bS John Evang\b", "Saint John the Evangelist", "abbreviation_expansion"),
    (r"\bSt John Evang\b", "Saint John the Evangelist", "abbreviation_expansion"),
    (r"\bS John the Evang\b", "Saint John the Evangelist", "abbreviation_expansion"),
    (r"\bS John Ev\b", "Saint John the Evangelist", "abbreviation_expansion"),
    (r"\bSt John Ev\b", "Saint John the Evangelist", "abbreviation_expansion"),
    (r"\bS Mark Ev\b", "Saint Mark the Evangelist", "abbreviation_expansion"),
    (r"\bSt Mark Ev\b", "Saint Mark the Evangelist", "abbreviation_expansion"),
    (r"\bS Luke Ev\b", "Saint Luke the Evangelist", "abbreviation_expansion"),
    (r"\bSt Luke Ev\b", "Saint Luke the Evangelist", "abbreviation_expansion"),
    (r"\bS Matthew Ev\b", "Saint Matthew the Evangelist", "abbreviation_expansion"),
    (r"\bSt Matthew Ev\b", "Saint Matthew the Evangelist", "abbreviation_expansion"),
    (r"\bS Thomas a Becket\b", "Saint Thomas Becket", "spelling_variant"),
    (r"\bSt Thomas a Becket\b", "Saint Thomas Becket", "spelling_variant"),
    (r"\bS Thomas of Canterbury\b", "Saint Thomas Becket", "alias"),
    (r"\bSt Thomas of Canterbury\b", "Saint Thomas Becket", "alias"),
    (r"\bS Michael & AA\b", "Saint Michael and All Angels", "abbreviation_expansion"),
    (r"\bSt Michael & AA\b", "Saint Michael and All Angels", "abbreviation_expansion"),
    (r"\bS Michael & All AA\b", "Saint Michael and All Angels", "abbreviation_expansion"),
    (r"\bBVM\b", "the Blessed Virgin Mary", "abbreviation_expansion"),
    (r"\b\(RC\)\b", "(Roman Catholic)", "abbreviation_expansion"),
    (r"\bCh\b", "Church", "abbreviation_expansion"),
    (r"\bK & M\b", "King and Martyr", "honorific_expansion"),
    (r"\bK&M\b", "King and Martyr", "honorific_expansion"),
    (r"\bB & M\b", "Bishop and Martyr", "honorific_expansion"),
    (r"\bB&M\b", "Bishop and Martyr", "honorific_expansion"),
    (r"\bK & C\b", "King and Confessor", "honorific_expansion"),
    (r"\bK&C\b", "King and Confessor", "honorific_expansion"),
    (r"\bB & C\b", "Bishop and Confessor", "honorific_expansion"),
    (r"\bB&C\b", "Bishop and Confessor", "honorific_expansion"),
    (r"\bP & M\b", "Pope and Martyr", "honorific_expansion"),
]

# Canonical Saint Spelling Variants (Variant -> Canonical)
SAINT_SPELLING_VARIANTS = {
    "Laurence": "Lawrence",
    "Katherine": "Catherine",
    "Catharine": "Catherine",
    "Katharine": "Catherine",
    "Swithun": "Swithin",
    "Alphege": "Alfege",
    "Elfego": "Alfege",
    "Bartholomew": "Bartholomew",
    "Bartolomew": "Bartholomew",
    "Botolph": "Botolph",
    "Botulph": "Botolph",
    "Ceadda": "Chad",
    "Cuthberht": "Cuthbert",
    "Dunston": "Dunstan",
    "Edmond": "Edmund",
    "Ethelreda": "Etheldreda",
    "Audrey": "Etheldreda",
    "Guthlake": "Guthlac",
    "Helena": "Helen",
    "Hillary": "Hilary",
    "Marguerite": "Margaret",
    "Mildryth": "Mildred",
    "Oswold": "Oswald",
    "Petrock": "Petroc",
    "Petrox": "Petroc",
    "Wolfran": "Wulfram",
    "Vulfran": "Wulfram",
    "Weneppa": "Wennapa",
    "Wenappa": "Wennapa",
    "Mabena": "Mabyn",
    "Glywys": "Gluvias",
    "Fiacc": "Feock",
    "Breage": "Breaca",
    "Budock": "Budoc",
}

# Toponymic Pattern Normalization
TOPONYMIC_VARIANTS = [
    (r"\bBarrow-on-Soar\b", "Barrow upon Soar", "toponym_variant"),
    (r"\bNewcastle-upon-Tyne\b", "Newcastle upon Tyne", "toponym_variant"),
    (r"\bNewcastle on Tyne\b", "Newcastle upon Tyne", "toponym_variant"),
    (r"\bStratford-on-Avon\b", "Stratford-upon-Avon", "toponym_variant"),
    (r"\bStratford on Avon\b", "Stratford-upon-Avon", "toponym_variant"),
    (r"\bKingston-upon-Thames\b", "Kingston upon Thames", "toponym_variant"),
    (r"\bKingston on Thames\b", "Kingston upon Thames", "toponym_variant"),
    (r"\bBerwick-upon-Tweed\b", "Berwick-upon-Tweed", "toponym_variant"),
    (r"\bBerwick on Tweed\b", "Berwick-upon-Tweed", "toponym_variant"),
    (r"\bRichmond-upon-Thames\b", "Richmond upon Thames", "toponym_variant"),
    (r"\bRichmond on Thames\b", "Richmond upon Thames", "toponym_variant"),
    (r"\bStoke-on-Trent\b", "Stoke-on-Trent", "toponym_variant"),
    (r"\bStoke upon Trent\b", "Stoke-on-Trent", "toponym_variant"),
    (r"\bSouth Mymms\b", "South Mimms", "spelling_variant"),
    (r"\bBishop's Stortford\b", "Bishops Stortford", "punctuation_variant"),
    (r"\bKing's Lynn\b", "Kings Lynn", "punctuation_variant"),
    (r"\bStoke-by-Nayland\b", "Stoke by Nayland", "toponym_variant"),
    (r"\bMinster-in-Thanet\b", "Minster in Thanet", "toponym_variant"),
    (r"\bKirkby-in-Ashfield\b", "Kirkby in Ashfield", "toponym_variant"),
    (r"\bSutton-in-Ashfield\b", "Sutton in Ashfield", "toponym_variant"),
    (r"\bWeston-super-Mare\b", "Weston-super-Mare", "toponym_variant"),
    (r"\bWeston super Mare\b", "Weston-super-Mare", "toponym_variant"),
    (r"\bStow-on-the-Wold\b", "Stow-on-the-Wold", "toponym_variant"),
    (r"\bStow on the Wold\b", "Stow-on-the-Wold", "toponym_variant"),
    (r"\bBourton-on-the-Water\b", "Bourton-on-the-Water", "toponym_variant"),
    (r"\bBourton on the Water\b", "Bourton-on-the-Water", "toponym_variant"),
    (r"\bChapel-en-le-Frith\b", "Chapel-en-le-Frith", "toponym_variant"),
    (r"\bChapel en le Frith\b", "Chapel-en-le-Frith", "toponym_variant"),
]


def expand_dedication(raw: str) -> tuple[str, str, str]:
    """
    Standardize a dedication string into its canonical representation.
    Returns: (canonical_string, category, notes)
    """
    if not raw or not isinstance(raw, str):
        return ("", "empty", "")

    s = raw.strip()
    category = "verbatim"
    notes = []

    # 1. Prefix expansions
    for pat, repl, cat in PREFIX_EXPANSIONS:
        if re.search(pat, s, re.IGNORECASE):
            s = re.sub(pat, repl, s, flags=re.IGNORECASE)
            category = cat
            notes.append(f"Prefix expanded: {pat} -> {repl}")

    # 2. Specific qualifier expansions
    for pat, repl, cat in QUALIFIER_EXPANSIONS:
        if re.search(pat, s, re.IGNORECASE):
            s = re.sub(pat, repl, s, flags=re.IGNORECASE)
            category = cat
            notes.append(f"Qualifier expanded: {pat} -> {repl}")

    # 3. Saints and Saint prefixes
    # Expand "SS " -> "Saints "
    if re.search(r"\bSS\b\.?", s):
        s = re.sub(r"\bSS\b\.?\s*", "Saints ", s)
        category = "abbreviation_expansion"
        notes.append("SS -> Saints")
    elif re.search(r"\bSts\b\.?", s):
        s = re.sub(r"\bSts\b\.?\s*", "Saints ", s)
        category = "abbreviation_expansion"
        notes.append("Sts -> Saints")

    # Expand "S " or "St " -> "Saint "
    if re.search(r"\bS\b\.?\s+([A-Z])", s):
        s = re.sub(r"\bS\b\.?\s+([A-Z])", r"Saint \1", s)
        category = "abbreviation_expansion"
        notes.append("S -> Saint")
    elif re.search(r"\bSt\b\.?\s+([A-Z])", s):
        s = re.sub(r"\bSt\b\.?\s+([A-Z])", r"Saint \1", s)
        category = "abbreviation_expansion"
        notes.append("St -> Saint")

    # Replace ampersands with "and"
    if " & " in s:
        s = s.replace(" & ", " and ")
        category = "abbreviation_expansion" if category == "verbatim" else category

    # 4. Standardize Saint spellings
    for var, canon in SAINT_SPELLING_VARIANTS.items():
        pat = rf"\b{re.escape(var)}\b"
        if re.search(pat, s, re.IGNORECASE):
            s = re.sub(pat, canon, s, flags=re.IGNORECASE)
            category = "spelling_variant" if category == "verbatim" else category
            notes.append(f"Spelling standardized: {var} -> {canon}")

    # Clean whitespace
    s = re.sub(r"\s+", " ", s).strip()
    return s, category, "; ".join(notes)


def expand_place_name(raw: str) -> tuple[str, str, str]:
    """
    Standardize a place name into its canonical representation.
    Returns: (canonical_string, category, notes)
    """
    if not raw or not isinstance(raw, str):
        return ("", "empty", "")

    s = raw.strip()
    category = "verbatim"
    notes = []

    # 1. Toponymic patterns
    for pat, repl, cat in TOPONYMIC_VARIANTS:
        if re.search(pat, s, re.IGNORECASE):
            s = re.sub(pat, repl, s, flags=re.IGNORECASE)
            category = cat
            notes.append(f"Toponym standardized: {pat} -> {repl}")

    # 2. Saint prefixes in place names (St Albans, St Ives, etc.)
    if re.match(r"^St\.?\s+([A-Z])", s):
        s = re.sub(r"^St\.?\s+([A-Z])", r"Saint \1", s)
        category = "abbreviation_expansion" if category == "verbatim" else category
        notes.append("Place St -> Saint")

    # 3. Clean trailing / leading commas, spaces
    s = re.sub(r"\s+", " ", s).strip(", ")
    return s, category, "; ".join(notes)


def build_lexicon(db_path: Path, out_path: Path):
    print(f"Reading corpus data from {db_path} ...")
    conn = sqlite3.connect(db_path)

    # 1. Fetch dedications and places from Dove & Towers
    query_path = QUERIES_DIR / "extract_dedications_and_places.sql"
    if query_path.exists():
        sql = query_path.read_text(encoding="utf-8")
    else:
        sql = """
        SELECT DISTINCT 'dove' AS source_table, TowerID, Dedicn, BareDedicn, Place, Place2, PlaceCL, AltName, County, Country FROM dove WHERE Dedicn IS NOT NULL OR Place IS NOT NULL
        UNION ALL
        SELECT DISTINCT 'towers' AS source_table, TowerID, Dedicn, BareDedicn, Place, Place2, PlaceCL, AltName, County, Country FROM towers WHERE Dedicn IS NOT NULL OR Place IS NOT NULL
        """
    cursor = conn.cursor()
    records = cursor.execute(sql).fetchall()

    # 2. Fetch method performances building and town names
    mp_records = cursor.execute("SELECT DISTINCT building, town, county FROM method_performances WHERE building IS NOT NULL OR town IS NOT NULL").fetchall()
    conn.close()

    print(f"  Loaded {len(records):,} Dove/Towers records and {len(mp_records):,} Method Performances records.")

    # Frequency counters and sample collectors
    term_counts = collections.Counter()
    term_samples = collections.defaultdict(list)
    term_domains = {}

    # Process Dove/Towers
    for src, tid, ded, bare, pl, pl2, pl_cl, alt, cty, ctry in records:
        if ded:
            t = ded.strip()
            term_counts[t] += 1
            term_domains[t] = "dedication"
            if len(term_samples[t]) < 2:
                term_samples[t].append(f"{src.capitalize()}: {pl or tid}")
        if pl:
            t = pl.strip()
            term_counts[t] += 1
            term_domains[t] = "place_name"
            if len(term_samples[t]) < 2:
                term_samples[t].append(f"{src.capitalize()}: TowerID {tid}")

    # Process Method Performances
    for bld, town, cty in mp_records:
        if bld:
            t = bld.strip()
            term_counts[t] += 1
            term_domains[t] = "dedication"
            if len(term_samples[t]) < 2:
                term_samples[t].append(f"MP: {town or 'unspecified'}")
        if town:
            t = town.strip()
            term_counts[t] += 1
            term_domains[t] = "place_name"
            if len(term_samples[t]) < 2:
                term_samples[t].append(f"MP: {town}")

    # 3. Build lexicon rows
    lexicon_rows = []
    
    # Process dedications
    ded_terms = [t for t, d in term_domains.items() if d == "dedication"]
    for raw in ded_terms:
        canon, cat, notes = expand_dedication(raw)
        if canon:
            lexicon_rows.append({
                "domain": "dedication",
                "raw_term": raw,
                "canonical_term": canon,
                "category": cat,
                "evidence_count": term_counts[raw],
                "source_examples": "; ".join(term_samples[raw]),
                "notes": notes or "Standard dedication"
            })

    # Process place names
    place_terms = [t for t, d in term_domains.items() if d == "place_name"]
    for raw in place_terms:
        canon, cat, notes = expand_place_name(raw)
        if canon:
            lexicon_rows.append({
                "domain": "place_name",
                "raw_term": raw,
                "canonical_term": canon,
                "category": cat,
                "evidence_count": term_counts[raw],
                "source_examples": "; ".join(term_samples[raw]),
                "notes": notes or "Standard place name"
            })

    # Add canonical saint spelling cross-reference entries
    for var, canon in SAINT_SPELLING_VARIANTS.items():
        lexicon_rows.append({
            "domain": "saint_name",
            "raw_term": var,
            "canonical_term": canon,
            "category": "spelling_variant",
            "evidence_count": term_counts.get(var, 0) + 1,
            "source_examples": "Canonical Hagiographical Lexicon",
            "notes": f"Historical English orthographic variation of {canon}"
        })

    # Sort rows by domain, then evidence_count desc, then raw_term
    lexicon_rows.sort(key=lambda x: (x["domain"], -x["evidence_count"], x["raw_term"]))

    # 4. Write CSV
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["domain", "raw_term", "canonical_term", "category", "evidence_count", "source_examples", "notes"]
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(lexicon_rows)

    print(f"Wrote {len(lexicon_rows):,} canonical lexicon mappings to {out_path} ({out_path.stat().st_size / 1024:.1f} KB)")
    
    # Summary statistics
    cat_counts = collections.Counter(r["category"] for r in lexicon_rows)
    dom_counts = collections.Counter(r["domain"] for r in lexicon_rows)
    print("\nLexicon Breakdown:")
    for dom, cnt in dom_counts.items():
        print(f"  Domain '{dom}': {cnt:,} entries")
    print("\nCategory Breakdown:")
    for cat, cnt in cat_counts.most_common():
        print(f"  Category '{cat}': {cnt:,} entries")


def main():
    parser = argparse.ArgumentParser(description="Build canonical dedication and place-name lexicon.")
    parser.add_argument("--db", default=str(DEFAULT_DB), help="SQLite database path")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="Output CSV path")
    args = parser.parse_args()

    db_path = Path(args.db)
    out_path = Path(args.out)
    build_lexicon(db_path, out_path)


if __name__ == "__main__":
    main()
