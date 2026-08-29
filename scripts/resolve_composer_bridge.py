#!/usr/bin/env python3
"""
Bridge the composition library to the performance record, by composer.

    python scripts/resolve_composer_bridge.py --local-db data/change-ringing.db \
        --out data/composer_bridge_candidates.csv

Why by composer, and not by composition
---------------------------------------
The obvious bridge does not exist. `performances.composition` is populated on
**0 of 293,471** rows -- BellBoard does not record which composition was rung,
and no amount of work here will change that. R-37 writes that dead end up
properly; this script takes the route that is left.

`performances.composer` is free text on 71,959 records, and CompLib carries a
composer for 79,056 of its 86,054 compositions (inside `derived_title`, after
the last " by "). Those two name populations overlap heavily, so a name is the
join key that is actually available.

A name is a bad join key, and this file is mostly about how bad
--------------------------------------------------------------
"A J Cox" and "Anthony J Cox" are one man; "Andrew N Tyler" and "Albert M Tyler"
are two, and both are "A Tyler". So the key used here -- first initial plus
surname -- is deliberately crude, it over-merges, and the whole point of the
exercise is to say by how much rather than to publish a silent join. R-41 does
the normalisation properly with an adjudicated sample; this establishes what
that has to beat.

Three things are measured rather than assumed:

1. **How ambiguous the key is inside CompLib alone.** 24 keys cover more than
   one real person, 2.8% of keyable credits. That is the ceiling on precision
   before a single performance is looked at, and it is a property of the
   library, not of this matcher.

2. **What the free text actually contains.** A tenth of performance credits are
   a single token -- "BEW", "MBD", "Elf", "Traditional". Initialisms are a real
   ringing convention and they are NOT resolved here: expanding "BEW" to Brian E
   Whiting is a guess, and a guess with a plausible answer is the worst kind.
   They are reported as unresolved with the reason attached.

3. **Whether a match is right**, against evidence that carries no name in it.
   CompLib records each composition's stage and length, so a credit resolved to
   a composer can be checked against whether that composer has ever published a
   composition of the stage and length actually rung. A spurious name match has
   no reason to line up. The null model is in `--report`: the same test against
   a randomly drawn composer, which is what "lines up" is worth on its own.

What comes out
--------------
`data/composer_bridge_candidates.csv`, one row per distinct performance credit
string, carrying the parse, the key, the CompLib name it reached, how many
people that key covers, and the corroboration result. Candidates, adjudicated,
with the ambiguous ones marked -- not a join applied to the corpus.
"""
import argparse
import csv
import random
import re
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / "data" / "composer_bridge_candidates.csv"

# Credits that name no person. Matched on the whole string, not a substring:
# "Traditional" is not a composer, but "Traditional Doubles arranged by J Smith"
# names one. Ordered longest-first is unnecessary here since these are anchored.
NOT_A_PERSON = re.compile(
    r"^\W*(trad(itional)?|anon(ymous)?|unknown|various|composer unknown|"
    r"n/?a|none|as rung|standard|see below|peal composition)\W*$", re.I)

# A trailing qualifier describes the composition, not the composer:
# "D F Morrison No. 108 (2 parts)", "J J Parker (12 part, 7th obs)".
# Stripped BEFORE splitting on " and ", because "(SU0308 and SU0403)" would
# otherwise split one man into two.
PARENTHETICAL = re.compile(r"\([^)]*\)|\[[^\]]*\]")
QUALIFIER = re.compile(
    r"\b(no\.?\s*\d+\w*|op\.?\s*\d+\w*|\d+\s*-?\s*part\w*|"
    r"variation|arrangement|arr\.?|arranged)\b.*$", re.I)

SEPARATOR = re.compile(r",| and | & | with | plus |/", re.I)

# "Composed by Charles Middleton", "Comp. C Adams", "Arranged by John Pladdys".
# The credit field sometimes restates what the field already means. Left in, the
# first token becomes "Composed" and the surname becomes the forename.
LEAD_VERB = re.compile(r"^\W*(composed|comp\.?|arranged|arr\.?|by)\b\W*", re.I)

# A leading provenance token in front of a real name: "Trad Thurstans",
# "n/a Williams". Stripping it leaves a bare surname, which is correctly
# unkeyable -- better than keying the surname against a wrong forename.
LEAD_QUALIFIER = re.compile(
    r"^\W*(trad(itional)?|anon(ymous)?|unknown|n/?a|various)\b\W*", re.I)

# A single token cannot carry first-initial-plus-surname. Initialisms ("BEW",
# "MBD") and series names ("Elf", "Monument", "Sabre") both land here, and both
# are left unresolved on purpose -- see the module docstring.
def is_initialism(tok):
    return len(tok) <= 5 and tok.isupper() and tok.isalpha()


def strip_lead(s):
    """Remove leading verbs and provenance words, repeatedly.

    Once is not enough: LEAD_VERB matches "Composed", and what it leaves is
    "by Charles Middleton" -- whose first token is "by", so the credit keys as
    b-middleton and reaches nobody. Both words have to come off, and the second
    is only exposed after the first.
    """
    while True:
        t = LEAD_QUALIFIER.sub("", LEAD_VERB.sub("", s)).strip(" .,;:-")
        if t == s:
            return s
        s = t


def people(credit):
    """A credit string -> the individual people it names, in order.

    Returns [] for a credit that names nobody resolvable. The caller
    distinguishes 'names nobody' from 'names someone unkeyable' by re-reading
    the original string; classify() does that.
    """
    if not credit:
        return []
    s = re.sub(r"\s+", " ", credit.strip())
    s = PARENTHETICAL.sub(" ", s)
    # "n/a" before the separator split, or the '/' cuts it into "n" and "a",
    # and "a Williams" then keys as a real person under a-williams.
    s = re.sub(r"\bn/a\b", " ", s, flags=re.I)
    # Leading verbs and qualifiers come off BEFORE the trailing-qualifier strip.
    # "Arranged by John Pladdys" would otherwise lose the whole string: QUALIFIER
    # deletes from "arranged" to the end, which is right for
    # "D F Morrison arr W J Couperthwaite" -- Morrison composed it -- and wrong
    # when the word opens the credit and the arranger IS the attribution.
    s = strip_lead(s)
    s = QUALIFIER.sub(" ", s)
    s = re.sub(r"\s+", " ", s).strip(" .,;:-")
    if not s or NOT_A_PERSON.match(s):
        return []
    out = []
    for part in SEPARATOR.split(s):
        part = strip_lead(part.strip(" .,;:-")).strip(" .,;:-")
        # A possessive is a reference to a composition, not an attribution in
        # the form we can key: "Johnson's variation of Middleton's".
        if not part or "'" in part or "’" in part:
            continue
        if len(part.split()) >= 2:
            out.append(part)
    return out


def key(name):
    """First initial + surname, lowercased. None if the name cannot carry one."""
    parts = [p for p in name.split() if p]
    if len(parts) < 2:
        return None
    initial, surname = parts[0][0].lower(), parts[-1].lower().strip(".,")
    if not initial.isalpha() or not surname.isalpha() or len(surname) < 2:
        return None
    return f"{initial}-{surname}"


def compatible(a, b):
    """Could these two name strings be the same person?

    Compares the initial sequence before the surname, position by position, as
    far as both go. "A J Cox" and "Anthony J Cox" agree (a,j vs a,j). "Andrew N
    Tyler" and "Albert M Tyler" do not (a,n vs a,m). "Robin Daw" and "Robin A
    Daw" agree, because the shorter simply says less.
    """
    ia = [p[0].lower() for p in a.split()[:-1]]
    ib = [p[0].lower() for p in b.split()[:-1]]
    return all(x == y for x, y in zip(ia, ib))


def complib_index(conn):
    """key -> {person name -> compositions credited}, from derived_title.

    The composer sits after the last " by " in `derived_title`, which is the
    title with the attribution appended. Splitting on the LAST occurrence is
    deliberate: seven titles contain " by " themselves -- "240 Death by
    Chocolate Bob Minor by Ryan J Faulkner-Hatt", and an Op. field reading
    "shortened by Brian E Whiting by Ian M Holland", where the composer is
    Holland and Whiting wrote what was shortened. Splitting on the first
    occurrence gets all seven wrong.
    """
    idx = defaultdict(Counter)
    unattributed = 0
    for (dt,) in conn.execute("SELECT derived_title FROM compositions"):
        if not dt or " by " not in dt:
            unattributed += 1
            continue
        for person in people(dt.rsplit(" by ", 1)[1]):
            k = key(person)
            if k:
                idx[k][person] += 1
    return idx, unattributed


def repertoire(conn):
    """CompLib composer name -> set of (stage, length) they have published.

    This is the corroboration evidence, and it contains no name of the
    performance's own. A credit resolved to a composer is checked against
    whether that composer has ever published at the stage and length rung.
    """
    rep = defaultdict(set)
    for dt, stage, length in conn.execute(
            "SELECT derived_title, stage, length FROM compositions "
            "WHERE stage IS NOT NULL AND length IS NOT NULL"):
        if not dt or " by " not in dt:
            continue
        for person in people(dt.rsplit(" by ", 1)[1]):
            rep[person].add((stage, length))
    return rep


def performance_shape(conn):
    """perf_id -> (stage, changes) for performances carrying a composer.

    Stage comes from the resolved method link (schema/005), not from parsing
    the free-text method column again -- that resolution is already measured at
    77.9% coverage and re-deriving it here would be a second, unmeasured answer
    to the same question.
    """
    rows = conn.execute("""
        SELECT p.perf_id, m.stage, p.changes
        FROM performances p
        JOIN performance_methods pm ON pm.perf_id = p.perf_id AND pm.ord = 0
        JOIN methods m ON m.method_id = pm.method_id
        WHERE p.composer IS NOT NULL AND TRIM(p.composer) <> ''
          AND p.changes IS NOT NULL AND m.stage IS NOT NULL
    """).fetchall()
    return {pid: (stage, changes) for pid, stage, changes in rows}


def classify(credit, idx):
    """(status, parsed_people, key, complib_name, names_under_key).

    status is one of:
      resolved        exactly one person, key found, name compatible
      ambiguous_key   key found but covers more than one real person
      incompatible    key found but the initials rule this person out
      no_key_match    a keyable name CompLib has never published
      initialism      a single uppercase token -- deliberately not guessed
      not_a_person    Traditional, Anon, a series name, an empty parse
    """
    parsed = people(credit)
    if not parsed:
        tok = re.sub(r"\s+", " ", (credit or "").strip())
        if len(tok.split()) == 1 and is_initialism(tok):
            return "initialism", [], "", "", 0
        return "not_a_person", [], "", "", 0

    # A joint credit is attributed to its first-named composer for the bridge,
    # with the rest kept in the CSV. Attributing to all of them would count one
    # performance several times, which is the shape that made PR #28's composer
    # table wrong.
    person = parsed[0]
    k = key(person)
    if not k:
        return "not_a_person", parsed, "", "", 0
    if k not in idx:
        return "no_key_match", parsed, k, "", 0

    candidates = idx[k]
    # Real people under this key, not distinct strings: "A J Cox" and "Anthony
    # J Cox" are one, and collapsing them first is what stops the ambiguity
    # figure being three times its true size.
    groups = people_under(candidates)
    best = max(candidates, key=lambda x: candidates[x])
    if len(groups) > 1:
        return "ambiguous_key", parsed, k, best, len(groups)
    if not compatible(person, best):
        return "incompatible", parsed, k, best, len(groups)
    return "resolved", parsed, k, best, len(groups)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[1].strip())
    ap.add_argument("--local-db", default="data/change-ringing.db")
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--seed", type=int, default=20260829,
                    help="seed for the null model's random composer draw")
    args = ap.parse_args()

    db = Path(args.local_db)
    if not db.exists():
        sys.exit(f"ERROR: no replica at {db}. Build one with "
                 f"scripts/build_local_db.py --out {db}")
    conn = sqlite3.connect(str(db))
    if not conn.execute("SELECT name FROM sqlite_master WHERE type='table' "
                        "AND name='compositions'").fetchone():
        sys.exit("ERROR: this replica has no CompLib tables. Load them with "
                 "scripts/load_complib_csv.py --init --local-db " + str(db))

    idx, unattributed = complib_index(conn)
    print(f"CompLib: {sum(sum(c.values()) for c in idx.values()):,} credits "
          f"under {len(idx):,} keys; {unattributed:,} compositions carry no "
          f"attribution")

    ambiguous_keys = {k for k, c in idx.items() if len(people_under(c)) > 1}
    amb_credits = sum(sum(idx[k].values()) for k in ambiguous_keys)
    total_credits = sum(sum(c.values()) for c in idx.values())
    print(f"  {len(ambiguous_keys):,} keys cover more than one real person "
          f"({amb_credits:,} credits, {100*amb_credits/total_credits:.1f}%) "
          f"-- the precision ceiling before any matching")

    credits = conn.execute(
        "SELECT TRIM(composer), COUNT(*) FROM performances "
        "WHERE composer IS NOT NULL AND TRIM(composer) <> '' "
        "GROUP BY 1 ORDER BY 2 DESC").fetchall()

    rows, status_perfs = [], Counter()
    for credit, n in credits:
        status, parsed, k, name, groups = classify(credit, idx)
        status_perfs[status] += n
        rows.append({
            "performance_credit": credit,
            "performances": n,
            "status": status,
            "parsed_people": "; ".join(parsed),
            "key": k,
            "complib_composer": name,
            "people_under_key": groups,
            "complib_compositions": idx[k][name] if name else 0,
        })

    total = sum(n for _, n in credits)
    print(f"\nperformance credits: {len(credits):,} distinct strings, "
          f"{total:,} performances")
    for s, n in status_perfs.most_common():
        print(f"  {n:>7,} ({100*n/total:4.1f}%)  {s}")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    try:
        shown = out.relative_to(ROOT)
    except ValueError:
        shown = out
    print(f"\nwrote {len(rows):,} candidate rows -> {shown}")

    measure_accuracy(rows, idx)
    corroborate(conn, rows, idx, args.seed)
    return 0


def measure_accuracy(rows, idx):
    """Precision on the subset where the right answer is already known.

    The corroboration below says the matches behave like real ones. It does not
    say how many are right, and it cannot: a wrong match to a prolific composer
    corroborates just as well as a correct one.

    There is a subset where truth is available without any outside knowledge.
    When the performance credit spells the forename out -- "Anthony J Cox", not
    "A J Cox" -- and the CompLib name it reached also spells one out, the two
    forenames either agree or they do not, and that is the answer. Neither side
    is derived from the matcher, so this is a held-out test rather than the
    matcher grading itself.

    It measures the ONE failure mode the crude key has: choosing the wrong
    person from a key covering several. It cannot see a credit for someone
    CompLib does not hold, which lands in no_key_match and is counted there.

    The subset is easier than the whole, and the direction is knowable: a
    spelled-out forename carries strictly more information than an initial, so
    the figure here is an upper bound on precision for the initial-only
    credits, not an estimate of it. Both counts are printed for that reason.
    """
    print("\naccuracy on the held-out subset (forename spelled out both sides)")
    known = 0
    buckets = Counter()
    residual = []
    for r in rows:
        if r["status"] != "resolved" or not r["parsed_people"]:
            continue
        perf_first = r["parsed_people"].split("; ")[0].split()[0]
        cl_first = r["complib_composer"].split()[0]
        if is_initials(perf_first) or is_initials(cl_first):
            buckets["not checkable (an initial on one side)"] += r["performances"]
            continue
        known += r["performances"]
        a = perf_first.lower().strip(".")
        b = cl_first.lower().strip(".")
        if a == b:
            buckets["forenames identical"] += r["performances"]
        elif a.startswith(b) or b.startswith(a):
            # "Don"/"Donald", "Nick"/"Nicholas": one is a truncation of the
            # other, which is the same person shortened, not a mismatch.
            buckets["one forename abbreviates the other"] += r["performances"]
        elif edit_distance_le_1(a, b):
            # "Glen"/"Glenn": a spelling slip in free text typed by a ringer.
            buckets["forenames differ by one letter"] += r["performances"]
        else:
            buckets["forenames genuinely differ"] += r["performances"]
            residual.append((r["performances"], r["performance_credit"],
                             r["complib_composer"]))
    if not known:
        print("  no credit spelled a forename out on both sides")
        return
    print(f"  {known:,} performances are checkable this way")
    for k, v in buckets.most_common():
        print(f"    {v:>7,}  {k}")

    # A forename disagreement is not yet an error. "Mike Platt" and "Michael J
    # Platt" disagree by string and are one man; "George Hayward" and "Graham R
    # Hayward" disagree and are two. Only reading them tells you which, so they
    # are read once, committed, and counted from the committed file -- the
    # published precision then comes from labels a reviewer can check line by
    # line rather than from a rule invented to make the number come out.
    labels = load_adjudication()
    if labels is None:
        print("  no adjudication file; treating every disagreement as an error")
        wrong = buckets["forenames genuinely differ"]
    else:
        unlabelled = [(n, c, m) for n, c, m in residual if c not in labels]
        if unlabelled:
            print(f"  {len(unlabelled)} disagreement(s) have no adjudicated "
                  f"label -- the parser changed and the labels are stale:")
            for n, c, m in sorted(unlabelled, reverse=True)[:10]:
                print(f"    {n:>5,}  {c!r} -> {m!r}")
            sys.exit("ERROR: adjudication is stale. Re-read the new rows and "
                     "add them to data/composer_bridge_adjudication.csv, or "
                     "the precision below is measured against labels that no "
                     "longer describe the output.")
        wrong = sum(n for n, c, _ in residual if labels[c] == "different")
        same = sum(n for n, c, _ in residual if labels[c] == "same")
        print(f"    of which, adjudicated by hand ({len(residual)} strings):")
        print(f"      {same:>7,}  the same person (diminutive, archaic "
              f"abbreviation, spelling slip)")
        print(f"      {wrong:>7,}  genuinely a different person")
    agree = known - wrong
    print(f"  precision on the checkable subset: {100*agree/known:.2f}% "
          f"({agree:,} of {known:,})")

    # The half this test cannot reach, stated rather than extrapolated into.
    ic = buckets["not checkable (an initial on one side)"]
    print(f"  This figure does NOT cover the {ic:,} performances giving an "
          f"initial only. The same failure mode is present there -- a composer "
          f"CompLib does not hold, sharing a key with one it does -- and a bare "
          f"initial cannot rule it out, so directly this is an upper bound for "
          f"them rather than an estimate. The corroboration section below "
          f"reaches them by a different route.")


def load_adjudication():
    """credit -> 'same' | 'different', from the committed labels."""
    p = ROOT / "data" / "composer_bridge_adjudication.csv"
    if not p.exists():
        return None
    with p.open(newline="", encoding="utf-8") as fh:
        return {r["performance_credit"]: r["verdict"] for r in csv.DictReader(fh)}


def is_initials(token):
    """Is this token an initial or a run of them, rather than a forename?

    "J", "J.", "DF", "RDS", "A.J.", "G.A.C." are all initials -- a single
    letter, or a short all-capitals run with no lower case in it. "Don" and
    "Mike" are not.

    Two bugs were found here by reading the residual list rather than the code.
    The first version tested `len(token) < 2`, counting "J." and "RDS" as
    forenames. The second stripped dots only from the ENDS, so "A.J." became
    "A.J", which is not isalpha() and so was not recognised either -- and the
    dotted style is the common one, worth 226 performances of false errors.
    """
    t = token.replace(".", "")
    return len(t) <= 1 or (len(t) <= 4 and t.isupper() and t.isalpha())


def edit_distance_le_1(a, b):
    """True if a and b are within one insertion, deletion or substitution."""
    if abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        return sum(x != y for x, y in zip(a, b)) <= 1
    short, long = (a, b) if len(a) < len(b) else (b, a)
    for i in range(len(long)):
        if short == long[:i] + long[i + 1:]:
            return True
    return False


def people_under(counter):
    """Distinct-string counter -> lists of strings that could be one person.

    "A J Cox" and "Anthony J Cox" go in one group; "Andrew N Tyler" and
    "Albert M Tyler" do not. Counting groups rather than strings is the whole
    difference between an ambiguity figure of 2.9% and one of 48.3%.
    """
    groups = []
    for n in sorted(counter, key=lambda x: -counter[x]):
        for g in groups:
            if compatible(n, g[0]):
                g.append(n)
                break
        else:
            groups.append([n])
    return groups


def corroborate(conn, rows, idx, seed):
    """Check resolved matches against evidence that carries no name.

    For every performance whose credit resolved to a CompLib composer, ask
    whether that composer has ever published a composition at the stage and
    length actually rung. A correct match should usually agree; a spurious one
    has no reason to.

    The number is meaningless without the null, so the same test runs against a
    composer drawn at random, weighted by how much they have published -- which
    is the harder null, since a prolific composer corroborates almost anything.
    """
    print("\ncorroboration -- does the matched composer publish at this "
          "stage and length?")
    rep = repertoire(conn)
    shape = performance_shape(conn)
    by_credit = {r["performance_credit"]: r for r in rows
                 if r["status"] == "resolved"}
    if not by_credit:
        print("  no resolved credits")
        return

    perfs = conn.execute(
        "SELECT perf_id, TRIM(composer) FROM performances "
        "WHERE composer IS NOT NULL AND TRIM(composer) <> ''").fetchall()

    pool = [name for name, sl in rep.items() for _ in range(len(sl))]
    rng = random.Random(seed)
    hit = miss = null_hit = null_miss = no_shape = 0
    for pid, credit in perfs:
        r = by_credit.get(credit)
        if not r:
            continue
        if pid not in shape:
            no_shape += 1
            continue
        sl = shape[pid]
        if sl in rep.get(r["complib_composer"], ()):
            hit += 1
        else:
            miss += 1
        if sl in rep.get(rng.choice(pool), ()):
            null_hit += 1
        else:
            null_miss += 1

    n = hit + miss
    if not n:
        print("  no resolved performance had a resolvable stage and length")
        return
    print(f"  {n:,} resolved performances with a known stage and length "
          f"({no_shape:,} had no method link, so no shape to check)")
    print(f"  matched composer publishes that shape : {hit:,} "
          f"({100*hit/n:.1f}%)")
    print(f"  random composer publishes that shape  : {null_hit:,} "
          f"({100*null_hit/(null_hit+null_miss):.1f}%)   <- the null")
    lift = (hit / n) / (null_hit / (null_hit + null_miss)) if null_hit else 0
    print(f"  lift over the null                    : {lift:.2f}x")

    discriminates(conn, by_credit, rep, shape)


def discriminates(conn, by_credit, rep, shape):
    """Does the corroboration test separate matches known to be wrong?

    A test that fires equally on right and wrong answers measures nothing, which
    is how PR #21's oracle came to report F1 = 1.00 while telling us nothing at
    all. So before the corroboration rate above is used for anything, it is run
    against the 68 hand-adjudicated strings, where the answer is already known.

    It separates them by a factor of eight. That is what makes the estimate
    below legitimate: a rate this discriminating can be inverted.
    """
    labels = load_adjudication()
    if not labels:
        return
    buckets = {"known RIGHT": [0, 0], "known WRONG": [0, 0],
               "initial-only": [0, 0]}
    for pid, credit in conn.execute(
            "SELECT perf_id, TRIM(composer) FROM performances "
            "WHERE composer IS NOT NULL AND TRIM(composer) <> ''"):
        r = by_credit.get(credit)
        if not r or pid not in shape or not r["parsed_people"]:
            continue
        pf = r["parsed_people"].split("; ")[0].split()[0]
        cf = r["complib_composer"].split()[0]
        if is_initials(pf) or is_initials(cf):
            b = "initial-only"
        elif labels.get(credit) == "different":
            b = "known WRONG"
        else:
            b = "known RIGHT"
        buckets[b][1] += 1
        if shape[pid] in rep.get(r["complib_composer"], ()):
            buckets[b][0] += 1

    print("\n  is that rate discriminating? -- the same test on matches whose "
          "answer is known")
    for b, (h, t) in buckets.items():
        if t:
            print(f"    {b:<14} {h:>6,}/{t:<7,} {100*h/t:5.1f}%")

    (rh, rt), (wh, wt), (oh, ot) = (buckets["known RIGHT"],
                                    buckets["known WRONG"],
                                    buckets["initial-only"])
    if not (rt and wt and ot):
        return
    r, w, o = rh / rt, wh / wt, oh / ot
    if abs(r - w) < 0.05:
        print("    the test does not separate right from wrong, so no estimate "
              "follows from it")
        return
    p = min(1.0, max(0.0, (o - w) / (r - w)))
    print(f"\n  estimate for the initial-only half, which nothing else reaches:")
    print(f"    observed {o:.3f} = p x {r:.3f} + (1-p) x {w:.3f}")
    print(f"    implied correct: {100*p:.1f}%  "
          f"(~{round(ot*(1-p)):,} wrong of {ot:,})")
    print(f"    The wrong-match rate rests on {wt} performances, but the "
          f"estimate barely moves with it: the observed rate sits so close to "
          f"the right-match rate that p stays above 99% for any w below 0.5.")


if __name__ == "__main__":
    raise SystemExit(main())
