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

The hero graphic
----------------
The submitted version used a 1 MB JPEG of a bell tower with no stated origin.
This repository documents the licence of every byte of its data, so an
unattributed binary is the one thing it should not ship -- but a landing page
with no image at all was the wrong correction, and a gradient in its place was
worse than either.

So the graphic is drawn from the corpus: one plain course of Cambridge Surprise
Minor, every bell's path through 120 changes, generated here from the place
notation the CCCBR Methods Library publishes. It is the emblem of the art and it
is also a fair advertisement for the page it sits on -- a picture the data can
produce, whose provenance is a row in `methods`.

It is checkable, too. `plain_course` is verified against the library's own
published `lead_head` before the page is written, so a silent regression in
`notation.py` fails the build rather than drawing a wrong line very neatly.
"""
import argparse
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from notation import lead_rows  # noqa: E402
from site_chrome import PAGES, apply_chrome  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = Path(__file__).parent / "templates" / "home.html"
OUT = ROOT / "docs" / "index.html"

# Minor rather than Major: at six bells a plain course is 120 changes, which draws
# as a band about seven times wider than it is tall -- the shape a hero needs.
# Cambridge is the method most ringers learn first beyond Plain Bob, so the line
# is one a reader may recognise.
HERO_METHOD = "Cambridge Surprise Minor"
HERO_WORKING_BELL = 2   # drawn in bronze: the "blue line" a ringer learns
HERO_TREBLE = 1         # drawn in green: the plain hunt the treble rings


def plain_course(notation, stage):
    """Rows of the plain course, from rounds back round to rounds.

    One lead is repeated, each repetition composed through the permutation
    reached so far, until the row is rounds again.
    """
    lead = lead_rows(notation, stage)
    rounds = lead[0]
    course, cur = [rounds], rounds
    for _ in range(stage * 2):          # a plain course cannot be longer than this
        for row in lead[1:]:
            course.append([cur[int(b, 36) - 1] for b in row])
        cur = course[-1]
        if cur == rounds:
            return course, len(lead) - 1
    raise ValueError(f"{notation!r} at stage {stage} did not come back to rounds")


def course_svg(course, stage, lead_len):
    """The course as an SVG: x is time, y is the place a bell is ringing in.

    Every bell is drawn faintly; two are picked out. Colours are CSS variables,
    so the graphic follows the page into dark mode instead of needing a second
    copy of itself.
    """
    dx, dy, pad = 9.2, 20.0, 12.0
    w = pad * 2 + (len(course) - 1) * dx
    h = pad * 2 + (stage - 1) * dy

    def path(bell):
        """Where `bell` is standing at each row, as a polyline."""
        pts = []
        for i, row in enumerate(course):
            place = row.index(bell)
            pts.append(f"{pad + i * dx:.1f},{pad + place * dy:.1f}")
        return " ".join(pts)

    parts = [f'<svg viewBox="0 0 {w:.0f} {h:.0f}" role="img" '
             f'aria-label="One plain course of {HERO_METHOD}: the path of each of '
             f'{stage} bells through {len(course) - 1} changes.">']
    # Lead boundaries, behind everything.
    for i in range(0, len(course), lead_len):
        x = pad + i * dx
        parts.append(f'<line x1="{x:.1f}" y1="{pad - 6:.0f}" x2="{x:.1f}" '
                     f'y2="{h - pad + 6:.0f}" stroke="var(--rule,#CFCCC2)" '
                     f'stroke-width="1" opacity=".7"/>')
    bells = [b for b in course[0]]
    highlight = {bells[HERO_TREBLE - 1]: ("var(--bar,#2F6D53)", 2.4),
                 bells[HERO_WORKING_BELL - 1]: ("var(--bronze,#8A5F22)", 2.4)}
    for bell in bells:                       # faint bells first, picked-out on top
        if bell not in highlight:
            parts.append(f'<polyline points="{path(bell)}" fill="none" '
                         f'stroke="var(--ink-3,#7C7E78)" stroke-width="1" '
                         f'opacity=".38" stroke-linejoin="round"/>')
    for bell, (colour, width) in highlight.items():
        parts.append(f'<polyline points="{path(bell)}" fill="none" stroke="{colour}" '
                     f'stroke-width="{width}" stroke-linejoin="round" '
                     f'stroke-linecap="round"/>')
    parts.append("</svg>")
    return "\n    ".join(parts)


def hero(conn):
    """The graphic and its caption, checked against the library before use."""
    row = conn.execute(
        "SELECT title, stage, notation, lead_head FROM methods WHERE title = ?",
        (HERO_METHOD,)).fetchone()
    if row is None:
        sys.exit(f"ERROR: {HERO_METHOD} is not in the methods table")
    title, stage, notation, published_lead_head = row

    course, lead_len = plain_course(notation, stage)
    # The oracle: the library publishes the lead head, so the parse can be wrong
    # in a way that still draws. Check it rather than trust it.
    computed = "".join(course[lead_len])
    if computed != published_lead_head:
        sys.exit(f"ERROR: parsed lead head {computed} for {title} disagrees with the "
                 f"CCCBR library's published {published_lead_head}. "
                 f"Fix scripts/notation.py; do not publish the drawing.")

    changes = len(course) - 1
    leads = changes // lead_len
    key = (f'One plain course of <b>{title}</b> — {changes} changes in {leads} leads, '
           f'the path of every one of the {stage} bells. '
           f'<b class="k-work">Gold</b> is the second’s line, '
           f'<b class="k-treble">green</b> the treble’s plain hunt. '
           f'Drawn from the place notation <code>{notation}</code> published by the '
           f'CCCBR Methods Library, and checked against the library’s own lead head '
           f'({published_lead_head}) before this page was written.')
    return course_svg(course, stage, lead_len), key, title, changes


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
    markers = ("<!--/*TOC*/-->", "<!--/*STATS*/-->",
               "<!--/*COURSE*/-->", "<!--/*COURSEKEY*/-->")
    for marker in markers:
        if marker not in html:
            sys.exit(f"ERROR: {TEMPLATE} has no {marker} placeholder")

    toc = "\n".join(
        f'    <li>\n'
        f'      <a href="{href}"><span class="num">{i:02d}</span>{label}</a>\n'
        f'      <p>{desc}</p>\n'
        f'    </li>'
        for i, (href, label, desc) in enumerate(
            [p for p in PAGES if p[0] != "index.html"], start=1)
    )

    conn = sqlite3.connect(db_path)
    rows = stats(conn)
    svg, key, hero_title, hero_changes = hero(conn)
    conn.close()

    stat_html = "\n".join(
        f'    <div class="fig">\n'
        f'      <div class="n">{n:,}</div>\n'
        f'      <div class="l">{label}</div>\n'
        f'      <div class="s">{sub}</div>\n'
        f'    </div>'
        for n, label, sub in rows
    )

    for marker, value in (("<!--/*TOC*/-->", toc), ("<!--/*STATS*/-->", stat_html),
                          ("<!--/*COURSE*/-->", svg), ("<!--/*COURSEKEY*/-->", key)):
        html = html.replace(marker, value)
    # dark=False: the landing page uses the shared CSS variables like the other
    # typographic pages, so the chrome should too. The submitted version passed
    # dark=True, which emits literal dark colours into a page that themes itself.
    out_path.write_text(apply_chrome(html, dark=False), encoding="utf-8")

    print(f"Wrote {out_path}  ({out_path.stat().st_size / 1024:.0f} KB)")
    print(f"  hero: {hero_title}, {hero_changes} changes, lead head verified")
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
