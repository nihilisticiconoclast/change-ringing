#!/usr/bin/env python3
"""
Build the Composition Demands page (Roadmap Item R-40 / G-11).

    python scripts/build_calling_page.py --local-db local_corpus.db

Reads CompLib compositions from local SQLite/libSQL database, analyzes calling sequences,
and writes docs/calling.html from scripts/templates/calling.html.
"""

import argparse
import json
import sqlite3
import sys
from pathlib import Path

# Add scripts directory to path for imports
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import db
from analyse_composition_demands import analyze_corpus
from site_chrome import apply_chrome

TEMPLATE = ROOT / "scripts" / "templates" / "calling.html"
OUT = ROOT / "docs" / "calling.html"
CANDIDATE_DBS = [
    Path("local_corpus.db"),
    ROOT / "local_corpus.db",
    ROOT / "data" / "change-ringing.db",
    Path("data/change-ringing.db"),
]


def resolve_db_path(cli_path=None):
    """Finds a valid local database containing the compositions table."""
    if cli_path and Path(cli_path).exists():
        return str(cli_path)

    for p in CANDIDATE_DBS:
        if p.exists():
            try:
                conn = sqlite3.connect(str(p))
                cur = conn.cursor()
                cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='compositions'")
                if cur.fetchone():
                    conn.close()
                    return str(p)
                conn.close()
            except sqlite3.Error:
                continue

    for p in CANDIDATE_DBS:
        if p.exists():
            return str(p)

    return "local_corpus.db"


def build_page(args=None):
    """Generates docs/calling.html from template and database analysis."""
    if args is None:
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument("--db", help="database path")
        parser.add_argument("--local-db", dest="local_db", help="alias for --db / local db path")
        args = parser.parse_args()

    explicit_path = getattr(args, "local_db", None) or getattr(args, "db", None)
    args.local_db = resolve_db_path(explicit_path)

    conn = db.connect(args)
    data = analyze_corpus(conn)
    conn.close()

    raw_html = TEMPLATE.read_text(encoding="utf-8")
    json_data = json.dumps(data, separators=(",", ":"))
    html_with_data = raw_html.replace("__DATA__", json_data)

    final_html = apply_chrome(html_with_data, dark=False)
    OUT.write_text(final_html, encoding="utf-8")
    print(f"Wrote {OUT} ({OUT.stat().st_size / 1024:.1f} KB)")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", help="database path")
    parser.add_argument("--local-db", dest="local_db", help="local db path")
    args = parser.parse_args()
    build_page(args=args)


if __name__ == "__main__":
    main()
