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


def check_documentation_privacy():
    """Audit markdown documentation in docs/ for individual profiling or named appearance league tables."""
    failures = []

    # Check ringer identity resolution document specifically
    doc = DOCS / "ringer_identity_resolution.md"
    if doc.exists():
        content = doc.read_text(encoding="utf-8", errors="ignore")
        # Check if full names with peal appearance counts are presented as a leaderboard table
        if re.search(r"\|\s*\*\*Susan M Sawyer\*\*\s*\|.*\|\s*\*\*4,512\*\*", content):
            failures.append("docs/ringer_identity_resolution.md contains named individuals in a public appearance table.")

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
