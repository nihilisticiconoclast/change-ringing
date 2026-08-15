#!/usr/bin/env python3
"""
Build the Invention page -- roadmap item 8a, the first half of IDEAS option C.

Usage:
    python scripts/build_invention_page.py --db data/change-ringing.db

Writes docs/invention.html from scripts/templates/invention.html, one
self-contained file. Reads a local SQLite/libSQL file, never Turso.

Why this half of option C needs no backfill
-------------------------------------------
`docs/IDEAS.md` deferred all of option C -- "Invention and Survival" -- until the
BellBoard backfill completed. Half of that was wrong, which is why the roadmap
splits it. `method_performances` holds 30,746 dated first-performance records
spanning 1684 to 2026: when a method was first rung, where, and by which society
is complete history already in the corpus. Only the survival half needs adoption
data.

What "invention" means here, and does not
-----------------------------------------
Nothing in any of the four corpora records who devised a method. What the CCCBR
library records is the first PERFORMANCE, and in change ringing that is nearly the
same event -- a method enters the collection by being rung and named. So the page
says "first rung" throughout. A method can be worked out on paper years before a
band attempts it, and that gap is invisible here.

The four things the data turned out to say
------------------------------------------
1. A TRICKLE, THEN AN EXPLOSION. 166 methods first rung before 1900, against
   11,950 in 2000-24. The modern collection is a modern artefact.

2. THE WAR IS A HARD ZERO. 1939: 17 methods. Then 0, 3, 0, 0, 4, 0. Church bells
   were silenced in Britain from 1940, reserved as an invasion warning, and the
   collection simply stops. Not a gap in the records -- a gap in the ringing.

3. METHODS ARRIVE IN BATCHES. The largest single day is 1993-10-17 at Stow
   Bardolph, Norfolk: 562 methods first rung in one peal by one band. The second
   is 496 at Cambridge in 1983. "Invention" is not a steady trickle of individual
   ideas; it is occasionally one afternoon.

4. THE PANDEMIC INVENTED A NEW KIND OF FIRST, NOT NEW METHODS. "Ringing Room",
   the browser platform ringers moved to when towers closed, carries 1,142
   first-performance events and only 115 method debuts. It was used to achieve a
   new category of first in methods that already existed -- and the CCCBR library
   grew four event types to record it (firstKeyboardQuarterPeal,
   firstKeyboardExtent, firstInclusionInKeyboardPeal, ...InKeyboardQuarterPeal),
   1,138 events of which all but a single 2014 outlier are 2020 or later. A schema
   change legible in the data.

   The first version of this page claimed instead that a virtual tower was the
   third-largest source of new methods. That was wrong, and wrong in an instructive
   way: it counted first-performance EVENTS rather than method debuts, and
   `method_performances` holds up to fifteen event types per method. Collapsing to
   one row per method -- the record matching the method's own earliest date -- took
   the figure from 946 to 115 and removed Ringing Room from the top sixteen places
   entirely. Every place, society and batch figure on the page was inflated by the
   same bug.

And the finding that needed guarding
------------------------------------
Of methods first rung in 1975-99 -- the peak era, 7,645 of them -- only 13.1% were
rung at all in 2021-24. For methods first rung before 1900 the figure is 72-82%.
The oldest methods are the ones still in use and the 1975-99 vintage is the least
current, which is the opposite of what a naive reading of an invention curve
suggests.

That finding could have been manufactured by the schema/005 linkage, which only
resolves 74.7% of performances -- and the rows it refuses are disproportionately
SPLICED peals, exactly where rare methods appear. So both bounds are computed and
both are published: the strict set the resolver asserted, and a deliberately
over-generous set that also counts every method merely NAMED in a refused row.
1975-99 moves 13.1% -> 16.2%, pre-1900 stays above 72%, and the shape holds. A
single number there would have been indefensible.
"""
import argparse
import collections
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from site_chrome import apply_chrome  # noqa: E402

ROOT = Path(__file__).parent.parent
TEMPLATE = ROOT / "scripts" / "templates" / "invention.html"
QUERIES = ROOT / "queries" / "invention"
OUT = ROOT / "docs" / "invention.html"

ERA = 25          # years per vintage bucket in the currency chart
BATCH_MIN = 60    # methods in one day to count as a batch debut


def sql(name, index=0):
    """Load one statement from queries/invention/.

    Comments stripped before splitting on ';', not after -- splitting first breaks
    on any semicolon inside a '--' comment.
    """
    text = (QUERIES / name).read_text(encoding="utf-8")
    body = "\n".join(
        line for line in text.splitlines() if not line.strip().startswith("--")
    )
    return [s.strip() for s in body.split(";") if s.strip()][index]


def build(db_path):
    import sqlite3
    conn = sqlite3.connect(db_path)
    q = lambda s, p=(): conn.execute(s, p).fetchall()

    debuts = q(sql("01_method_debuts.sql", 0))
    if not debuts:
        sys.exit(f"ERROR: no dated first-performance records in {db_path}")
    methods_total, with_debut = q(sql("01_method_debuts.sql", 1))[0]

    # --- the curve, by year, split two ways --------------------------------
    per_year = collections.Counter()
    by_stage = collections.defaultdict(collections.Counter)
    by_class = collections.defaultdict(collections.Counter)
    for mid, title, name, stage, cls, little, debut in debuts:
        y = int(debut[:4])
        per_year[y] += 1
        by_stage[y][stage or 0] += 1
        by_class[y][cls or "Unclassified"] += 1

    years = list(range(min(per_year), max(per_year) + 1))
    # Stages worth their own colour; the rest fold into Other. Chosen by volume
    # over the whole period, not per year, so a band does not change identity as
    # the reader scrubs through time.
    top_stages = [s for s, _ in collections.Counter(
        {s: sum(by_stage[y][s] for y in years) for s in
         {k for y in years for k in by_stage[y]}}).most_common(6)]
    top_classes = [c for c, _ in collections.Counter(
        {c: sum(by_class[y][c] for y in years) for c in
         {k for y in years for k in by_class[y]}}).most_common(6)]

    def series(src, keys):
        return {
            "keys": [str(k) for k in keys] + ["Other"],
            "rows": [
                [y] + [src[y].get(k, 0) for k in keys]
                + [sum(v for k, v in src[y].items() if k not in keys)]
                for y in years
            ],
        }

    # --- one debut record per method ----------------------------------------
    # Keep only the record matching the method's own earliest date, so each method
    # is attributed to exactly one place and counted once. Without this, a method
    # with five event types at five towers counts five times and every figure in
    # the next three sections is inflated -- the first version of this page
    # reported 1,137 methods first rung in Ringing Room when the true figure is
    # lower, because it was counting events.
    debut_date = {r[0]: r[6] for r in debuts}
    best = {}
    for mid, d, et, b, t, c, s, tid in q(sql("02_debut_events.sql")):
        if debut_date.get(mid) != d:
            continue
        # Deterministic tie-break: prefer a row that names a tower, then one that
        # names a place, then the event type alphabetically.
        rank = (tid is None, t is None, et or "")
        if mid not in best or rank < best[mid][0]:
            best[mid] = (rank, {"date": d, "event": et, "building": b, "town": t,
                                "county": c, "society": s, "tower_id": tid})
    debut_rows = [v[1] for v in best.values()]

    # --- batch debuts -------------------------------------------------------
    groups = collections.defaultdict(list)
    for r in debut_rows:
        groups[(r["date"], r["building"], r["town"], r["county"], r["society"])].append(r)
    batches = sorted(
        ({"date": k[0], "building": k[1], "town": k[2], "county": k[3],
          "society": k[4], "methods": len(v)}
         for k, v in groups.items() if len(v) >= BATCH_MIN),
        key=lambda r: -r["methods"],
    )
    # How much of the whole collection arrived on a batch day. The point of the
    # section: if this share is large, an invention "rate" is a misleading idea.
    in_batches = sum(b["methods"] for b in batches)

    # --- places -------------------------------------------------------------
    places = collections.Counter()
    place_meta = collections.defaultdict(collections.Counter)
    for r in debut_rows:
        if not r["town"]:
            continue
        # County is inconsistently null in this table, so the town alone is the
        # key and the county shown is whichever non-null value that town most
        # often carries. Keying on (town, county) would list Cambridge twice.
        places[r["town"]] += 1
        if r["county"]:
            place_meta[r["town"]][r["county"]] += 1
    is_virtual = lambda s: "ringing room" in s.lower() or "stadium" in s.lower()
    top_places = [
        {"town": t, "county": (place_meta[t].most_common(1)[0][0]
                               if place_meta.get(t) else None),
         "methods": n, "virtual": is_virtual(t)}
        for t, n in places.most_common(16)
    ]

    virtual = collections.Counter()
    for r in debut_rows:
        if r["town"] and "ringing room" in r["town"].lower():
            virtual[r["date"][:4]] += 1

    societies = collections.Counter()
    for r in debut_rows:
        if r["society"]:
            societies[r["society"]] += 1

    # --- the pandemic's new category of first ------------------------------
    kb_by_year = collections.Counter()
    kb_by_type = collections.Counter()
    for et, yr, n in q(sql("02_debut_events.sql", 1)):
        kb_by_year[yr] += n
        kb_by_type[et] += n
    virtual_events, virtual_debuts = q(sql("02_debut_events.sql", 2))[0]

    # --- currency: two bounds ----------------------------------------------
    asserted = {r[0] for r in q(sql("03_currency.sql", 0))}
    sys.path.insert(0, str(ROOT / "scripts"))
    # The resolver records, for each spliced row it REFUSED, the name-keys it did
    # find. Those are unasserted, but they are still evidence a method was rung,
    # and mapping them back gives the generous bound. Uses the resolver's own
    # index so the two cannot disagree about what a key means; keys are stored
    # space-free, so the index is flattened the same way.
    import re as _re
    from resolve_performance_methods import build_indexes
    spaced, _attrs = build_indexes(conn)
    key_to_methods = {}
    for stage_index in spaced.values():
        for k, mids in stage_index.items():
            key_to_methods.setdefault(_re.sub(r"\s+", "", k), set()).update(mids)
    generous = set(asserted)
    for (cj,) in q(sql("03_currency.sql", 1)):
        for k in json.loads(cj):
            generous |= key_to_methods.get(k, set())

    era_tot = collections.Counter()
    era_strict = collections.Counter()
    era_loose = collections.Counter()
    for mid, title, name, stage, cls, little, debut in debuts:
        e = (int(debut[:4]) // ERA) * ERA
        era_tot[e] += 1
        if mid in asserted:
            era_strict[e] += 1
        if mid in generous:
            era_loose[e] += 1
    currency = [
        {"era": e, "methods": era_tot[e],
         "strict": era_strict[e], "loose": era_loose[e]}
        for e in sorted(era_tot) if era_tot[e] >= 20
    ]

    return {
        "years": years,
        "perYear": [[y, per_year[y]] for y in years],
        "byStage": series(by_stage, top_stages),
        "byClass": series(by_class, top_classes),
        "batches": batches[:14],
        "debutRows": len(debut_rows),
        "noPlace": sum(1 for r in debut_rows if not r["town"]),
        "noSociety": sum(1 for r in debut_rows if not r["society"]),
        "batchTotal": in_batches,
        "batchMin": BATCH_MIN,
        "places": top_places,
        "virtualByYear": sorted(virtual.items()),
        "virtualTotal": sum(virtual.values()),
        "keyboard": {
            "byYear": sorted(kb_by_year.items()),
            "byType": kb_by_type.most_common(),
            "total": sum(kb_by_year.values()),
            "virtualEvents": virtual_events,
            "virtualDebuts": virtual_debuts,
        },
        "societies": [[s, n] for s, n in societies.most_common(10)],
        "currency": currency,
        "era": ERA,
        "totals": {
            "methods": methods_total,
            "withDebut": with_debut,
            "dated": len(debuts),
            "earliest": min(r[6] for r in debuts),
            "latest": max(r[6] for r in debuts),
            "before1900": sum(1 for r in debuts if int(r[6][:4]) < 1900),
            "since2000": sum(1 for r in debuts if int(r[6][:4]) >= 2000),
        },
    }


def main():
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
    print(f"  {t['dated']:,} methods with a first-rung date, {t['earliest']} to {t['latest']}")
    print(f"  {t['methods'] - t['withDebut']:,} methods have no dated performance at all")
    print(f"  {t['before1900']:,} before 1900 against {t['since2000']:,} since 2000")
    print(f"  {data['debutRows']:,} debut records after collapsing to one per method")
    print(f"  {data['batchTotal']:,} first rung on a day that introduced "
          f"{data['batchMin']}+ methods at once")
    print(f"  {data['noPlace']:,} debuts name no place, {data['noSociety']:,} name no society")
    print(f"  virtual venue: {data['virtualTotal']:,} methods")
    print("  currency, strict and generous bounds:")
    for c in data["currency"]:
        print(f"    {c['era']}s  {c['methods']:6,} methods  "
              f"{100*c['strict']/c['methods']:5.1f}% - {100*c['loose']/c['methods']:5.1f}% "
              f"rung in 2021-24")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
