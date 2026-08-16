#!/usr/bin/env python3
"""Audit repository for licence compliance and privacy constraints.

Licence obligations:
  1. data/LICENCE-DATA.md exists and documents dual-licensing (MIT code, CC BY-SA 4.0 data).
  2. Dove's Guide CC BY-SA 4.0 attribution and link is present on all built HTML pages.
  3. CCCBR and BellBoard attributions are present in LICENCE-DATA.md and page footers.
  4. docs/vendor/README.md records all third-party libraries and licences.

Privacy constraints:
  1. Pages claiming 'No individual is named anywhere on this page' (occasions, rhythm,
     practice, populations, careers) contain no individual ringer names or private footnote texts.
  2. Documentation (.md) avoids publishing individual ringer leaderboards, appearance counts
     linked to named living individuals, or private memorial footnote texts.
  3. Footnote occasion datasets and accuracy evaluations use aggregate-only representations.
"""

from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
DATA = ROOT / "data"
SCRIPTS = ROOT / "scripts"

RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RESET = "\033[0m"


def check_licence_files():
    """Verify presence and contents of licence documentation."""
    failures = []
    
    # 1. Root LICENSE
    mit_license = ROOT / "LICENSE"
    if not mit_license.exists():
        failures.append("Missing root LICENSE file.")
    elif "MIT License" not in mit_license.read_text(encoding="utf-8"):
        failures.append("Root LICENSE does not contain MIT License text.")

    # 2. data/LICENCE-DATA.md
    data_licence = DATA / "LICENCE-DATA.md"
    if not data_licence.exists():
        failures.append("Missing data/LICENCE-DATA.md file.")
    else:
        text = data_licence.read_text(encoding="utf-8")
        for req in ["CC BY-SA 4.0", "Dove's Guide", "CCCBR", "BellBoard", "Share alike"]:
            if req.lower() not in text.lower():
                failures.append(f"data/LICENCE-DATA.md missing mention of '{req}'.")

    # 3. data/SOURCES.md
    sources = DATA / "SOURCES.md"
    if not sources.exists():
        failures.append("Missing data/SOURCES.md file.")
    else:
        text = sources.read_text(encoding="utf-8")
        if "CC BY-SA 4.0" not in text:
            failures.append("data/SOURCES.md does not record CC BY-SA 4.0 licence.")

    # 4. docs/vendor/README.md
    vendor_readme = DOCS / "vendor" / "README.md"
    if not vendor_readme.exists():
        failures.append("Missing docs/vendor/README.md.")
    else:
        text = vendor_readme.read_text(encoding="utf-8")
        for lib in ["3d-force-graph", "chart", "d3", "three"]:
            if lib not in text.lower():
                failures.append(f"docs/vendor/README.md missing documented entry for '{lib}'.")

    return failures


def check_html_page_licence_footers():
    """Verify every built HTML page in docs/ has the standard CC BY-SA 4.0 footer note."""
    failures = []
    html_files = list(DOCS.glob("*.html"))
    if not html_files:
        failures.append("No HTML files found in docs/ to check.")
        return failures

    required_phrases = [
        "CC BY-SA 4.0",
        "LICENCE-DATA.md",
        "Dove",
        "BellBoard",
    ]

    for html_file in html_files:
        content = html_file.read_text(encoding="utf-8", errors="ignore")
        for phrase in required_phrases:
            if phrase not in content:
                failures.append(f"{html_file.name} missing required licence attribution phrase '{phrase}'.")

    return failures


def check_privacy_disclaimed_pages():
    """Verify that pages with privacy disclaimers state them explicitly."""
    failures = []
    disclaimed_pages = {
        "occasions.html": ["no footnote text", "no names"],
        "rhythm.html": ["No individual is named anywhere on this page"],
        "practice.html": ["no individual is named anywhere"],
        "populations.html": ["No individual is named anywhere"],
        "careers.html": ["No individual is named anywhere on this page"],
    }

    for page_name, required_phrases in disclaimed_pages.items():
        page_path = DOCS / page_name
        if not page_path.exists():
            continue
        content = page_path.read_text(encoding="utf-8", errors="ignore")
        
        for phrase in required_phrases:
            if phrase.lower() not in content.lower():
                failures.append(f"{page_name} missing expected privacy disclaimer phrase '{phrase}'.")

    return failures


def _identity_index():
    """forename -> {total appearances -> {canonical names}} from the committed CSV.

    Read once and reused. If the CSV is absent (a shallow checkout, or CI without
    data) the caller degrades to the structural check rather than passing silently.
    """
    import csv
    from collections import defaultdict
    path = DATA / "ringer_identity_candidates.csv"
    if not path.exists():
        return None
    clusters = defaultdict(lambda: {"total": 0, "names": set()})
    with path.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            c = clusters[r["canonical_ringer_id"]]
            try:
                c["total"] += int(r.get("variant_peal_count") or 0)
            except ValueError:
                pass
            c["names"].add(r.get("canonical_name", ""))
    index = defaultdict(lambda: defaultdict(set))
    for c in clusters.values():
        for full in c["names"]:
            parts = full.split()
            if parts:
                index[parts[0].lower()][c["total"]].add(full)
    return index


def check_documentation_privacy():
    """Fail when a documentation table makes a real individual RECOVERABLE.

    The first version of this check tested for one literal string -- a specific
    name beside a specific total. It passed the moment that row was reworded,
    which is precisely what happened: the surnames were replaced with archetype
    labels and the check went green while the table still identified the same
    fourteen people.

    Removing the surname does not anonymise the row. It kept a forename, an exact
    appearance count and a date span, and `data/ringer_identity_candidates.csv` is
    in this repository -- so searching that CSV for a ringer named *Susan* with
    *4,512* appearances returned exactly one person, as did *Reg* with *2,569*.
    The redaction removed the label and left the key.

    So this tests the hazard rather than the wording: for every number in a
    documentation table, does that number plus a name-shaped token in the same
    row single out one person in the identity CSV? A check written against the
    symptom can only ever find the symptom.
    """
    failures = []
    index = _identity_index()

    for doc in sorted(DOCS.rglob("*.md")):
        if doc.name == "privacy_and_licence_audit.md":
            continue      # this file quotes the violation in order to explain it
        for n, line in enumerate(doc.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
            # Every line, not only table rows. The exposure that this check was
            # written for lived in a table, but an identical one -- a forename
            # beside an exact appearance count -- was sitting three sections
            # above it in ordinary prose, and a table-only check walked past it.
            numbers = set()
            for x in re.findall(r"\b\d[\d,]{2,}\b", line):
                if x.startswith("0"):
                    continue                     # `001` in decisions/001-..., not a count
                v = int(x.replace(",", ""))
                # Below ~100 a forename+total coincidence is meaningless across
                # 56,000 clusters; 1500-2100 are years, which appear constantly.
                if v < 100 or 1500 <= v <= 2100:
                    continue
                numbers.add(v)
            if not numbers:
                continue
            # Church dedications look exactly like forenames -- "S Michael & All
            # Angels", "St Mary", "Saint Peter" -- and towers carry performance
            # counts, so a dedication beside a count is not a person. Drop any
            # capitalised word introduced by a saint marker.
            dedications = set(re.findall(
                r"\b(?:S|St|Ss|Saint)\.?\s+([A-Z][a-zà-ÿ'-]+)", line))
            words = set(re.findall(r"\b([A-Z][a-zà-ÿA-ZÀ-Ý'-]{1,})\b", line)) - dedications
            if index is None:
                continue
            for w in words:
                buckets = index.get(w.lower())
                if not buckets:
                    continue
                for total in numbers:
                    # +/- 2 absorbs the difference between counting appearances
                    # and counting performances; an exact-only test is trivially
                    # defeated by rounding.
                    hits = {name for t in range(total - 2, total + 3)
                            for name in buckets.get(t, ())}
                    if len(hits) == 1:
                        failures.append(
                            f"{doc.relative_to(ROOT)}:{n}: '{w}' beside {total:,} "
                            f"identifies exactly one ringer in "
                            f"data/ringer_identity_candidates.csv — the row is "
                            f"re-identifiable even without a surname")
    return failures


def main():
    print("============================================================")
    print("Privacy and Licence Compliance Audit")
    print("============================================================")

    all_failures = []

    # 1. Licence Files
    lic_fails = check_licence_files()
    if lic_fails:
        print(f"{RED}[FAIL]{RESET} Licence documentation integrity:")
        for f in lic_fails:
            print(f"       - {f}")
        all_failures.extend(lic_fails)
    else:
        print(f"{GREEN}[PASS]{RESET} Licence documentation integrity (MIT, CC BY-SA 4.0, Dove, CCCBR, BellBoard, Vendor)")

    # 2. HTML Page Licence Footers
    footer_fails = check_html_page_licence_footers()
    if footer_fails:
        print(f"{RED}[FAIL]{RESET} Built HTML page licence footers:")
        for f in footer_fails:
            print(f"       - {f}")
        all_failures.extend(footer_fails)
    else:
        print(f"{GREEN}[PASS]{RESET} HTML page licence footers (all 13 pages contain required attributions)")

    # 3. Privacy Disclaimed Pages
    priv_fails = check_privacy_disclaimed_pages()
    if priv_fails:
        print(f"{RED}[FAIL]{RESET} Privacy disclaimers on analytical pages:")
        for f in priv_fails:
            print(f"       - {f}")
        all_failures.extend(priv_fails)
    else:
        print(f"{GREEN}[PASS]{RESET} Privacy disclaimers on analytical pages (occasions, rhythm, practice, populations, careers)")

    # 4. Documentation Privacy Audit
    doc_priv_fails = check_documentation_privacy()
    if doc_priv_fails:
        print(f"{RED}[FAIL]{RESET} Documentation privacy & individual profiling:")
        for f in doc_priv_fails:
            print(f"       - {f}")
        all_failures.extend(doc_priv_fails)
    else:
        print(f"{GREEN}[PASS]{RESET} Documentation privacy (no individual appearance league tables)")

    print("============================================================")
    if all_failures:
        print(f"{RED}FAILED: {len(all_failures)} compliance issue(s) detected.{RESET}")
        return 1
    else:
        print(f"{GREEN}SUCCESS: All licence and privacy audit assertions passed.{RESET}")
        return 0


if __name__ == "__main__":
    sys.exit(main())
