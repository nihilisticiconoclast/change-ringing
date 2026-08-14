#!/usr/bin/env python3
"""
Link BellBoard performances to the CCCBR Methods Library.

Usage:
    python scripts/resolve_performance_methods.py --local-db data/change-ringing.db --init
    python scripts/resolve_performance_methods.py --local-db data/change-ringing.db --report

Writes `performance_methods` and `performance_method_unresolved`
(schema/005_init_performance_methods.sql). Nothing else is modified.

The problem
-----------
`performances.method` is free text. 58,577 of 96,067 rows (61.0%) match a
`methods.title` exactly; the rest split three ways:

  * ~24,000 are not methods at all -- "Tolling", "General Ringing",
    "Call Changes", "Rounds". Bells being rung, but not a method being rung.
  * 15,497 name SEVERAL methods at once: "Spliced Surprise Major (8m)" is eight
    methods, and the eight are listed in `details` as free text
    ("336 each of Tarrant, Kent, Oxford and Guilsfield").
  * the remainder are variants, abbreviations and methods the library does not
    hold.

The oracle
----------
This is why the spliced case is worth attempting at all. The method string states
HOW MANY methods to find -- the "8" in "(8m)" -- so every row checks itself:

    scan `details` for library method names at the right stage
    -> if exactly N distinct methods are found, assert the links
    -> otherwise assert nothing, and record N, what was found, and the candidates

No labelled sample was needed and none was made. The rule is per-row falsifiable
against data the source supplied.

What it achieves, and what it does not
--------------------------------------
The oracle passes on **68.0%** of the 15,497 spliced performances. It was not
pushed further, and that is deliberate. Two rounds of work took it from 63.6% to
68.0%; the next round would have been abbreviation expansion ("Rev Court" for
"Reverse Court"), which is a third tuning parameter on an approach that had
already had its two attempts. A resolver that reports precisely which rows it
cannot do is more useful than one that claims everything, and the failures here
are recorded row by row with the counts that produced them, so a later pass
starts from evidence rather than from scratch.

The three shapes of remaining failure, from the recorded rows:

  * one method short (the largest group) -- almost always an abbreviation
  * one method over -- a name that is also a common word in the surrounding prose
  * badly short -- a performance citing a named collection rather than a list
    ("Standard 8"), which cannot be resolved from `details` in principle

Result on the committed snapshot
--------------------------------
  performances                96,067
  with >= 1 method link       69,368  (72.2%)
  method links written       126,973

  high   106,643 links / 66,328 performances
  low     20,081 links /  2,791 performances
  medium     249 links /    249 performances

  unresolved                  26,699
    not_a_method              19,750   tolling, general ringing, call changes
    spliced_count_mismatch     4,348   the oracle refused it
    no_title_match             1,994   a method the library does not hold
    spliced_no_details           599   several methods claimed, none listed
    no_stage_word                  8

`not_a_method` is not a failure. Tolling and call changes are bells being rung
without a method being rung, and they must never acquire a method_id.

Confidence
----------
  high    exact `methods.title` match, or a spliced row where the oracle passed
          and every name resolved to exactly one method
  medium  title match after normalising case, apostrophes and "No. 2" -> "no2"
  low     oracle passed but at least one name is ambiguous between two library
          methods at that stage -- "Minor (2m)" naming "Cambridge" declares no
          classification, so Cambridge Bob, Surprise, Delight and Treble Bob
          Minor all remain possible. Written, flagged, and excluded from
          `v_performance_methods`.

The low band is checked for emptiness on every run: a confidence scale that never
emits its bottom band is not a scale, and finding that out is worth more than the
rows themselves. It is also checked for being too large -- the first version put
6,613 of 10,542 spliced rows in `low` because it read the stage out of the method
string and discarded the classification sitting next to it. Reading both cut it
to 2,791 and moved 34,150 links from low to high. A crowded bottom band is
usually a defect in the resolver, not honesty about the data.

Hand-checked
------------
Six `high` spliced rows were read against their `details` text by eye; all six
were correct, including two the count oracle alone could not have vouched for --
"Spliced Minor (2m)" naming "Cambridge Surprise and Plain Bob" (a prefix that
declares no classification, disambiguated by the details), and "London No.3"
resolving to "London No. 3 Surprise Royal". Six is a spot check, not an error
rate, and no error rate is claimed.
"""
import argparse
import collections
import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).parent.parent
SCHEMA = ROOT / "schema" / "005_init_performance_methods.sql"

# Stage words as they appear in a BellBoard method string, mapped to bell counts.
STAGES = {
    "singles": 3, "minimus": 4, "doubles": 5, "minor": 6, "triples": 7,
    "major": 8, "caters": 9, "royal": 10, "cinques": 11, "maximus": 12,
    "sextuples": 13, "fourteen": 14, "septuples": 15, "sixteen": 16,
    "eighteen": 18, "twenty": 20,
}

# "Spliced Surprise Major (8m)", "Doubles (11m/v)", "Doubles (1p/2m)".
# The bracket holds one or more counts tagged m (methods), v (variations) or
# p (principles); they are summed, because all three are things with names that
# appear in `details`.
MULTI_RE = re.compile(r"^(?P<pre>.*?)\s*\((?P<spec>[^)]*\d+\s*[mvp][^)]*)\)\s*$")
COUNT_RE = re.compile(r"(\d+)\s*[mvp]")

# Classification named in a multi-method prefix, mapped to the column that
# encodes it. "Spliced Surprise Major (8m)" says Surprise, and the eight names in
# `details` are therefore Surprise Major methods -- so "Cambridge" means Cambridge
# Surprise Major, not the Bob, Delight or Treble Bob method of the same name.
#
# This is the difference between a resolver that guesses and one that does not.
# Without it, 6,613 of the 10,542 oracle-passing rows had at least one name
# ambiguous across four or five library methods and had to be written as `low`.
# The information to disambiguate them was in the string the whole time; the
# first version parsed it out to get the stage and then dropped it.
#
# "Treble Dodging" and "Plain" are superclasses rather than classifications, so
# they map to their flag column instead. Longest key first, since "treble bob"
# and "treble place" both start with a word that is also meaningful alone.
CLASS_FILTERS = [
    ("treble dodging", ("cls_treble_dodging", 1)),
    ("treble place",   ("classification", "Treble Place")),
    ("treble bob",     ("classification", "Treble Bob")),
    ("surprise",       ("classification", "Surprise")),
    ("delight",        ("classification", "Delight")),
    ("alliance",       ("classification", "Alliance")),
    ("hybrid",         ("classification", "Hybrid")),
    ("place",          ("classification", "Place")),
    ("bob",            ("classification", "Bob")),
    ("plain",          ("cls_plain", 1)),
]

# Activities BellBoard records in the method field that are not methods. Matched
# as whole words against the normalised string, and only used to explain a row
# that failed to resolve -- never to skip a row that would otherwise have
# matched, so a real method called "Rounds Bob Minor" could not be lost to it.
NOT_A_METHOD = [
    "tolling", "general ringing", "call changes", "called changes", "rounds",
    "chiming", "plain hunt", "queens", "whole pulls", "ringing up",
    "ringing down", "firing", "not known", "unknown",
]


def base(s):
    """Normalise for comparison: case, accents, apostrophes, "No. 2" -> "no2"."""
    s = unicodedata.normalize("NFKD", s or "").replace("’", "'").replace("‘", "'")
    s = s.lower()
    s = re.sub(r"\bno\.?\s*(\d)", r"no\1", s)
    s = re.sub(r"['`.]", "", s)
    s = re.sub(r"[^a-z0-9 -]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def squash(s):
    """Punctuation- and space-free form.

    Needed because the same name is spaced inconsistently either side of an
    apostrophe: the library writes "Sgurr a' Mhadaidh", a footnote writes
    "Sgurr a'Mhadaidh", and after apostrophe removal those differ by a space.
    This is an alias, not a threshold -- the oracle still has to pass.
    """
    return re.sub(r"[^a-z0-9]", "", base(s))


def stage_of(text):
    """Last stage word in a method string wins: 'Spliced Surprise Major' -> 8."""
    for token in reversed(base(text).split()):
        if token in STAGES:
            return STAGES[token]
    return None


def expected_count(spec):
    counts = [int(x) for x in COUNT_RE.findall(spec)]
    return sum(counts) if counts else None


def class_filter_of(prefix):
    """Which classification, if any, a multi-method prefix commits to."""
    p = base(prefix)
    for word, spec in CLASS_FILTERS:
        if re.search(rf"(?<![a-z]){re.escape(word)}(?![a-z])", p):
            return spec
    return None


def build_indexes(conn):
    """Per stage, map a normalised name to the methods it could mean.

    Both the bare name and name-plus-classification are indexed, because the
    library splits them: "Plain Bob Minor" is stored as name "Plain" with
    classification "Bob", so a footnote saying "Plain Bob" matches nothing unless
    the combined form is indexed too. Without this, "720 Oxford, 540 Plain Bob"
    resolves to three methods -- Oxford, Plain and Bob -- and fails a two-method
    oracle for the wrong reason.
    """
    spaced = collections.defaultdict(lambda: collections.defaultdict(set))
    squashed = collections.defaultdict(lambda: collections.defaultdict(set))
    rows = conn.execute(
        "SELECT method_id, name, stage, classification, cls_plain, "
        "cls_little, cls_treble_dodging FROM methods "
        "WHERE name IS NOT NULL AND name <> ''"
    ).fetchall()
    attrs = {}
    for mid, name, stage, cls, plain, little, td in rows:
        attrs[mid] = {"classification": cls, "cls_plain": plain,
                      "cls_little": little, "cls_treble_dodging": td}
    for mid, name, stage, cls, plain, little, td in rows:
        if not stage:
            continue
        forms = {name} | ({f"{name} {cls}"} if cls else set())
        for form in forms:
            k = base(form)
            if len(k) >= 3:
                spaced[stage][k].add(mid)
            k2 = squash(form)
            if len(k2) >= 4:
                squashed[stage][k2].add(mid)
    return spaced, squashed, attrs


def compile_patterns(index):
    """One alternation per stage, longest alternative first so it wins.

    Compiled once. Matching 15,497 rows against 9,680 separately-compiled names
    took over two minutes; one alternation per stage takes 4.5 seconds.
    """
    out = {}
    for stage, names in index.items():
        keys = sorted(names, key=len, reverse=True)
        out[stage] = re.compile(
            r"(?<![a-z0-9])(?:" + "|".join(re.escape(k) for k in keys) + r")(?![a-z0-9])"
        )
    return out


def resolve(conn):
    titles = {t: m for m, t in conn.execute("SELECT method_id, title FROM methods")}
    norm_titles = collections.defaultdict(set)
    for mid, title in conn.execute("SELECT method_id, title FROM methods"):
        norm_titles[base(title)].add(mid)

    spaced, squashed, attrs = build_indexes(conn)
    pat_spaced = compile_patterns(spaced)
    pat_squash = compile_patterns(squashed)

    links = []          # (perf_id, method_id, ord, kind, confidence, matched_on)
    unresolved = []     # (perf_id, method_text, reason, expected, found, candidates)
    tally = collections.Counter()

    for perf_id, method, details in conn.execute(
        "SELECT perf_id, method, details FROM performances"
    ):
        method = method or ""

        # --- 1. exact title -------------------------------------------------
        if method in titles:
            links.append((perf_id, titles[method], 0, "exact_title", "high", method))
            tally["exact_title"] += 1
            continue

        multi = MULTI_RE.match(method)

        # --- 2. title after normalisation, only when unambiguous ------------
        if not multi:
            cands = norm_titles.get(base(method), set())
            if len(cands) == 1:
                links.append((perf_id, next(iter(cands)), 0,
                              "normalised_title", "medium", method))
                tally["normalised_title"] += 1
                continue
            if len(cands) > 1:
                unresolved.append((perf_id, method, "ambiguous_title", None,
                                   len(cands), json.dumps(sorted(cands))))
                tally["ambiguous_title"] += 1
                continue
            nm = base(method)
            if any(re.search(rf"(?<![a-z]){re.escape(w)}(?![a-z])", nm) for w in NOT_A_METHOD):
                unresolved.append((perf_id, method, "not_a_method", None, None, None))
                tally["not_a_method"] += 1
            else:
                unresolved.append((perf_id, method, "no_title_match", None, None, None))
                tally["no_title_match"] += 1
            continue

        # --- 3. several methods, named in `details` ------------------------
        n = expected_count(multi.group("spec"))
        stage = stage_of(multi.group("pre"))
        if stage is None or stage not in pat_spaced:
            unresolved.append((perf_id, method, "no_stage_word", n, None, None))
            tally["no_stage_word"] += 1
            continue
        if not details:
            unresolved.append((perf_id, method, "spliced_no_details", n, None, None))
            tally["spliced_no_details"] += 1
            continue

        hits = collections.defaultdict(set)   # squashed key -> candidate method_ids
        for k in set(pat_spaced[stage].findall(base(details))):
            hits[squash(k)] |= spaced[stage][k]
        for k in set(pat_squash[stage].findall(squash(details))):
            hits[k] |= squashed[stage][k]

        # Narrow each name to the classification the performance itself declares.
        # Only applied when it leaves something: a prefix saying "Surprise" beside
        # a name the library holds only as Bob is a disagreement to record, not a
        # reason to delete the candidate and fail the count for the wrong reason.
        cf = class_filter_of(multi.group("pre"))
        if cf:
            col, want = cf
            for key, mids in list(hits.items()):
                narrowed = {m for m in mids if attrs[m][col] == want}
                if narrowed:
                    hits[key] = narrowed

        if n is None or len(hits) != n:
            unresolved.append((
                perf_id, method,
                "spliced_count_mismatch", n, len(hits),
                json.dumps(sorted(hits)[:40]),
            ))
            tally["spliced_count_mismatch"] += 1
            continue

        # Oracle passed. Ambiguous names drop the whole row to `low` rather than
        # being silently picked from -- one guess makes the row untrustworthy,
        # not just that method.
        ambiguous = any(len(v) > 1 for v in hits.values())
        conf = "low" if ambiguous else "high"
        for i, (key, mids) in enumerate(sorted(hits.items())):
            links.append((perf_id, sorted(mids)[0], i, "spliced_details", conf, key))
        tally["spliced_low" if ambiguous else "spliced_high"] += 1

    return links, unresolved, tally


def write(conn, links, unresolved, reset):
    conn.executescript(SCHEMA.read_text(encoding="utf-8"))
    if reset:
        conn.execute("DELETE FROM performance_methods")
        conn.execute("DELETE FROM performance_method_unresolved")
    # Multi-row VALUES, never executemany: measured at 4.1 rows/s against Turso
    # versus ~1300 for batched VALUES, and it stalls on long runs. Batches stay
    # under SQLite's 32766 bind-parameter ceiling.
    def insert(sql, rows, width):
        per = max(1, 32000 // width)
        for i in range(0, len(rows), per):
            chunk = rows[i:i + per]
            ph = ",".join(["(" + ",".join(["?"] * width) + ")"] * len(chunk))
            conn.execute(sql + ph, [v for r in chunk for v in r])
    insert("INSERT OR REPLACE INTO performance_methods "
           "(perf_id, method_id, ord, match_kind, confidence, matched_on) VALUES ",
           links, 6)
    insert("INSERT OR REPLACE INTO performance_method_unresolved "
           "(perf_id, method_text, reason, expected_n, found_n, candidates) VALUES ",
           unresolved, 6)
    conn.commit()


def report(conn):
    q = lambda s: conn.execute(s).fetchall()
    total = q("SELECT COUNT(*) FROM performances")[0][0]
    linked = q("SELECT COUNT(DISTINCT perf_id) FROM performance_methods")[0][0]
    print(f"\nperformances                  {total:,}")
    print(f"  with >=1 method link        {linked:,}  ({100*linked/total:.1f}%)")
    print(f"  method links written        {q('SELECT COUNT(*) FROM performance_methods')[0][0]:,}")
    print("\nby confidence")
    for c, n in q("SELECT confidence, COUNT(*) FROM performance_methods GROUP BY 1 ORDER BY 2 DESC"):
        print(f"  {c:8s} {n:8,}")
    for band in ("high", "medium", "low"):
        if not q(f"SELECT 1 FROM performance_methods WHERE confidence='{band}' LIMIT 1"):
            print(f"  !! band '{band}' is EMPTY -- a scale that never emits a band is not a scale")
    print("\nby match kind")
    for k, n in q("SELECT match_kind, COUNT(DISTINCT perf_id) FROM performance_methods GROUP BY 1 ORDER BY 2 DESC"):
        print(f"  {k:20s} {n:8,}")
    print("\nunresolved, by reason")
    for r, n in q("SELECT reason, COUNT(*) FROM performance_method_unresolved GROUP BY 1 ORDER BY 2 DESC"):
        print(f"  {r:24s} {n:8,}")
    print("\nspliced oracle -- how far off the failures were")
    for d, n in q("""SELECT found_n - expected_n, COUNT(*) FROM performance_method_unresolved
                     WHERE reason='spliced_count_mismatch' AND expected_n IS NOT NULL
                     GROUP BY 1 ORDER BY 2 DESC LIMIT 6"""):
        print(f"  {d:+3d} methods {n:8,}")
    print("\nmost-rung methods, now answerable for the first time")
    for t, s, c, n in q("""SELECT method_title, stage, classification, COUNT(*) n
                           FROM v_performance_methods GROUP BY method_id
                           ORDER BY n DESC LIMIT 10"""):
        print(f"  {n:6,}  {t:44s} stage {s:2d} {c or ''}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--local-db", help="local SQLite/libSQL file")
    ap.add_argument("--init", action="store_true", help="create the tables")
    ap.add_argument("--reset", action="store_true", help="clear both tables first")
    ap.add_argument("--report", action="store_true", help="print the report only")
    args = ap.parse_args()

    sys.path.insert(0, str(ROOT / "scripts"))
    if args.local_db:
        import sqlite3
        conn = sqlite3.connect(args.local_db)
    else:
        from db import connect          # enforces the production interlock
        conn = connect()

    if args.report:
        report(conn)
        return 0

    links, unresolved, tally = resolve(conn)
    print("resolution pass:")
    for k, v in tally.most_common():
        print(f"  {k:24s} {v:8,}")
    write(conn, links, unresolved, reset=args.reset or args.init)
    report(conn)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
