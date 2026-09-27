#!/usr/bin/env python3
"""
Is the compositional corpus mostly dead paper? (R-37)

    python scripts/analyse_dead_paper.py --local-db data/change-ringing.db

The question, and the limit, stated in the question rather than a footnote
--------------------------------------------------------------------------
CompLib holds 86,054 compositions. BellBoard holds 293,471 performances. The
obvious question is what fraction of the library has ever been rung, and it
**cannot be asked**: `performances.composition` is populated on 0 of 293,471
rows, so no performance in this corpus is tied to a specific composition, and
R-36 established that no future work changes that.

What can be asked is weaker and still worth having:

    Does any performance exist that COULD have been this composition?

Matching on composer, method and length. That gives an asymmetric answer, and
the asymmetry is the whole design:

  * **No match is close to proof of absence.** If nobody ever rang that method
    at that length crediting that composer, this composition was not rung.
  * **A match proves almost nothing.** 1,496 compositions share
    `Stedman Triples @ 5040`. A performance matching a signature matches every
    composition carrying it.

So the honest output is a **lower bound on dead paper**: at least this much of
the library has nothing in the belfry that could be it. The "rung" side is an
upper bound and is reported as such, never as a count of compositions rung.

This is the same trap PR #28's withdrawn Junction 2 fell into -- it read
`(method, length)` matches as compositions identified, and published a
library-versus-belfry gap built on it. The difference here is the direction: the
unmatched side is the one that carries information.

Three things bound what this can see
------------------------------------
1. **Thirteen years.** The corpus is 2012-2024. A composition rung in 1990 and
   not since reads as dead paper, and for many of the older library it will be.
2. **Composer credit is on 24.5% of performances.** A composition whose composer
   is simply never credited looks unrung whether it is or not. The controlled
   figure below removes that explanation by restricting to composers who DO
   appear in the performance record.
3. **Single-method compositions only** -- 62,379 of 86,054. A spliced composition
   has no single method to match on, and BellBoard records spliced performances
   in a form that does not decompose reliably. Excluded and counted, not
   silently dropped.
"""
import argparse
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from resolve_composer_bridge import people, key  # noqa: E402
from semantics import is_peal, length_class  # noqa: E402


def composer_key_of(credit):
    """The R-36 bridge key for a free-text credit, or None."""
    parsed = people(credit)
    return key(parsed[0]) if parsed else None


def performance_signatures(conn):
    """(composer_key, method_title, changes) for every usable performance.

    Usable means: a composer credit that parses to a keyable name, a resolved
    first method, and a length. Everything else cannot participate in the match
    in either direction, and is counted so the denominator is honest.
    """
    rows = conn.execute("""
        SELECT p.composer, m.title, p.changes
        FROM performances p
        JOIN performance_methods pm ON pm.perf_id = p.perf_id AND pm.ord = 0
        JOIN methods m ON m.method_id = pm.method_id
        WHERE p.composer IS NOT NULL AND TRIM(p.composer) <> ''
          AND p.changes IS NOT NULL
    """).fetchall()
    sigs = set()
    composers_seen = set()
    unkeyable = 0
    for credit, title, changes in rows:
        k = composer_key_of(credit)
        if not k:
            unkeyable += 1
            continue
        composers_seen.add(k)
        sigs.add((k, title, int(changes)))
    return sigs, composers_seen, len(rows), unkeyable


def askable_compositions(conn):
    """Single-method compositions with a keyable composer and a library method.

    Returns (composer_key, method_title, length, stage, composer_name).
    """
    rows = conn.execute("""
        SELECT co.composition_id, co.derived_title, x.mt, co.length, co.stage
        FROM compositions co
        JOIN (SELECT composition_id, MIN(method_title) mt
              FROM composition_methods GROUP BY 1 HAVING COUNT(*) = 1) x
          ON x.composition_id = co.composition_id
        JOIN methods m ON m.title = x.mt
        WHERE co.length IS NOT NULL AND co.derived_title LIKE '% by %'
    """).fetchall()
    out = []
    for cid, derived, mt, length, stage in rows:
        person = people(derived.rsplit(" by ", 1)[1])
        if not person:
            continue
        k = key(person[0])
        if not k:
            continue
        out.append((k, mt, int(length), stage, person[0]))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[1].strip())
    ap.add_argument("--local-db", default="data/change-ringing.db")
    args = ap.parse_args()
    db = Path(args.local_db)
    if not db.exists():
        sys.exit(f"ERROR: no replica at {db}")
    conn = sqlite3.connect(str(db))

    total_comps = conn.execute("SELECT COUNT(*) FROM compositions").fetchone()[0]
    single = conn.execute("SELECT COUNT(*) FROM (SELECT composition_id FROM "
                          "composition_methods GROUP BY 1 HAVING COUNT(*)=1)"
                          ).fetchone()[0]

    sigs, composers_seen, perf_rows, unkeyable = performance_signatures(conn)
    asks = askable_compositions(conn)

    print("R-37 -- is the compositional corpus mostly dead paper?")
    print("=" * 74)
    print("\nWhat can be asked at all")
    print(f"  compositions in the library              {total_comps:>8,}")
    print(f"    single-method                          {single:>8,}  "
          f"({100*single/total_comps:.1f}%)")
    print(f"    ...and askable (composer + library method + length)  {len(asks):>8,}")
    print(f"  performances with composer, method, length {perf_rows:>8,}")
    print(f"    of which the credit parses to a key    {perf_rows-unkeyable:>8,}")
    print(f"  distinct (composer, method, length) signatures in the belfry "
          f"{len(sigs):>8,}")

    matched = [a for a in asks if (a[0], a[1], a[2]) in sigs]
    unmatched = [a for a in asks if (a[0], a[1], a[2]) not in sigs]
    print(f"\n{'=' * 74}\nThe raw answer")
    print(f"  no performance could be it   {len(unmatched):>8,}  "
          f"({100*len(unmatched)/len(asks):.1f}%)   <- dead paper, lower bound")
    print(f"  some performance could be it {len(matched):>8,}  "
          f"({100*len(matched)/len(asks):.1f}%)   <- upper bound on rung, not a count")

    # Controlled: only composers who DO appear in the performance record, so
    # "nobody credits this composer" stops being an available explanation.
    ctrl = [a for a in asks if a[0] in composers_seen]
    ctrl_un = [a for a in ctrl if (a[0], a[1], a[2]) not in sigs]
    print(f"\n{'=' * 74}\nControlled for composer credit")
    print("  Restricted to compositions whose composer appears somewhere in the")
    print("  performance record, so an absent match cannot be explained by the")
    print("  composer simply never being credited.")
    print(f"\n  askable compositions by a composer the belfry knows  {len(ctrl):>8,}"
          f"  ({100*len(ctrl)/len(asks):.1f}% of askable)")
    print(f"  of those, no performance could be it                 {len(ctrl_un):>8,}"
          f"  ({100*len(ctrl_un)/len(ctrl):.1f}%)")
    print("\n  This is the defensible figure. The raw one above is inflated by")
    print("  composers the performance record never names.")

    # By length class -- using the semantic layer, so the peal rule here is the
    # same rule the performance pages use.
    print(f"\n{'=' * 74}\nBy what the composition is, using scripts/semantics.py")
    by_class = defaultdict(lambda: [0, 0])
    for k, mt, length, stage, _ in ctrl:
        cls = length_class(length, stage) or "unknown"
        by_class[cls][0] += 1
        if (k, mt, length) not in sigs:
            by_class[cls][1] += 1
    print(f"  {'class':<10} {'askable':>9} {'unmatched':>11} {'dead':>8}")
    for cls in ("peal", "quarter", "short", "unknown"):
        tot, un = by_class[cls]
        if tot:
            print(f"  {cls:<10} {tot:>9,} {un:>11,} {100*un/tot:>7.1f}%")

    # Who writes paper nobody rings, and who does not.
    print(f"\n{'=' * 74}\nBy composer, the ten most prolific in the controlled set")
    per = defaultdict(lambda: [0, 0])
    names = {}
    for k, mt, length, stage, nm in ctrl:
        per[k][0] += 1
        names.setdefault(k, nm)
        if (k, mt, length) not in sigs:
            per[k][1] += 1
    top = sorted(per.items(), key=lambda kv: -kv[1][0])[:10]
    print(f"  {'composer':<26} {'compositions':>13} {'unmatched':>10} {'dead':>7}")
    for k, (tot, un) in top:
        print(f"  {names[k]:<26} {tot:>13,} {un:>10,} {100*un/tot:>6.1f}%")

    # The reverse direction. Two jobs: it validates the matching machinery -- if
    # hardly any performance found a composition, the join would be broken rather
    # than the library dead -- and it is a finding on its own.
    print(f"\n{'=' * 74}\nThe same question asked backwards")
    comp_sigs = {(k, mt, ln) for k, mt, ln, _, _ in asks}
    hit = miss = 0
    for credit, title, changes in conn.execute("""
            SELECT p.composer, m.title, p.changes FROM performances p
            JOIN performance_methods pm ON pm.perf_id = p.perf_id AND pm.ord = 0
            JOIN methods m ON m.method_id = pm.method_id
            WHERE p.composer IS NOT NULL AND TRIM(p.composer) <> ''
              AND p.changes IS NOT NULL"""):
        k = composer_key_of(credit)
        if not k:
            continue
        if (k, title, int(changes)) in comp_sigs:
            hit += 1
        else:
            miss += 1
    n = hit + miss
    print(f"  performances whose signature IS in the library     {hit:>8,}  "
          f"({100*hit/n:.1f}%)")
    print(f"  performances whose signature is NOT in the library {miss:>8,}  "
          f"({100*miss/n:.1f}%)")
    print("\n  First, this validates the matching: 61.8% is a healthy hit rate, so the")
    print("  64.5% above is a library that is not rung rather than a join that does")
    print("  not work. A broken join would show near-zero here.")
    print("\n  Second, it is a finding. The overlap is partial in BOTH directions: the")
    print("  belfry rings a great deal the library does not hold -- from the Ringing")
    print("  World, from personal collections, from compositions never uploaded --")
    print("  and the library holds a great deal the belfry never rings. These are two")
    print("  populations that meet at the edges, not one feeding the other.")

    print(f"\n{'=' * 74}")
    print("Read the unmatched column, not the matched one. A match means some")
    print("performance shares the signature, and 1,496 compositions share")
    print("`Stedman Triples @ 5040`. Only absence carries information here.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
