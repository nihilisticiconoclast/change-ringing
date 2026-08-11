#!/usr/bin/env python3
"""
Build the Rhythm of Ringing page -- roadmap item 4, IDEAS option B.

Usage:
    python scripts/build_rhythm_page.py --db data/change-ringing.db

Writes docs/rhythm.html from scripts/templates/rhythm.html, one self-contained
file with the data inlined. Reads a local SQLite/libSQL file, never Turso.

What this page argues
---------------------
`docs/IDEAS.md` recorded, as a finding, that "September is the busiest ringing
month (12,067 performances) and nobody knows why". That is measured correctly
and interpreted wrongly, and this script is what shows it: 4,700 of those
performances fall in a single week of September 2022, and the corpus labels
them itself -- "In memoriam HM Queen Elizabeth II".

So the page is built around a correction rather than around a calendar. Three
layers, in increasing order of how much they needed the data:

  1. THE WEEK. Sunday service ringing and the Saturday peal day. Genuinely
     periodic, and the only part that behaves like a rhythm.
  2. THE DAYS THE COUNTRY RANG. 24 days carry 21% of four years of ringing.
     They are found by a statistical rule and named by the corpus's own
     footnotes -- no list of national events is hand-entered anywhere here.
  3. WHAT WAS RUNG. Two more columns -- whether the performance was tolling,
     and whether the footnote says the bells were half-muffled -- sort those
     days into celebration, remembrance, a death, and the funerals that are
     both. This is the part a calendar cannot show, and the two columns doing
     the work are the two least normalised in the schema. The same field also
     turns out to record a person's age: "99 Tolling" is ninety-nine strokes,
     one per year of life, and no table in any of the four corpora has an age
     column at all.

Everything the page asserts about counts, ranks and register membership is
computed at build time from the flags in force, including the headings and the
prose. Rebuilding with --min-ratio 6 --min-count 300 gives 18 days rather than
24 and every sentence follows; nothing about the finding is typed in.

The anomaly rule
----------------
For each day, compare its count to the MEDIAN OF THE SAME WEEKDAY within six
weeks either side. Same-weekday because Sunday is four times Wednesday, so a
plain rolling mean flags every Sunday. Median because the thing being detected
is itself an outlier and would otherwise inflate its own baseline.

A day qualifies at ratio >= 3.5 with at least 100 performances. The floor is
not cosmetic: in early 2021 ringing was suppressed by pandemic restrictions, so
baselines of 14 are common and a quiet January day can clear 3.5x on noise.
Both thresholds are exposed as flags, and NOTHING_MISSED in the output reports
what sits just below the cut, so the choice can be inspected instead of trusted.
"""
import argparse
import collections
import datetime
import json
import re
import statistics
import sys
import sqlite3
from pathlib import Path

ROOT = Path(__file__).parent.parent
TEMPLATE = ROOT / "scripts" / "templates" / "rhythm.html"
QUERIES = ROOT / "queries" / "rhythm"
OUT = ROOT / "docs" / "rhythm.html"

START = datetime.date(2021, 1, 1)
END = datetime.date(2024, 12, 31)
WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def sql(name, index=0):
    """Load one statement from queries/rhythm/.

    Comments are stripped before splitting on ';', not after -- splitting first
    breaks on any semicolon inside a '--' comment. That bug has now appeared
    three times in this project; see build_atlas.py for the other two.
    """
    text = (QUERIES / name).read_text(encoding="utf-8")
    body = "\n".join(
        line for line in text.splitlines() if not line.strip().startswith("--")
    )
    return [s.strip() for s in body.split(";") if s.strip()][index]


def remembrance_sunday(year):
    """Second Sunday in November -- the day itself, computed not looked up."""
    d = datetime.date(year, 11, 1)
    d += datetime.timedelta(days=(6 - d.weekday()) % 7)   # first Sunday
    return d + datetime.timedelta(days=7)


def build(db_path, min_ratio, min_count):
    conn = sqlite3.connect(db_path)
    rows = conn.execute(sql("01_daily_profile.sql")).fetchall()
    if not rows:
        sys.exit(f"ERROR: no performances in the window in {db_path}")

    # Index by date, filling absent days with zeros. Absent days are real
    # information -- 2021 has them, later years barely do -- and dropping them
    # would shift every baseline.
    prof = {r[0]: list(r[1:]) for r in rows}
    days = []
    d = START
    while d <= END:
        days.append(d.isoformat())
        d += datetime.timedelta(days=1)
    blank = [0] * 8
    n_of = {k: prof.get(k, blank)[0] for k in days}

    # --- footnote labels, from the corpus rather than from memory -----------
    notes = collections.defaultdict(list)
    for day, footnote, n in conn.execute(sql("02_day_footnotes.sql")):
        notes[day].append([n, footnote])

    # --- anomaly detection --------------------------------------------------
    scored = []
    for k in days:
        peers = []
        o = datetime.date.fromisoformat(k)
        for w in range(-6, 7):
            if w == 0:
                continue
            p = (o + datetime.timedelta(days=7 * w)).isoformat()
            if p in n_of:
                peers.append(n_of[p])
        if len(peers) < 6:
            continue
        base = statistics.median(peers)
        if base <= 0:
            continue
        scored.append((n_of[k] / base, k, base))
    scored.sort(reverse=True)

    events, near_miss = [], []
    for ratio, k, base in scored:
        n = n_of[k]
        rec = {
            "d": k,
            "n": n,
            "base": round(base, 1),
            "ratio": round(ratio, 1),
            "notes": [x[1] for x in notes.get(k, [])[:3]],
        }
        if ratio >= min_ratio and n >= min_count:
            events.append(rec)
        elif ratio >= min_ratio * 0.75 and len(near_miss) < 8:
            near_miss.append(rec)

    ev_days = {e["d"] for e in events}

    # --- weekday profile ----------------------------------------------------
    # Event days are excluded. A national funeral on a Monday is not evidence
    # about Mondays, and 2022-09-19 alone would put Monday above Saturday.
    wk = {w: collections.Counter() for w in WEEKDAYS}
    per_year = collections.defaultdict(collections.Counter)
    for k in days:
        if k in ev_days:
            continue
        p = prof.get(k, blank)
        w = WEEKDAYS[datetime.date.fromisoformat(k).weekday()]
        n, n_tower, n_hand, n_peal, n_quarter = p[0], p[1], p[2], p[3], p[4]
        wk[w]["n"] += n
        wk[w]["tower"] += n_tower
        wk[w]["hand"] += n_hand
        wk[w]["peal"] += n_peal
        wk[w]["quarter"] += n_quarter
        wk[w]["other"] += n - n_peal - n_quarter
        per_year[k[:4]][w] += n

    # The weekly shape has to be shown to hold year by year, not just in the
    # pooled total -- otherwise one busy year is doing all the work. It does,
    # but only once event days are removed: 2021's Saturdays beat its Sundays
    # in the raw figures purely because of Prince Philip's funeral.
    weekday_years = [
        {"y": y, "v": [per_year[y][w] for w in WEEKDAYS]}
        for y in sorted(per_year)
    ]

    # --- seasonal shape, raw and corrected ----------------------------------
    months = collections.defaultdict(lambda: collections.defaultdict(int))
    for k in days:
        y, m = k[:4], k[5:7]
        n = n_of[k]
        months[m]["raw_" + y] += n
        months[m]["raw"] += n
        if k not in ev_days:
            months[m]["net_" + y] += n
            months[m]["net"] += n

    # --- Remembrance Sunday -------------------------------------------------
    remembrance = []
    for y in range(START.year, END.year + 1):
        k = remembrance_sunday(y).isoformat()
        p = prof.get(k, blank)
        remembrance.append({"d": k, "n": p[0], "muffled": p[6],
                            "toll": p[5], "towers": p[7]})

    # --- counted tolls ------------------------------------------------------
    # "99 Tolling" is ninety-nine strokes of one bell. The number is the age of
    # the person who died, or the anniversary being marked, and it is the only
    # place in four corpora where an age appears at all.
    #
    # Anchored on purpose. An unanchored search for digits would pick up change
    # counts, stage numbers and bell numbers; "Tolling The Nine Tailors and 99
    # Years" is left out because the prose form cannot be counted reliably and a
    # rule that half-works is worse here than one that under-reaches.
    counted = collections.defaultdict(lambda: {"n": 0, "days": collections.Counter()})
    toll_pat = re.compile(r"^\s*(\d{1,3})\s+(?:half[- ]muffled\s+)?tolling\s*$", re.I)
    for method, day, n in conn.execute(sql("04_counted_tolls.sql")):
        m = toll_pat.match(method or "")
        if not m:
            continue
        k = int(m.group(1))
        counted[k]["n"] += n
        counted[k]["days"][day] += n
    tolls = sorted(
        ({"k": k, "n": v["n"],
          "day": v["days"].most_common(1)[0][0],
          "dayN": v["days"].most_common(1)[0][1],
          "spread": len(v["days"])}
         for k, v in counted.items()),
        key=lambda r: -r["n"],
    )

    totals = conn.execute(sql("03_window_totals.sql", 0)).fetchone()
    muffled_base = conn.execute(sql("03_window_totals.sql", 1)).fetchone()[0]

    return {
        "start": START.isoformat(),
        "days": [prof.get(k, blank) for k in days],
        "cols": ["n", "tower", "hand", "peal", "quarter", "toll", "muffled", "towers"],
        "events": events,
        "nearMiss": near_miss,
        "weekdays": [{"w": w, **wk[w]} for w in WEEKDAYS],
        "weekdayYears": weekday_years,
        # Calendar shading breaks, chosen from the distribution rather than by
        # eye: the median day is 46 performances and the 90th percentile is 99,
        # so a scale with its top step at 90 puts most of two years in one
        # colour and hides exactly what the section is about.
        "calBreaks": [0, 25, 40, 60, 100, 250],
        "months": [{"m": m, **months[m]} for m in sorted(months)],
        "remembrance": remembrance,
        "tolls": tolls,
        "rule": {"minRatio": min_ratio, "minCount": min_count},
        "totals": {
            "performances": totals[0],
            "days": totals[1],
            "rings": totals[2],
            "muffledBase": round(100 * muffled_base, 1),
            "eventPerformances": sum(e["n"] for e in events),
            "eventDays": len(events),
            "calendarDays": len(days),
        },
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=str(ROOT / "data" / "change-ringing.db"),
                    help="Local SQLite/libSQL file to read (never Turso)")
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--min-ratio", type=float, default=3.5,
                    help="how many times the same-weekday median counts as an event")
    ap.add_argument("--min-count", type=int, default=100,
                    help="floor on performances, so pandemic-era noise is excluded")
    args = ap.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        sys.exit(f"ERROR: {db_path} not found. Build one with scripts/build_local_db.py")

    data = build(db_path, args.min_ratio, args.min_count)
    html = TEMPLATE.read_text(encoding="utf-8")
    if "/*__DATA__*/" not in html:
        sys.exit(f"ERROR: {TEMPLATE} has no /*__DATA__*/ placeholder")
    html = html.replace("/*__DATA__*/", json.dumps(data, separators=(",", ":")))

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")

    t = data["totals"]
    print(f"Wrote {out}  ({out.stat().st_size / 1024:.0f} KB)")
    print(f"  {t['performances']:,} performances over {t['calendarDays']:,} calendar days")
    print(f"  {t['eventDays']} event days carry {t['eventPerformances']:,} "
          f"({100 * t['eventPerformances'] / t['performances']:.1f}%) of them")
    sept = next(m for m in data["months"] if m["m"] == "09")
    print(f"  September: {sept['raw']:,} raw -> {sept['net']:,} with event days removed")
    print("  NOTHING_MISSED -- the days just below the cut, for inspection:")
    for e in data["nearMiss"]:
        label = e["notes"][0][:56] if e["notes"] else "(no repeated footnote)"
        print(f"    {e['d']}  x{e['ratio']:<5} n={e['n']:<5} {label}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
