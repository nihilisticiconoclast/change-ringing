#!/usr/bin/env python3
"""
Generate and bless golden structural snapshots for all published HTML pages (R-42 / G-13).

Usage:
    python scripts/generate_golden_snapshots.py
    python scripts/generate_golden_snapshots.py --check
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import site_chrome
from page_structure import extract_structure

DOCS_DIR = ROOT / "docs"
GOLDEN_DIR = ROOT / "tests" / "golden"


def generate_snapshots(check_only: bool = False) -> int:
    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
    mismatches = []
    updated = 0

    for href, label, desc in site_chrome.PAGES:
        html_path = DOCS_DIR / href
        if not html_path.exists():
            print(f"WARNING: Registered page {href} does not exist in {DOCS_DIR}")
            continue

        raw_html = html_path.read_text(encoding="utf-8", errors="ignore")
        current_struct = extract_structure(raw_html)

        stem = href.replace(".html", "")
        golden_path = GOLDEN_DIR / f"{stem}.json"

        current_json = json.dumps(current_struct, indent=2)

        if golden_path.exists():
            saved_json = golden_path.read_text(encoding="utf-8")
            if current_json != saved_json:
                mismatches.append(href)
                if not check_only:
                    golden_path.write_text(current_json, encoding="utf-8")
                    updated += 1
        else:
            mismatches.append(f"{href} (new)")
            if not check_only:
                golden_path.write_text(current_json, encoding="utf-8")
                updated += 1

    if check_only:
        if mismatches:
            print(f"FAIL: {len(mismatches)} page structure(s) differ from golden baseline:")
            for m in mismatches:
                print(f"  - {m}")
            print("\nRun `python scripts/generate_golden_snapshots.py` to bless intentional structural updates.")
            return 1
        else:
            print(f"OK: All {len(site_chrome.PAGES)} page structures match golden snapshots.")
            return 0
    else:
        print(f"Blessed/Updated {updated} golden snapshot(s) in {GOLDEN_DIR}.")
        return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Check against golden snapshots without writing")
    args = parser.parse_args()
    return generate_snapshots(check_only=args.check)


if __name__ == "__main__":
    raise SystemExit(main())
