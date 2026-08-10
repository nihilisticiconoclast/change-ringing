#!/usr/bin/env python3
"""
Place-notation parser: turn a method's notation into the rows it produces.

Usage:
    python scripts/notation.py --score          # score against all methods
    python scripts/notation.py --show "Cambridge Surprise Minor"

Place notation describes each change as the set of bells that stay put; every
other bell swaps with its neighbour. "-" (or "x") means nobody stays, so all
bells swap in pairs, which requires an even stage.

The oracle
----------
methods.lead_head is populated for all 25,066 methods in the corpus. Parse the
notation, apply it from rounds, and the row reached must equal lead_head. That
gives a per-method pass/fail on the entire collection with no labelling and no
sampling, which is why the comma-expansion rule below was *measured* rather
than assumed: several plausible readings of the abbreviated "A,B" form exist,
and the oracle picks the right one.
"""
import argparse
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
# Bell symbols in order. 0 is 10, E is 11, T is 12, then A..D for 13..16.
SYMBOLS = "1234567890ET ABCD".replace(" ", "")
BELL_ORDER = "1234567890ETABCD"


def sym_to_place(ch):
    """'1'->0, '9'->8, '0'->9, 'E'->10, 'T'->11, 'A'->12 ..."""
    i = BELL_ORDER.find(ch.upper())
    return i if i >= 0 else None


def split_changes(block):
    """Split a notation block into individual changes.

    Changes are separated by '.', except that '-'/'x' is self-delimiting and
    needs no separator -- "-36-14" is three changes, not one.
    """
    out, buf = [], ""
    for ch in block:
        if ch in "-x":
            if buf:
                out.append(buf)
                buf = ""
            out.append("-")
        elif ch == ".":
            if buf:
                out.append(buf)
                buf = ""
        elif ch.strip():
            buf += ch
    if buf:
        out.append(buf)
    return out


def apply_change(row, change):
    """Apply one change to a row (a list of bell symbols)."""
    n = len(row)
    if change == "-":
        places = set()
    else:
        places = {sym_to_place(c) for c in change}
        places.discard(None)
    new = list(row)
    i = 0
    while i < n:
        if i in places:
            i += 1
            continue
        if i + 1 < n and (i + 1) not in places:
            new[i], new[i + 1] = row[i + 1], row[i]
            i += 2
        else:
            # A bell with no partner stays put. Notation that leaves an odd
            # gap is malformed for this stage; treating it as a place keeps
            # the parse total rather than raising.
            i += 1
    return new


# Candidate readings of the abbreviated "A,B" form. Which one is correct is an
# empirical question, settled by --score against lead_head.
EXPANSIONS = {
    "mirror_drop_last": lambda a, b: a + a[-2::-1] + b,
    "mirror_full": lambda a, b: a + a[::-1] + b,
    "mirror_drop_first": lambda a, b: a + a[:0:-1] + b,
    "b_between": lambda a, b: a + b + a[-2::-1],
}


def expand(notation, rule="mirror_drop_last"):
    """Notation string -> flat list of changes for one lead."""
    parts = notation.split(",")
    if len(parts) == 1:
        return split_changes(parts[0])
    a = split_changes(parts[0])
    b = split_changes(parts[1])
    return EXPANSIONS[rule](a, b)


def lead_rows(notation, stage, rule="mirror_drop_last"):
    """All rows of one lead, starting from rounds. First row is rounds."""
    row = list(BELL_ORDER[:stage])
    rows = [row]
    for ch in expand(notation, rule):
        row = apply_change(row, ch)
        rows.append(row)
    return rows


def lead_head(notation, stage, rule="mirror_drop_last"):
    return "".join(lead_rows(notation, stage, rule)[-1])


def score(db, rule):
    conn = sqlite3.connect(db)
    rows = conn.execute(
        'SELECT method_id, title, stage, notation, lead_head FROM methods '
        'WHERE notation IS NOT NULL AND notation <> "" '
        'AND lead_head IS NOT NULL AND lead_head <> ""'.replace('""', "''")
    ).fetchall()
    ok, fails = 0, []
    for mid, title, stage, nt, lh in rows:
        if not stage:
            fails.append((mid, title, stage, nt, lh, "no stage"))
            continue
        try:
            got = lead_head(nt, stage, rule)
        except Exception as exc:
            fails.append((mid, title, stage, nt, lh, f"error: {exc}"))
            continue
        if got == lh:
            ok += 1
        else:
            fails.append((mid, title, stage, nt, lh, got))
    return len(rows), ok, fails


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=str(ROOT / "data" / "change-ringing.db"))
    ap.add_argument("--score", action="store_true")
    ap.add_argument("--rule", default=None, help="force one expansion rule")
    ap.add_argument("--show", help="print the blue line rows for a method title")
    args = ap.parse_args()

    if args.show:
        conn = sqlite3.connect(args.db)
        r = conn.execute(
            "SELECT title, stage, notation, lead_head FROM methods WHERE title = ?",
            (args.show,),
        ).fetchone()
        if not r:
            sys.exit(f"no method titled {args.show!r}")
        title, stage, nt, lh = r
        print(f"{title}  stage {stage}  notation {nt}  lead_head {lh}")
        for i, row in enumerate(lead_rows(nt, stage)):
            print(f"  {i:3d} {''.join(row)}")
        print(f"reached {lead_head(nt, stage)}  expected {lh}  "
              f"{'MATCH' if lead_head(nt,stage)==lh else 'MISMATCH'}")
        return 0

    if args.score:
        rules = [args.rule] if args.rule else list(EXPANSIONS)
        best = None
        for rule in rules:
            total, ok, fails = score(args.db, rule)
            pct = 100 * ok / total
            print(f"  {rule:20s} {ok:6d}/{total} = {pct:5.1f}%")
            if best is None or ok > best[1]:
                best = (rule, ok, total, fails)
        rule, ok, total, fails = best
        print(f"\nbest rule: {rule} -- {ok}/{total} ({100*ok/total:.1f}%), "
              f"{len(fails)} unmatched")
        by_stage = {}
        for f in fails:
            by_stage[f[2]] = by_stage.get(f[2], 0) + 1
        print("unmatched by stage:", dict(sorted(by_stage.items(), key=lambda x: -x[1])[:10]))
        print("\nfirst 8 unmatched:")
        for f in fails[:8]:
            print(f"  stage {f[2]} {f[1][:38]:38s} {f[3][:34]:34s} want {f[4]} got {f[5]}")
        return 0

    ap.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
