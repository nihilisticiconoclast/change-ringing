#!/usr/bin/env python3
"""
Build the datasets behind the corpus dashboard, from committed files only.

    python scripts/build_dashboard_data.py                 # writes dashboard/data/*.json
    python scripts/build_dashboard_data.py --out some/dir

The dashboard (docs/dashboard.md) has three pages -- ringing activity, corpus
health, and the project itself -- and every figure on them comes from one of the
JSON files this writes. Nothing here touches the network or the database: the
inputs are data/bellboard/*.csv, data/complib/*.csv, the committed resolution
files, the Markdown in the repository and its git history. About 30 seconds.

Definitions are imported, not restated
--------------------------------------
Peal, quarter and unknown come from scripts/semantics.py through `is_peal` and
`length_class`, so a threshold cannot drift between this and the rest of the
repository. The one input semantics.py takes that this script has to supply is
the stage, and only for lengths in [5000, 5040). The repository's view reads it
from the resolved CCCBR method, which needs the Methods Library; here it is read
from the stage word in BellBoard's method name. That is the same answer
whenever the performance has a resolved method -- the resolver matched the method
by that name -- and a performance with no resolved method is left unknown here
too, exactly as v_performance_length leaves it. Two cases would make the
substitution differ: a resolved performance whose name states no stage, and one
whose name states stages either side of seven. Both are counted, and the build
fails if either is non-zero rather than publishing a figure that disagrees with
the views.

Settings: virtual ringing is separated
--------------------------------------
"Virtual" is any performance BellBoard flags `simulated-sound`, whatever its ring
type; tower bells and handbells are the rest, by TOWER_RING_TYPE. semantics.py
does not separate them yet, so `is_tower` counts virtual tower-mode ringing as
tower ringing. The count of those is published as a hazard rather than buried.

Figures the docs state are recounted, not asserted
--------------------------------------------------
An earlier draft of this script asserted the documented figures -- 293,471
performances, 22,623 unknown -- as constants. That is the same number written
down twice, and it would have failed the first time a document was corrected.
So the stated value is read from the document at run time, by pattern, and set
beside a fresh count: doc_claims.json. A pattern that no longer matches is
reported as "Not found", not as a failure, because the usual reason is that
someone fixed the sentence. What does fail the build is an internal invariant:
the stage substitution above, a setting that does not partition the corpus, a
commit author nobody has classified.

Privacy
-------
Aggregates only. Ringer names are read to count distinct ringers and are never
written; no footnote text is read at all. Towers are named, because a tower is a
building. Ringers are the repository's resolved name clusters
(data/ringer_identity_candidates.csv), not verified people.
"""
import argparse
import csv
import datetime
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

# pandas and numpy are imported inside the functions that read the corpus, so the
# pure functions here -- and tests/test_dashboard_data.py, which pins them -- run
# on a bare Python, as CI's test step does.

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from semantics import (  # noqa: E402
    PEAL_HIGH_STAGE,
    PEAL_MIN_CHANGES,
    PEAL_MIN_CHANGES_LOW_STAGE,
    PERFORMANCE_DATE_COLUMN,
    TOWER_RING_TYPE,
    is_peal,
    length_class,
)

DATA = ROOT / "data"
BB = DATA / "bellboard"
SETTINGS = ["tower", "hand", "virtual"]
csv.field_size_limit(10**9)

# ------------------------------------------------------------------ stages

STAGE_WORDS = {
    "singles": 3, "minimus": 4, "doubles": 5, "minor": 6, "triples": 7, "major": 8,
    "caters": 9, "royal": 10, "cinques": 11, "maximus": 12, "sextuples": 13,
    "fourteen": 14, "septuples": 15, "sixteen": 16, "octuples": 17, "eighteen": 18,
    "nonuples": 19, "twenty": 20, "decuples": 21, "twenty-two": 22,
}
_ANY_STAGE = re.compile(r"\b(" + "|".join(sorted(STAGE_WORDS, key=len, reverse=True)) + r")\b", re.I)
_TRAILING_PAREN = re.compile(r"\s*\([^)]*\)\s*$")

STAGE_NAMES = {3: "Singles", 4: "Minimus", 5: "Doubles", 6: "Minor", 7: "Triples", 8: "Major",
               9: "Caters", 10: "Royal", 11: "Cinques", 12: "Maximus"}
GROUP_ORDER = ["Singles", "Minimus", "Doubles", "Minor", "Triples", "Major", "Caters", "Royal",
               "Cinques", "Maximus", "13+ bells", "Mixed stages", "Stage not named",
               "Non-method ringing"]
# The repository's own labels for unlinked performances that are not methods at all.
NON_METHOD_LABELS = {"tolling", "call_changes", "rounds_and_call_changes", "general", "rounds"}


def parse_stages(method):
    """Stage(s) named in a BellBoard method string, as numbers of bells, sorted.

    The stage is conventionally the last word -- "Cambridge Surprise Minor",
    "Spliced Surprise Major (8m)" -- and "X and Y" at the end names two. Only when
    the last word is not a stage word does this fall back to every stage word in
    the string, so a method whose own name contains "Royal" or "Major" is not
    misread as two stages.
    """
    s = (method or "").strip()
    while _TRAILING_PAREN.search(s):
        s = _TRAILING_PAREN.sub("", s)
    words = re.findall(r"[A-Za-z][A-Za-z\-']*", s)
    if not words:
        return []
    m = re.search(r"\b(\w+)\s+and\s+(\w+)\s*$", s)
    if m and m.group(1).lower() in STAGE_WORDS and m.group(2).lower() in STAGE_WORDS:
        return sorted({STAGE_WORDS[m.group(1).lower()], STAGE_WORDS[m.group(2).lower()]})
    if words[-1].lower() in STAGE_WORDS:
        return [STAGE_WORDS[words[-1].lower()]]
    return sorted({STAGE_WORDS[w.lower()] for w in _ANY_STAGE.findall(s)})


def stage_group(label, stages):
    """The stage-mix bucket for one performance."""
    if label in NON_METHOD_LABELS:
        return "Non-method ringing"
    if not stages:
        return "Stage not named"
    if len(stages) > 1:
        return "Mixed stages"
    s = stages[0]
    return STAGE_NAMES.get(s, "13+ bells" if s >= 13 else "Stage not named")


def stage_for_rule(changes, linked, stages):
    """The stage to hand semantics.is_peal, and whether the substitution is safe.

    Returns (stage, problem). Outside [5000, 5040) the stage cannot change the
    answer and None is passed. Inside it, an unlinked performance is unknown in
    the views, so None again; a linked one needs a stage word, and its stages must
    all sit on one side of PEAL_HIGH_STAGE. `problem` names any case where the
    substitution could disagree with v_performance_length.
    """
    if changes is None or not (PEAL_MIN_CHANGES <= changes < PEAL_MIN_CHANGES_LOW_STAGE):
        return None, None
    if not linked:
        return None, None
    if not stages:
        return None, "resolved, but the name states no stage"
    if min(stages) < PEAL_HIGH_STAGE <= max(stages):
        return None, "resolved, but the name states stages either side of the peal threshold"
    return stages[0], None


# ------------------------------------------------------------------ number words

_UNITS = {w: i for i, w in enumerate(
    "zero one two three four five six seven eight nine ten eleven twelve thirteen "
    "fourteen fifteen sixteen seventeen eighteen nineteen".split())}
_TENS = {w: 10 * i for i, w in enumerate(
    "_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()) if w != "_"}


def words_to_int(text):
    """'Thirteen' -> 13, 'twenty-three' -> 23, '1,234' -> 1234. None if neither."""
    t = text.strip().lower()
    if re.fullmatch(r"[\d,]+", t):
        return int(t.replace(",", ""))
    total = 0
    for part in t.replace("-", " ").split():
        if part in _UNITS:
            total += _UNITS[part]
        elif part in _TENS:
            total += _TENS[part]
        else:
            return None
    return total


# ------------------------------------------------------------------ doc claims

def find_claim(text, pattern, group=1, flags=0):
    """(stated value, 1-based line, the matched sentence) or (None, None, None)."""
    m = re.search(pattern, text, flags)
    if not m:
        return None, None, None
    raw = m.group(group)
    value = float(raw) if re.fullmatch(r"\d+\.\d+", raw) else words_to_int(raw)
    quote = " ".join(re.sub(r"\*\*|`", "", m.group(0)).split())
    return value, text.count("\n", 0, m.start()) + 1, quote


# ------------------------------------------------------------------ helpers

def _clean(v):
    import numpy as np
    if v is None:
        return None
    if isinstance(v, np.bool_):
        return bool(v)
    if isinstance(v, np.integer):
        return int(v)
    if isinstance(v, (np.floating, float)):
        return None if np.isnan(v) else float(v)
    return v


def ratio(a, b):
    return None if not b else a / b


def pct_change(cur, prev):
    return None if prev in (None, 0) or cur is None else (cur - prev) / prev


def prev_year(y, years):
    return None if y == "all" or y == years[0] else str(int(y) - 1)


def load_bellboard(kind, usecols=None):
    import pandas as pd
    files = sorted(BB.glob(f"{kind}_*.csv"))
    if not files:
        raise SystemExit(f"no {kind}_*.csv under {BB.relative_to(ROOT)}")
    return pd.concat([pd.read_csv(f, dtype=str, keep_default_na=False, usecols=usecols)
                      for f in files], ignore_index=True)


def count_rows(path):
    with path.open(newline="", encoding="utf-8") as fh:
        return sum(1 for _ in csv.reader(fh)) - 1


def git(*args):
    return subprocess.run(["git", "-C", str(ROOT), *args], check=True,
                          capture_output=True, text=True).stdout


# ------------------------------------------------------------------ the build

def build(out):
    import numpy as np
    import pandas as pd

    out.mkdir(parents=True, exist_ok=True)
    problems = []
    written = {}

    def write(name, rows):
        rows = [{k: _clean(v) for k, v in r.items()} for r in rows]
        path = out / f"{name}.json"
        path.write_text(json.dumps(rows, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        written[name] = len(rows)
        print(f"  {name}: {len(rows):,} rows")
        return rows

    def add_change(rows):
        for r in rows:
            pv = r.get("performances_prev")
            r["performances_change"] = pct_change(r["performances"], pv) if pv else None
        return rows

    # -------------------------------------------------------------- performances
    print("reading the committed corpus")
    perf = load_bellboard("performances")
    flags = load_bellboard("flags")
    ringers = load_bellboard("ringers", ["perf_id", "name"])
    footnote_ids = load_bellboard("footnotes", ["perf_id"])
    n = len(perf)

    perf["year"] = perf[PERFORMANCE_DATE_COLUMN].str[:4]
    perf["month"] = perf[PERFORMANCE_DATE_COLUMN].str[:7]
    perf["ch"] = pd.to_numeric(perf.changes, errors="coerce")
    years = sorted(perf.year.unique())

    unlinked = pd.read_csv(DATA / "regional_traditions_classified.csv", dtype=str, keep_default_na=False)
    unlinked_label = dict(zip(unlinked.perf_id, unlinked.label))
    if not set(unlinked_label) <= set(perf.perf_id):
        problems.append("regional_traditions_classified.csv names performances the corpus does not hold")
    perf["unres_label"] = perf.perf_id.map(unlinked_label)
    perf["linked"] = perf.unres_label.isna()

    stage_cache = {m: parse_stages(m) for m in perf.method.unique()}
    perf["stages"] = perf.method.map(stage_cache)

    classes, substitution = [], Counter()
    for c, lk, st in zip(perf.ch.to_numpy(), perf.linked.to_numpy(), perf.stages.to_list()):
        c = None if np.isnan(c) else int(c)
        stage, problem = stage_for_rule(c, lk, st)
        if problem:
            substitution[problem] += 1
        classes.append(length_class(c, stage) or "unknown")
    perf["length_class"] = classes
    for problem, k in substitution.items():
        problems.append(f"{k:,} performances in [{PEAL_MIN_CHANGES}, {PEAL_MIN_CHANGES_LOW_STAGE}) "
                        f"are {problem}; the stage read from the name could disagree with the views")

    simulated = set(flags.loc[flags.flag_type == "simulated-sound", "perf_id"])
    perf["virtual"] = perf.perf_id.isin(simulated)
    perf["setting"] = np.where(perf.virtual, "virtual",
                               np.where(perf.ring_type == TOWER_RING_TYPE, "tower", "hand"))
    if perf.setting.value_counts().sum() != n:
        problems.append("the three settings do not partition the corpus")
    perf["stage_group"] = [stage_group(lab if isinstance(lab, str) else None, st)
                           for lab, st in zip(perf.unres_label, perf.stages)]
    window = (perf.ch >= PEAL_MIN_CHANGES) & (perf.ch < PEAL_MIN_CHANGES_LOW_STAGE)

    # ringers: resolved clusters, names never written out
    ids = pd.read_csv(DATA / "ringer_identity_candidates.csv", dtype=str, keep_default_na=False,
                      usecols=["raw_name", "canonical_ringer_id"])
    name_to_cluster = dict(zip(ids.raw_name, ids.canonical_ringer_id))
    rg = ringers[ringers.name != ""].drop_duplicates(["perf_id", "name"]).copy()
    rg["rid"] = rg.name.map(name_to_cluster)
    unmapped = int(rg.rid.isna().sum())
    rg["rid"] = rg.rid.fillna("raw:" + rg.name)
    rg = rg.merge(perf[["perf_id", "year", "setting"]], on="perf_id", how="inner")
    print(f"  {len(rg):,} ringer appearances; {unmapped:,} carry a name the identity file lacks "
          f"and count as their own cluster")

    firsts = flags[flags.flag_type.isin(["first-quarter", "first-peal"])].merge(
        perf[["perf_id", "year", "setting"]], on="perf_id")

    def subsets():
        for y in years + ["all"]:
            ym = np.ones(n, bool) if y == "all" else (perf.year == y).to_numpy()
            for s in ["all"] + SETTINGS:
                sm = np.ones(n, bool) if s == "all" else (perf.setting == s).to_numpy()
                yield y, s, ym & sm

    def mask(frame, y, s):
        m = np.ones(len(frame), bool)
        if y != "all":
            m &= (frame.year == y).to_numpy()
        if s != "all":
            m &= (frame.setting == s).to_numpy()
        return m

    print("writing")
    # ================================================================ activity
    rows, base = [], {}
    for y, s, m in subsets():
        p = perf[m]
        cls = p.length_class.value_counts()
        rm = mask(rg, y, s)
        ff = firsts[mask(firsts, y, s)].flag_type.value_counts()
        known = len(p) - int(cls.get("unknown", 0))
        rec = {
            "key": f"{y}|{s}", "year": y, "setting": s,
            "performances": len(p),
            "peals": int(cls.get("peal", 0)), "quarters": int(cls.get("quarter", 0)),
            "short": int(cls.get("short", 0)), "unknown_length": int(cls.get("unknown", 0)),
            "peal_share": ratio(int(cls.get("peal", 0)), known),
            "unknown_share": ratio(int(cls.get("unknown", 0)), len(p)),
            "ringers": int(rg[rm].rid.nunique()),
            "ringer_appearances": int(rm.sum()),
            "first_quarters": int(ff.get("first-quarter", 0)),
            "first_peals": int(ff.get("first-peal", 0)),
        }
        base[(y, s)] = rec
        rows.append(rec)
    for rec in rows:
        py = prev_year(rec["year"], years)
        prev = base.get((py, rec["setting"])) if py else None
        for k in ["performances", "peals", "quarters", "ringers", "first_quarters", "first_peals"]:
            rec[k + "_prev"] = prev[k] if prev else None
            rec[k + "_change"] = pct_change(rec[k], prev[k]) if prev else None
    write("activity_yearly", rows)

    tower_bell = perf[(perf.setting == "tower") & (perf.dove_tower_id != "")]
    towers = {y: int((tower_bell if y == "all" else tower_bell[tower_bell.year == y]).dove_tower_id.nunique())
              for y in years + ["all"]}
    rows = []
    for y in years + ["all"]:
        py = prev_year(y, years)
        rows.append({"year": y, "towers": towers[y], "towers_prev": towers.get(py) if py else None,
                     "towers_change": pct_change(towers[y], towers[py]) if py else None})
    write("towers_yearly", rows)

    g = perf.groupby(["month", "setting"])
    monthly = g.size().rename("performances").to_frame()
    monthly["peals"] = g.length_class.apply(lambda x: int((x == "peal").sum()))
    monthly["quarters"] = g.length_class.apply(lambda x: int((x == "quarter").sum()))
    rows = []
    for month in sorted(perf.month.unique()):
        for s in SETTINGS:
            r = monthly.loc[(month, s)] if (month, s) in monthly.index else None
            rows.append({"key": f"{month}|{s}", "month": month, "year": month[:4], "setting": s,
                         "performances": int(r.performances) if r is not None else 0,
                         "peals": int(r.peals) if r is not None else 0,
                         "quarters": int(r.quarters) if r is not None else 0})
    write("activity_monthly", rows)

    rows, counts = [], {}
    for y, s, m in subsets():
        p = perf[m]
        grp = p.groupby("stage_group").length_class.value_counts().unstack(fill_value=0)
        for name in GROUP_ORDER:
            k = int(grp.loc[name].sum()) if name in grp.index else 0
            counts[(y, s, name)] = k
            rows.append({"key": f"{y}|{s}|{name}", "year": y, "setting": s, "stage_group": name,
                         "order": GROUP_ORDER.index(name), "performances": k,
                         "peals": int(grp.loc[name].get("peal", 0)) if name in grp.index else 0,
                         "quarters": int(grp.loc[name].get("quarter", 0)) if name in grp.index else 0,
                         "share": ratio(k, len(p))})
    for r in rows:
        py = prev_year(r["year"], years)
        r["performances_prev"] = counts.get((py, r["setting"], r["stage_group"])) if py else None
    write("stage_mix", add_change(rows))

    is_method = ~perf.unres_label.isin(NON_METHOD_LABELS).to_numpy()
    totals = {(y, s): int(m.sum()) for y, s, m in subsets()}
    by_method = {(y, s): perf[m & is_method].groupby("method").length_class.value_counts().unstack(fill_value=0)
                 for y, s, m in subsets()}
    rows = []
    for (y, s), t in by_method.items():
        t = t.copy()
        t["performances"] = t.sum(axis=1)
        t = t.reset_index().sort_values(["performances", "method"], ascending=[False, True]).head(100)
        py = prev_year(y, years)
        prev = by_method.get((py, s)) if py else None
        for rank, r in enumerate(t.itertuples(index=False), 1):
            pv = None
            if prev is not None:
                pv = int(prev.loc[r.method].sum()) if r.method in prev.index else 0
            rows.append({"key": f"{y}|{s}|{r.method}", "year": y, "setting": s, "rank": rank,
                         "method": r.method, "stage_group": stage_group(None, stage_cache[r.method]),
                         "performances": int(r.performances),
                         "peals": int(getattr(r, "peal", 0)), "quarters": int(getattr(r, "quarter", 0)),
                         "share": ratio(int(r.performances), totals[(y, s)]),
                         "performances_prev": pv})
    write("top_methods", add_change(rows))

    label = (tower_bell.groupby(["dove_tower_id", "place", "dedication", "county"]).size()
             .reset_index(name="k").sort_values(["dove_tower_id", "k"], ascending=[True, False])
             .drop_duplicates("dove_tower_id").set_index("dove_tower_id"))
    tower_totals = {y: int(((perf.setting == "tower") & ((perf.year == y) if y != "all" else True)).sum())
                    for y in years + ["all"]}
    by_tower = {y: (tower_bell if y == "all" else tower_bell[tower_bell.year == y])
                .groupby("dove_tower_id").length_class.value_counts().unstack(fill_value=0)
                for y in years + ["all"]}
    rows = []
    for y in years + ["all"]:
        t = by_tower[y].copy()
        t["performances"] = t.sum(axis=1)
        t = t.reset_index().sort_values(["performances", "dove_tower_id"], ascending=[False, True]).head(100)
        py = prev_year(y, years)
        for rank, r in enumerate(t.itertuples(index=False), 1):
            tid = r.dove_tower_id
            pv = (int(by_tower[py].loc[tid].sum()) if tid in by_tower[py].index else 0) if py else None
            lab = label.loc[tid]
            rows.append({"key": f"{y}|{tid}", "year": y, "rank": rank, "dove_tower_id": tid,
                         "place": lab.place, "dedication": lab.dedication, "county": lab.county,
                         "performances": int(r.performances),
                         "peals": int(getattr(r, "peal", 0)), "quarters": int(getattr(r, "quarter", 0)),
                         "share": ratio(int(r.performances), tower_totals[y]),
                         "performances_prev": pv})
    write("top_towers", add_change(rows))

    by_county = {(y, s): perf[m & (perf.county != "").to_numpy()].county.value_counts()
                 for y, s, m in subsets()}
    rows = []
    for (y, s), vc in by_county.items():
        py = prev_year(y, years)
        for rank, (county, k) in enumerate(vc.sort_values(ascending=False).head(20).items(), 1):
            rows.append({"key": f"{y}|{s}|{county}", "year": y, "setting": s, "rank": rank,
                         "county": county, "performances": int(k), "share": ratio(int(k), totals[(y, s)]),
                         "performances_prev": int(by_county[(py, s)].get(county, 0)) if py else None})
    write("counties", add_change(rows))

    # ================================================================ health
    licence = (DATA / "LICENCE-DATA.md").read_text(encoding="utf-8")
    snap = re.search(r"Snapshot built (\d{4}-\d{2}-\d{2}): ([\d,]+) ringing towers, ([\d,]+) bells, "
                     r"([\d,]+) methods,\s+([\d,]+) first-performance records", licence)
    stated = {}
    if snap:
        stated = {"date": snap.group(1), "towers": words_to_int(snap.group(2)),
                  "bells": words_to_int(snap.group(3)), "methods": words_to_int(snap.group(4)),
                  "events": words_to_int(snap.group(5))}
    stated_source = (f"data/LICENCE-DATA.md (snapshot {stated['date']})" if stated
                     else "data/LICENCE-DATA.md: snapshot sentence not found")
    complib_n = count_rows(DATA / "complib" / "compositions.csv")
    complib_m = count_rows(DATA / "complib" / "composition_methods.csv")
    counted = "Counted here"
    said = "Stated in the repo"
    write("corpus_tables", [
        {"key": "bb_performances", "corpus": "BellBoard", "table": "Performances", "rows": n,
         "basis": counted, "source": "data/bellboard/performances_*.csv"},
        {"key": "bb_ringers", "corpus": "BellBoard", "table": "Ringer rows", "rows": len(ringers),
         "basis": counted, "source": "data/bellboard/ringers_*.csv"},
        {"key": "bb_footnotes", "corpus": "BellBoard", "table": "Footnotes", "rows": len(footnote_ids),
         "basis": counted, "source": "data/bellboard/footnotes_*.csv"},
        {"key": "bb_flags", "corpus": "BellBoard", "table": "Flags", "rows": len(flags),
         "basis": counted, "source": "data/bellboard/flags_*.csv"},
        {"key": "complib_compositions", "corpus": "CompLib", "table": "Compositions", "rows": complib_n,
         "basis": counted, "source": "data/complib/compositions.csv"},
        {"key": "complib_methods", "corpus": "CompLib", "table": "Composition method rows", "rows": complib_m,
         "basis": counted, "source": "data/complib/composition_methods.csv"},
        {"key": "identity_names", "corpus": "Ringer identity", "table": "Raw ringer names",
         "rows": ids.raw_name.nunique(), "basis": counted, "source": "data/ringer_identity_candidates.csv"},
        {"key": "identity_clusters", "corpus": "Ringer identity", "table": "Resolved name clusters",
         "rows": ids.canonical_ringer_id.nunique(), "basis": counted, "source": "data/ringer_identity_candidates.csv"},
        {"key": "cccbr_methods", "corpus": "CCCBR Methods Library", "table": "Methods",
         "rows": stated.get("methods"), "basis": said, "source": stated_source},
        {"key": "cccbr_events", "corpus": "CCCBR Methods Library", "table": "First-performance events",
         "rows": stated.get("events"), "basis": said, "source": stated_source},
        {"key": "dove_towers", "corpus": "Dove's Guide", "table": "Ringing towers",
         "rows": stated.get("towers"), "basis": said, "source": stated_source},
        {"key": "dove_bells", "corpus": "Dove's Guide", "table": "Bells",
         "rows": stated.get("bells"), "basis": said, "source": stated_source},
    ])

    # Per-year counts against data/SOURCES.md and its search.php re-check.
    documented = {}
    for line in (DATA / "SOURCES.md").read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\s*\|\s*(20\d\d)\s*\|\s*([\d,]+)\s*\|\s*([\d,]+)\s*\|\s*([\d,]+)\s*\|"
                     r"\s*([\d,]+)\s*\|\s*(.*?)\s*\|\s*$", line)
        if m:
            documented[m.group(1)] = {
                "performances": words_to_int(m.group(2)), "ringers": words_to_int(m.group(3)),
                "footnotes": words_to_int(m.group(4)), "flags": words_to_int(m.group(5)),
                "recheck": m.group(6).replace("*", "")}
    per_year = {
        "performances": perf.year.value_counts(),
        "ringers": ringers.merge(perf[["perf_id", "year"]], on="perf_id").year.value_counts(),
        "footnotes": footnote_ids.merge(perf[["perf_id", "year"]], on="perf_id").year.value_counts(),
        "flags": flags.merge(perf[["perf_id", "year"]], on="perf_id").year.value_counts(),
    }
    rows, table_figures, table_matches = [], 0, 0
    for y in years:
        cnt = {k: int(v.get(y, 0)) for k, v in per_year.items()}
        d = documented.get(y)
        if d:
            table_figures += 4
            table_matches += sum(cnt[k] == d[k] for k in cnt)
        short = re.search(r"short by (\d+)", d["recheck"]) if d else None
        gap = int(short.group(1)) if short else 0
        rows.append({"year": y, "performances": cnt["performances"], "ringer_rows": cnt["ringers"],
                     "footnotes": cnt["footnotes"], "flags": cnt["flags"],
                     "matches_sources_md": bool(d) and all(cnt[k] == d[k] for k in cnt),
                     "bellboard_count": cnt["performances"] + gap if d else None, "gap": gap if d else None,
                     "status": ("Exact" if gap == 0 else f"Short by {gap}") if d else "Not in SOURCES.md",
                     "rechecked": "2026-08-15" if d else None})
    write("completeness_by_year", rows)

    bridge = pd.read_csv(DATA / "composer_bridge_candidates.csv", dtype=str, keep_default_na=False)
    perf["bridge"] = perf.composer.map(dict(zip(bridge.performance_credit, bridge.status)))
    fields = [
        ("length", "Length (changes)", perf.ch.notna()),
        ("decidable", "Peal or quarter decidable", perf.length_class != "unknown"),
        ("dove", "Dove tower ID", perf.dove_tower_id != ""),
        ("towerbase", "TowerBase ID", perf["towerbase-id"] != ""),
        ("method", "Method linked to the CCCBR library", perf.linked),
        ("composer", "Composer credit", perf.composer != ""),
        ("bridge", "Composer bridged to CompLib", perf.bridge == "resolved"),
        ("association", "Association", perf.association != ""),
        ("county", "County", perf.county != ""),
        ("composition", "Composition", perf.composition != ""),
    ]
    rows = []
    for y in years + ["all"]:
        ym = np.ones(n, bool) if y == "all" else (perf.year == y).to_numpy()
        for order, (fid, name, has) in enumerate(fields):
            k = int((has.to_numpy() & ym).sum())
            rows.append({"key": f"{y}|{fid}", "year": y, "field_id": fid, "field": name, "order": order,
                         "populated": k, "performances": int(ym.sum()), "share": ratio(k, int(ym.sum()))})
    write("field_coverage", rows)

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    notation_rate, _, _ = find_claim(readme, r"\*\*([\d.]+)% of the ([\d,]+) method rows\*\*")
    accepted = pd.read_csv(DATA / "method_location_adjudication.csv", dtype=str, keep_default_na=False)
    location_linked = int(pd.to_numeric(accepted.occurrences[accepted.decision == "accept"]).sum())
    tb_all = int((perf.setting == "tower").sum())
    tb_linked = int(((perf.setting == "tower") & (perf.dove_tower_id != "")).sum())
    resolved = int((perf.bridge == "resolved").sum())
    credited = int((perf.composer != "").sum())
    with_composition = int((perf.composition != "").sum())
    write("linkages", [
        {"key": "tower", "linkage": "Tower-bell performance → Dove tower", "linked": tb_linked, "of": tb_all,
         "rate": ratio(tb_linked, tb_all), "basis": counted,
         "note": "BellBoard publishes dove-tower-id, so this is an integer join, not a name match."},
        {"key": "method", "linkage": "Performance → CCCBR method", "linked": int(perf.linked.sum()), "of": n,
         "rate": ratio(int(perf.linked.sum()), n), "basis": counted,
         "note": "Unlinked performances are the repo's own list in data/regional_traditions_classified.csv."},
        {"key": "composer", "linkage": "Composer credit → CompLib composer", "linked": resolved, "of": credited,
         "rate": ratio(resolved, credited), "basis": counted,
         "note": "Precision 99.80% where checkable, as measured in docs/composer_bridge.md."},
        {"key": "composition", "linkage": "Performance → CompLib composition", "linked": with_composition, "of": n,
         "rate": ratio(with_composition, n), "basis": counted,
         "note": "BellBoard never fills the composition field, so this join cannot be made."},
        {"key": "location", "linkage": "Method first performance → Dove tower", "linked": location_linked,
         "of": stated.get("events"), "rate": ratio(location_linked, stated.get("events")),
         "basis": "Counted here; total stated",
         "note": "Accepted decisions in data/method_location_adjudication.csv; the total needs the Methods Library."},
        {"key": "notation", "linkage": "CompLib method row → CCCBR method, by place notation", "linked": None,
         "of": complib_m, "rate": notation_rate / 100 if notation_rate is not None else None, "basis": said,
         "note": "Measured offline in README.md; needs the Methods Library, which this build does not load."},
        {"key": "identity", "linkage": "Raw ringer name → resolved cluster", "linked": ids.canonical_ringer_id.nunique(),
         "of": ids.raw_name.nunique(), "rate": None, "basis": counted,
         "note": "Names collapse into clusters; whether the clusters are right is not yet measured (R-9)."},
    ])

    names = {"multiple_methods": ("Several methods named", "Method text"),
             "unclassified": ("Unclassified", "Method text"),
             "tolling": ("Tolling", "Not a method"),
             "call_changes": ("Call changes", "Not a method"),
             "rounds_and_call_changes": ("Rounds and call changes", "Not a method"),
             "general": ("General ringing", "Not a method"),
             "rounds": ("Rounds", "Not a method")}
    vc = unlinked.label.value_counts()
    unknown_labels = set(vc.index) - set(names)
    if unknown_labels:
        problems.append(f"unlinked labels with no display name: {sorted(unknown_labels)}")
    write("unresolved_methods", [
        {"label": k, "name": names[k][0], "kind": names[k][1], "performances": int(vc.get(k, 0)),
         "share_of_unlinked": ratio(int(vc.get(k, 0)), len(unlinked)), "share_of_all": ratio(int(vc.get(k, 0)), n)}
        for k in sorted(names, key=lambda k: -int(vc.get(k, 0)))])

    bulk_days = perf.bb_timestamp.str[:10].value_counts()
    bulk_days = bulk_days[bulk_days > 2000]
    bulk_rows = int(perf.bb_timestamp.str[:10].isin(bulk_days.index).sum())
    no_length = int(perf.ch.isna().sum())
    window_unlinked = int((window & ~perf.linked).sum())
    boundary = int((perf.ch == PEAL_MIN_CHANGES).sum())
    hand = int((perf.ring_type != TOWER_RING_TYPE).sum())
    initials = int((perf.bridge == "initialism").sum())
    virtual_tower = int((perf.virtual & (perf.ring_type == TOWER_RING_TYPE)).sum())
    write("hazards", [
        {"key": "bulk", "hazard": "bb_timestamp sits on bulk-import days", "rows": bulk_rows,
         "share": ratio(bulk_rows, n), "state": "Handled",
         "handling": "semantics.py names perf_date as the only date column that means what it says."},
        {"key": "nolength", "hazard": "No recorded length", "rows": no_length, "share": ratio(no_length, n),
         "state": "Handled",
         "handling": "is_peal is NULL, not false, so a denominator cannot quietly keep them."},
        {"key": "window", "hazard": "5,000–5,039 changes with no resolved method", "rows": window_unlinked,
         "share": ratio(window_unlinked, n), "state": "Handled",
         "handling": "NULL: a peal at 7+ bells and not at 5–6, and the stage is unknown."},
        {"key": "boundary", "hazard": "Exactly 5,000 changes", "rows": boundary, "share": ratio(boundary, n),
         "state": "Handled",
         "handling": "PEAL_MIN_CHANGES is inclusive; the old > spelling dropped these from a published finding."},
        {"key": "hand", "hazard": "Handbell performances in tower counts", "rows": hand, "share": ratio(hand, n),
         "state": "Handled", "handling": "TOWER_RING_TYPE separates them from tower counts."},
        {"key": "initials", "hazard": "Composer credited by initials only", "rows": initials,
         "share": ratio(initials, n), "state": "Handled",
         "handling": "Left unresolved on purpose: expanding initials is a guess."},
        {"key": "virtual", "hazard": 'Virtual ringing recorded with ring type "tower"', "rows": virtual_tower,
         "share": ratio(virtual_tower, n), "state": "Open",
         "handling": "Not in semantics.py: is_tower counts them as tower ringing. Separated on the dashboard."},
    ])

    # ================================================================ project
    # A shallow clone -- CI's default, and how agent sessions usually clone -- holds
    # one commit and would publish a project history of a single day.
    if git("rev-parse", "--is-shallow-repository").strip() == "true":
        problems.append("this is a shallow clone, so the commit history is incomplete; "
                        "run `git fetch --unshallow` (or a deep `--depth`) first")
    head = git("log", "-1", "--format=%h|%ad|%s", "--date=short").strip().split("|", 2)
    total_commits = int(git("rev-list", "--count", "HEAD").strip())
    who = {"Claude": "Claude Code", "Gemini Code Assist": "Gemini", "Gemini CLI": "Gemini",
           "James Boulton": "James", "nihilisticiconoclast": "James",
           "Vibe Nuage Agent": "Mistral Vibe", "Mistral Vibe": "Mistral Vibe"}
    log = [line.split("|", 1) for line in git("log", "--format=%ad|%an", "--date=short").strip().splitlines()]
    strangers = sorted({a for _, a in log if a not in who})
    if strangers:
        problems.append(f"commit authors with no contributor group: {strangers}")
    per_day = Counter((d, who.get(a, a)) for d, a in log)
    write("commits_daily", [{"key": f"{d}|{w}", "day": d, "contributor": w, "commits": c}
                            for (d, w), c in sorted(per_day.items())])
    if sum(per_day.values()) != total_commits:
        problems.append("commit history counted twice or not at all: the daily totals miss rev-list")
    write("snapshot", [{"repo": "nihilisticiconoclast/change-ringing", "commit": head[0], "commit_date": head[1],
                        "commit_subject": head[2], "commits": total_commits,
                        "built": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")}])

    roadmap_rows = parse_roadmap((ROOT / "docs" / "ROADMAP.md").read_text(encoding="utf-8"), problems)
    write("roadmap", roadmap_rows)
    hyp_text = (ROOT / "docs" / "HYPOTHESES.md").read_text(encoding="utf-8")
    hypotheses = parse_hypotheses(hyp_text, problems)
    write("hypotheses", hypotheses)

    # ================================================================ doc claims
    pages = len(list((ROOT / "docs").glob("*.html")))
    tests = sum(len(re.findall(r"^\s*def test_", p.read_text(encoding="utf-8"), flags=re.M))
                for p in (ROOT / "tests").glob("test_*.py"))
    verdicts = Counter(h["verdict"] for h in hypotheses)
    held, entries = verdicts["Held"], len(hypotheses)
    semantics_text = (ROOT / "scripts" / "semantics.py").read_text(encoding="utf-8")
    definitions = (ROOT / "docs" / "definitions_measured.md").read_text(encoding="utf-8")
    texts = {"README.md": readme, "docs/HYPOTHESES.md": hyp_text, "scripts/semantics.py": semantics_text,
             "docs/definitions_measured.md": definitions, "data/LICENCE-DATA.md": licence}
    low_stage_window = int((window & perf.stages.map(lambda s: bool(s) and max(s) < PEAL_HIGH_STAGE)).sum())
    dove_share = ratio(int((perf.dove_tower_id != "").sum()), n)
    tower_type_share = ratio(int(((perf.ring_type == TOWER_RING_TYPE) & (perf.dove_tower_id != "")).sum()),
                             int((perf.ring_type == TOWER_RING_TYPE).sum()))
    # (key, file, pattern, group, counted, unit, how it was counted)
    claims = [
        ("readme-pages", "README.md", r"\*\*(\w+) pages\*\*", 1, pages, "pages", "HTML pages in docs/"),
        ("readme-chrome-pages", "README.md", r"All (\d+) pages carry the same nav", 1, pages, "pages",
         "HTML pages in docs/"),
        ("readme-offline-pages", "README.md", r"all (\d+) pages\s+are built offline", 1, pages, "pages",
         "HTML pages in docs/"),
        ("readme-tests", "README.md", r"\*\*(\d+) unit and oracle tests", 1, tests, "tests",
         "test methods unittest discovers in tests/"),
        ("readme-held", "README.md", r"\*\*(\w+) of\s+([\w-]+) predictions held intact", 1, held, "held",
         "verdicts in docs/HYPOTHESES.md"),
        ("readme-predictions", "README.md", r"\*\*(\w+) of\s+([\w-]+) predictions held intact", 2, entries,
         "entries", "entries in docs/HYPOTHESES.md"),
        ("readme-backfill", "README.md", r"([\d,]+) performances\s+spanning", 1, n, "performances",
         "rows in data/bellboard/performances_*.csv"),
        ("readme-method-links", "README.md", r"([\d,]+) of ([\d,]+) performances\s+\(([\d.]+)%\) carry at least",
         1, int(perf.linked.sum()), "performances", "performances not in data/regional_traditions_classified.csv"),
        ("readme-bridge", "README.md", r"\*\*([\d,]+) performances\*\*, [\d.]+% of the", 1, resolved,
         "performances", "credits marked resolved in data/composer_bridge_candidates.csv"),
        ("readme-location", "README.md", r"([\d,]+) of ([\d,]+) first-performance\s+records", 1, location_linked,
         "records", "accepted occurrences in data/method_location_adjudication.csv"),
        ("readme-compositions", "README.md", r"\*\*([\d,]+) compositions and ([\d,]+) method-definition rows",
         1, complib_n, "compositions", "rows in data/complib/compositions.csv"),
        ("readme-composition-rows", "README.md", r"\*\*([\d,]+) compositions and ([\d,]+) method-definition rows",
         2, complib_m, "rows", "rows in data/complib/composition_methods.csv"),
        ("readme-raw-names", "README.md", r"([\d,]+) raw names resolved to ([\d,]+) canonical", 1,
         ids.raw_name.nunique(), "names", "raw names in data/ringer_identity_candidates.csv"),
        ("readme-clusters", "README.md", r"([\d,]+) raw names resolved to ([\d,]+) canonical", 2,
         ids.canonical_ringer_id.nunique(), "clusters", "clusters in data/ringer_identity_candidates.csv"),
        ("readme-dove-share", "README.md", r"~(\d+)% of performances carry it", 1, dove_share, "share",
         f"all performances; tower ring type alone is {tower_type_share:.1%}"),
        ("hyp-intro-wrong", "docs/HYPOTHESES.md", r"\*\*([\w-]+) of the\s+([\w-]+) entries below are wrong", 1,
         verdicts["Wrong"] + verdicts["Wrong in size"], "wrong", "verdicts in docs/HYPOTHESES.md"),
        ("hyp-intro-entries", "docs/HYPOTHESES.md", r"\*\*([\w-]+) of the\s+([\w-]+) entries below are wrong", 2,
         entries, "entries", "entries in docs/HYPOTHESES.md"),
        ("hyp-tally-held", "docs/HYPOTHESES.md", r"^\|\s*✅ Held\s*\|\s*(\d+)\s*\|", 1, held, "held",
         "verdicts in docs/HYPOTHESES.md"),
        ("hyp-tally-size", "docs/HYPOTHESES.md", r"^\|\s*🟡 Wrong in size\s*\|\s*(\d+)\s*\|", 1,
         verdicts["Wrong in size"], "entries", "verdicts in docs/HYPOTHESES.md"),
        ("hyp-tally-wrong", "docs/HYPOTHESES.md", r"^\|\s*❌ Wrong\s*\|\s*(\d+)\s*\|", 1, verdicts["Wrong"],
         "entries", "verdicts in docs/HYPOTHESES.md"),
        ("hyp-tally-total", "docs/HYPOTHESES.md", r"^\|\s*\*\*Total\*\*\s*\|\s*\*\*(\d+)\*\*\s*\|", 1, entries,
         "entries", "entries in docs/HYPOTHESES.md"),
        ("sem-unknown", "scripts/semantics.py", r"([\d,]+)\s+performances \(([\d.]+)%\) are unknown", 1,
         int((perf.length_class == "unknown").sum()), "performances",
         "the in-force peal rule applied to the committed CSVs"),
        ("sem-no-length", "scripts/semantics.py", r"`changes` is NULL -- ([\d,]+) performances", 1, no_length,
         "performances", "performances with no changes"),
        ("sem-window-unknown", "scripts/semantics.py", r"the stage is unknown -- ([\d,]+) performances", 1,
         window_unlinked, "performances", "5,000–5,039 changes with no resolved method"),
        ("sem-window", "scripts/semantics.py", r"which is ([\d,]+) performances, of which (\d+) are at a", 1,
         int(window.sum()), "performances", "performances of 5,000–5,039 changes"),
        ("sem-window-low", "scripts/semantics.py", r"which is ([\d,]+) performances, of which (\d+) are at a", 2,
         low_stage_window, "performances", "of those, stage below seven by BellBoard's method name"),
        ("sem-tower", "scripts/semantics.py", r"([\d,]+) tower \(([\d.]+)%\) and ([\d,]+) hand", 1,
         int((perf.ring_type == TOWER_RING_TYPE).sum()), "performances", "ring type tower"),
        ("sem-hand", "scripts/semantics.py", r"([\d,]+) tower \(([\d.]+)%\) and ([\d,]+) hand", 3, hand,
         "performances", "ring type hand"),
        ("sem-bulk", "scripts/semantics.py", r"([\d,]+) rows\s*(?:#:\s*)?\(([\d.]+)%\) sit on dates", 1, bulk_rows,
         "rows", "bb_timestamp days carrying more than 2,000 performances"),
        ("defs-ge-5000", "docs/definitions_measured.md", r"changes >= 5000 :\s+([\d,]+) peals", 1,
         int((perf.ch >= PEAL_MIN_CHANGES).sum()), "performances", "changes of 5,000 or more"),
        ("defs-gt-5000", "docs/definitions_measured.md", r"changes >  5000 :\s+([\d,]+) peals", 1,
         int((perf.ch > PEAL_MIN_CHANGES).sum()), "performances", "changes of more than 5,000"),
        ("defs-eq-5000", "docs/definitions_measured.md", r"exactly 5000\s+:\s+([\d,]+)", 1, boundary,
         "performances", "exactly 5,000 changes"),
        ("licence-tower-links", "data/LICENCE-DATA.md", r"([\d,]+) of them tower-linked", 1, location_linked,
         "records", "accepted occurrences in data/method_location_adjudication.csv"),
    ]
    rows = []
    for key, path, pattern, group, count, unit, how in claims:
        value, line, quote = find_claim(texts[path], pattern, group, re.M)
        if unit == "share" and value is not None:
            value = value / 100
        if value is None:
            agrees, verdict = None, "Not found"
        elif unit == "share":
            agrees = abs(value - count) < 0.005
            verdict = "Agrees" if agrees else "Drifted"
        else:
            agrees = value == count
            verdict = "Agrees" if agrees else "Drifted"
        rows.append({"key": key, "where": f"{path}:{line}" if line else path,
                     "claim": f"“{quote}”" if quote else "pattern no longer matches",
                     "stated": value, "counted": count, "unit": unit, "how": how,
                     "agrees": agrees, "verdict": verdict})
    rows.append({"key": "sources-years", "where": "data/SOURCES.md",
                 "claim": "Per-year counts table (years × 4 tables)", "stated": table_figures,
                 "counted": table_matches, "unit": "figures agree",
                 "how": "each per-year figure recounted from data/bellboard/",
                 "agrees": table_figures == table_matches and table_figures > 0,
                 "verdict": "Agrees" if table_figures == table_matches and table_figures > 0 else "Drifted"})
    write("doc_claims", rows)

    print("\nsemantic layer, as built here:",
          ", ".join(f"{k} {v:,}" for k, v in perf.length_class.value_counts().items()))
    print("settings:", ", ".join(f"{k} {v:,}" for k, v in perf.setting.value_counts().items()),
          f"(virtual with ring type tower: {virtual_tower:,})")
    drift = [r for r in rows if r["verdict"] != "Agrees"]
    print(f"doc figures recounted: {len(rows)}, of which {len(drift)} do not agree")
    for r in drift:
        print(f"  {r['verdict']:9} {r['where']:32} stated {r['stated']} counted {r['counted']}")
    return problems, written


def parse_roadmap(text, problems):
    """Every R- item in docs/ROADMAP.md: type tag, owner, and the state its section implies."""
    types = {"VISUALISATION", "FIX", "TEST", "JOIN", "SEARCH", "INTERPRETATION"}

    def plain(s):
        return " ".join(re.sub(r"\*\*|`|\*", "", s).split())

    rows, section, seen = [], None, set()
    for line in text.splitlines():
        if line.startswith("#"):
            section = line.strip("# ")
            continue
        m = re.match(r"^\|\s*(R-\d+[a-z]?)\s*\|", line)
        if not m:
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        rid, item = cells[0], cells[1]
        owner, state_text = (None, cells[2]) if section == "Held" else (cells[2], cells[3])
        t = re.match(r"^\*\*([A-Z]+)\*\*\s*[—-]\s*(.*)$", item)
        kind = t.group(1).title() if t and t.group(1) in types else None
        title = plain(t.group(2) if t else item)
        title = title[:1].upper() + title[1:]
        state_plain = plain(state_text)
        if section == "Now":
            state = "Open"
        elif section == "Done":
            state = "Superseded" if state_plain.lower().startswith("superseded") else "Done"
        elif section and section.startswith("Blocked"):
            state = ("Done" if state_plain.startswith("Done")
                     else "Superseded" if "superseded" in state_plain.lower()[:40] else "Blocked")
        elif section == "Held":
            state = "Held"
        else:
            problems.append(f"roadmap row {rid} sits in an unexpected section, {section!r}")
            continue
        if rid in seen:
            problems.append(f"roadmap row {rid} appears twice")
        seen.add(rid)
        if owner:
            o = plain(owner)
            owner = ("Claude Code" if "Claude" in o else "Gemini" if "Gemini" in o
                     else "Mistral Vibe" if "Vibe" in o else o)
        num = float(re.sub(r"[^\d]", "", rid)) + (0.5 if rid[-1].isalpha() else 0)
        rows.append({"id": rid, "num": num, "title": title, "type": kind, "owner": owner, "state": state})
    return rows


def parse_hypotheses(text, problems):
    """Each ### H entry in docs/HYPOTHESES.md with the one verdict written under it."""
    sections = [(m.start(), m.group(1)) for m in re.finditer(r"^## (.*)$", text, flags=re.M)]
    marks = {"✅": "Held", "❌": "Wrong", "🟡": "Wrong in size", "🔵": "Unresolved"}
    rows = []
    for m in re.finditer(r"^### (H\d+)\. (.*)$", text, flags=re.M):
        nxt = re.search(r"^(### |## )", text[m.end():], flags=re.M)
        body = text[m.end(): m.end() + (nxt.start() if nxt else len(text) - m.end())]
        found = re.findall(r"\*\*(✅|❌|🟡|🔵)\s*([^*]+?)\*\*", body)
        if len(found) != 1:
            problems.append(f"{m.group(1)} carries {len(found)} verdicts, not one")
            continue
        section = [s for p, s in sections if p <= m.start()][-1].replace("About the ", "").capitalize()
        rows.append({"id": m.group(1), "num": int(m.group(1)[1:]),
                     "claim": " ".join(re.sub(r"\*\*|`|\*", "", m.group(2)).split()),
                     "section": section, "verdict": marks[found[0][0]],
                     "verdict_as_written": found[0][1].strip().rstrip("."),
                     "reconstructed": "Reconstructed" in body})
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[1].strip())
    ap.add_argument("--out", default=str(ROOT / "dashboard" / "data"),
                    help="directory for the JSON datasets (default: dashboard/data, not committed)")
    args = ap.parse_args()
    problems, written = build(Path(args.out))
    if problems:
        print(f"\n{len(problems)} problem(s) -- the datasets above are not safe to publish:")
        for p in problems:
            print(f"  FAIL  {p}")
        return 1
    print(f"\n{len(written)} datasets written to {args.out}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
