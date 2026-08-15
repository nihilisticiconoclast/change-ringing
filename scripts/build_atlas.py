#!/usr/bin/env python3
"""
Build the Founder Atlas — the project's first analytical output — as a single
self-contained page for GitHub Pages.

Usage:
    python scripts/build_atlas.py --db data/change-ringing.db

Writes docs/index.html: the template in scripts/templates/atlas.html with the
data inlined. One file, no external requests, no build step for a reader.

It queries a local SQLite/libSQL file, never Turso -- the atlas is derived
data, and rebuilding a published page is not worth spending a read budget on.
Point --db at the committed snapshot or at a fresh build_local_db.py replica.

The data is aggregated before it is embedded, which keeps the page near 320 KB
rather than shipping 51,451 bell rows to the browser:

  points     one row per tower: coordinates, dominant foundry tradition,
             attributed bell count, earliest attributed casting year
  timeline   surviving bells per quarter-century per tradition
  firstPeals distinct methods first rung on a ring containing each tradition's
             bells -- the join that needs all three corpora at once

Only the eight largest traditions get their own colour; the rest fold into
"Other". That is a palette constraint, not an arbitrary cut: a map is an
all-pairs form, where more than a handful of categorical hues stop being
tellable apart. The map therefore shows one tradition at a time against a
neutral ground, and the eight-colour palette is used only in the timeline,
where segments are adjacent and the validated ordering holds.
"""
import argparse
import collections
import json
import re
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from site_chrome import apply_chrome  # noqa: E402
import sqlfile  # noqa: E402

ROOT = Path(__file__).parent.parent
TEMPLATE = ROOT / "scripts" / "templates" / "atlas.html"
QUERIES = ROOT / "queries" / "atlas"
OUT = ROOT / "docs" / "index.html"
TOP_N = 8


def sql(name, index=0):
    """Load a statement from queries/atlas/.

    The SQL lives in files rather than in string literals here so that the
    recorded queries and the ones that actually build the page cannot drift
    apart -- a queries/ folder that is a copy of the real thing is worse than
    none, because it looks authoritative while going stale.

    Files may hold more than one statement, separated by ';'.

    Comments are stripped BEFORE splitting, not after. Splitting first breaks
    on any ';' inside a '--' comment and leaves the tail of a sentence sitting
    where SQL should be. That is the same mistake that broke the very first
    loader in this project (schema/001 has a semicolon inside a comment), and
    it reappeared here the moment these queries grew prose worth reading.
    """
    return sqlfile.statement(QUERIES / name, index)

year_of = lambda s: (lambda m: int(m.group()) if m else None)(
    re.search(r"(1[0-9]{3}|20[0-9]{2})", str(s or ""))
)


def build(db_path: Path) -> dict:
    conn = sqlite3.connect(db_path)
    q = lambda s, p=(): conn.execute(s, p).fetchall()

    bells = q(sql("01_bells_by_founder_group.sql"))
    if not bells:
        sys.exit(f"ERROR: no attributed bells found in {db_path}")

    top = [g for g, _ in collections.Counter(r[3] for r in bells).most_common(TOP_N)]
    idx = {g: i for i, g in enumerate(top)}
    other = len(top)

    towers = collections.defaultdict(
        lambda: {"lat": None, "lng": None, "c": collections.Counter(), "y": None}
    )
    timeline = collections.defaultdict(collections.Counter)
    for tid, lat, lng, group, cast in bells:
        t = towers[tid]
        t["lat"], t["lng"] = lat, lng
        t["c"][idx.get(group, other)] += 1
        y = year_of(cast)
        if y and 1200 <= y <= 2026:
            t["y"] = y if t["y"] is None else min(t["y"], y)
            if y >= 1400:
                timeline[(y // 25) * 25][idx.get(group, other)] += 1

    points = [
        [round(t["lat"], 3), round(t["lng"], 3),
         t["c"].most_common(1)[0][0], sum(t["c"].values()), t["y"] or 0]
        for t in towers.values()
    ]

    first_peals = q(sql("02_first_peals_by_foundry.sql"))

    meta = []
    for g in top:
        a, b_, n, tot = q(
            sql("03_foundry_group_metadata.sql", 0).replace(":group_name", "?"), (g,)
        )[0]
        home = q(
            sql("03_foundry_group_metadata.sql", 1).replace(":group_name", "?"), (g,)
        )
        meta.append({"name": g, "from": a, "to": b_, "firms": n, "bells": tot,
                     "home": home[0][0] if home else None})

    return {
        "groups": top + ["Other"],
        "meta": meta,
        "points": points,
        "timeline": [
            {"y": b, "v": [timeline[b].get(i, 0) for i in range(len(top) + 1)]}
            for b in sorted(timeline)
        ],
        "firstPeals": [[g, n] for g, n in first_peals],
        "totals": {
            "bells": len(bells),
            "towers": len(points),
            "methods": q(sql("04_corpus_totals.sql", 0))[0][0],
            "linked": q(sql("04_corpus_totals.sql", 1))[0][0],
            "unlinked": q(sql("04_corpus_totals.sql", 2))[0][0],
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=str(ROOT / "data" / "change-ringing.db"),
                    help="Local SQLite/libSQL file to read (never Turso)")
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        sys.exit(f"ERROR: {db_path} not found. Build one with scripts/build_local_db.py")

    data = build(db_path)
    html = TEMPLATE.read_text(encoding="utf-8")
    if "/*__DATA__*/" not in html:
        sys.exit(f"ERROR: {TEMPLATE} has no /*__DATA__*/ placeholder")
    html = html.replace("/*__DATA__*/", json.dumps(data, separators=(",", ":")))

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    # One nav bar and one footer for the whole site: scripts/site_chrome.py
    html = apply_chrome(html)
    out.write_text(html, encoding="utf-8")

    t = data["totals"]
    print(f"Wrote {out}  ({out.stat().st_size / 1024:.0f} KB)")
    print(f"  {t['bells']:,} attributed bells across {t['towers']:,} towers")
    print(f"  {len(data['groups']) - 1} named traditions + Other")
    print(f"  {t['linked']:,} tower-linked first-performance records")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
