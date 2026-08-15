#!/usr/bin/env python3
"""
Build the landing page: docs/index.html.

    python scripts/build_home_page.py --local-db data/change-ringing.db

The table of contents is generated from site_chrome.PAGES, so a page added there
appears here without anyone remembering to. The headline figures are read from
the database for the same reason: the submitted version hard-coded them, and one
was already wrong (25,055 methods, against 25,066 in the corpus) before the page
had shipped. Three separate pages have now needed the same correction, so nothing
on this site states a number it did not compute.
"""
import argparse
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from site_chrome import PAGES, apply_chrome  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = Path(__file__).parent / "templates" / "home.html"
OUT = ROOT / "docs" / "index.html"


def stats(conn):
    """The four headline figures, each with the query that produced it."""
    q = lambda s: conn.execute(s).fetchone()[0]
    return [
        (q("SELECT COUNT(*) FROM performances"), "Performances", "2012–2024"),
        # The same definition the Founder Atlas uses -- a bell whose founder
        # resolves to a foundry TRADITION and which carries coordinates. A
        # looser "has any founder string" count gives 62,246 and would have
        # disagreed with the atlas by eleven thousand bells on the page linking
        # to it. queries/atlas/01 is the authority.
        (q('SELECT COUNT(*) FROM bells b JOIN founders f ON f."Name" = b."Founder" '
           'WHERE f."Group" IS NOT NULL AND b."Latitude" IS NOT NULL'),
         "Attributed bells", "mapped to a foundry"),
        (q("SELECT COUNT(*) FROM methods"), "Methods", "CCCBR library"),
        (q("SELECT COUNT(DISTINCT name) FROM performance_ringers"),
         "Ringer names", "before resolution"),
    ]


def build(db_path, out_path):
    html = TEMPLATE.read_text(encoding="utf-8")
    for marker in ("<!--/*TOC*/-->", "<!--/*STATS*/-->"):
        if marker not in html:
            sys.exit(f"ERROR: {TEMPLATE} has no {marker} placeholder")

    toc = "\n".join(
        f'      <a href="{href}" class="toc-card">\n'
        f'        <h3 class="toc-title">{label}</h3>\n'
        f'        <p class="toc-desc">{desc}</p>\n'
        f'      </a>'
        for href, label, desc in PAGES if href != "index.html"
    )

    conn = sqlite3.connect(db_path)
    rows = stats(conn)
    conn.close()
    stat_html = "\n".join(
        f'      <div class="stat-box">\n'
        f'        <span class="stat-value">{n:,}</span>\n'
        f'        <span class="stat-label">{label}</span>\n'
        f'        <span class="stat-sub">{sub}</span>\n'
        f'      </div>'
        for n, label, sub in rows
    )

    html = html.replace("<!--/*TOC*/-->", toc).replace("<!--/*STATS*/-->", stat_html)
    # dark=False: the landing page uses the shared CSS variables like the other
    # typographic pages, so the chrome should too. The submitted version passed
    # dark=True, which emits literal dark colours into a page that themes itself.
    out_path.write_text(apply_chrome(html, dark=False), encoding="utf-8")

    print(f"Wrote {out_path}  ({out_path.stat().st_size / 1024:.0f} KB)")
    for n, label, _ in rows:
        print(f"  {n:>10,}  {label}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--local-db", default=str(ROOT / "data" / "change-ringing.db"))
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()
    build(args.local_db, Path(args.out))


if __name__ == "__main__":
    main()
