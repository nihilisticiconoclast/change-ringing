#!/usr/bin/env python3
"""
Check the Markdown: that tables render, and that item references are unambiguous.

    python scripts/verify_docs.py        # exits non-zero on any failure

Two problems, both found the same way -- by a human reading the rendered page and
saying it looked wrong.

TABLES
------
A blank line ends a Markdown table. Every renderer treats the rows after it as a
NEW table, and a table whose first row is not a header renders without one --
so the roadmap's "Now" section came out as three tables, two of them headerless,
with the columns silently reassigned. Nothing in the source looks wrong: each row
is well formed, and the blank lines read as paragraph spacing.

Three things are checked per table: no blank line between rows, every row has the
header's cell count, and the delimiter row is present. The cell-count check also
catches the other common fault, an unescaped `|` inside a cell, which quietly
shifts every column to its right.

ITEM REFERENCES
---------------
There are three roadmaps -- the central one and a brief per agent -- and all
three numbered from 1. "Item 9" therefore named three different pieces of work,
and a report that item 9 had been committed to main could not be checked without
first asking which document was meant.

Every item now carries a prefixed ID that is unique across all three:

    R-nn   docs/ROADMAP.md, the central register of work
    G-nn   docs/tasks/gemini-roadmap.md
    V-nn   docs/tasks/mistral-vibe-roadmap.md

Agent tasks state which R- item they deliver, so the mapping is written down
rather than reconstructed. This file asserts that IDs are unique within each
register and that every cross-reference resolves to an ID that exists.

An ID may legitimately appear more than once -- an item listed under "Now" and
again under "Held" where the detail lives, or a task in a summary table and again
as its full brief. So the test is that one ID never names two different items,
plus the narrower rule that an ID never appears twice in the SAME table. That
second rule exists because a duplicate row can carry the same title and different
figures, which the title test waves through.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REGISTERS = {
    "R": ROOT / "docs" / "ROADMAP.md",
    "G": ROOT / "docs" / "tasks" / "gemini-roadmap.md",
    "V": ROOT / "docs" / "tasks" / "mistral-vibe-roadmap.md",
}
ID = re.compile(r"\b([RGV]-\d+[a-z]?)\b")
DELIM = re.compile(r"^\s*\|[\s:\-|]+\|\s*$")


def is_row(line):
    s = line.strip()
    return s.startswith("|") and s.endswith("|") and len(s) > 1


def cells(line):
    """Cell count, honouring \\| as an escaped literal rather than a separator."""
    return len(re.split(r"(?<!\\)\|", line.strip())) - 2


def check_tables(path):
    fails = []
    lines = path.read_text(encoding="utf-8").splitlines()
    i, rel = 0, path.relative_to(ROOT)
    while i < len(lines):
        if not is_row(lines[i]):
            i += 1
            continue
        start, width = i, cells(lines[i])
        # A blank line inside a table is invisible in the source and fatal in the
        # renderer, so look past it to see whether rows continue.
        j = i + 1
        saw_delim = False
        while j < len(lines):
            if is_row(lines[j]):
                if DELIM.match(lines[j]):
                    saw_delim = True
                elif cells(lines[j]) != width:
                    fails.append(f"{rel}:{j+1}: row has {cells(lines[j])} cells, "
                                 f"header has {width} — an unescaped '|' shifts "
                                 f"every column right of it")
                j += 1
            elif lines[j].strip() == "":
                nxt = next((k for k in range(j + 1, len(lines))
                            if lines[k].strip()), None)
                if nxt is not None and is_row(lines[nxt]):
                    fails.append(f"{rel}:{j+1}: blank line splits the table that "
                                 f"starts at line {start+1}; the rows below it "
                                 f"render as a second, headerless table")
                    j = nxt
                    continue
                break
            else:
                break
        if not saw_delim and j - start > 1:
            fails.append(f"{rel}:{start+1}: table has no |---| delimiter row, "
                         f"so it renders as plain text")
        i = max(j, i + 1)
    return fails


def _title(line, key):
    """The item's name: the second table cell, or the text after the heading dash."""
    if line.lstrip().startswith("|"):
        parts = re.split(r"(?<!\\)\|", line.strip())
        raw = parts[2] if len(parts) > 2 else ""
    else:
        raw = line.split("—", 1)[1] if "—" in line else ""
    raw = re.sub(r"\*+|`|\[|\]\([^)]*\)", "", raw)     # strip emphasis and links
    # Trailing parentheticals on a heading are status or history, not the name:
    # "(done — PR #3)", "(still active)", "(after task 6)",
    # "(was "abbreviation expansion")". Only the leading text identifies the item.
    raw = re.sub(r"\([^)]*\)\s*$", "", raw.strip())
    return " ".join(raw.split()).rstrip(".").lower()


def check_ids():
    """One ID means one item, and every reference resolves.

    An ID appearing more than once is NOT an error: the central roadmap lists an
    item in "Now" and again under "Held" where the detail lives, and each agent
    brief lists a task in its summary table and again as the full brief below.
    Those are the same item described twice, which is the document working.

    What must not happen is one ID naming two different pieces of work -- which
    is exactly what the bare numbers did across three registers. So the check is
    on the TITLE: every occurrence of an ID must agree about what it refers to.
    """
    fails, defined = [], {}
    for prefix, path in REGISTERS.items():
        if not path.exists():
            fails.append(f"{path.relative_to(ROOT)}: missing")
            continue
        seen, in_table = {}, {}
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            # A non-row line ends the current table.
            if not line.lstrip().startswith("|"):
                in_table = {}
            # A definition is an ID in the first cell of a table row, or in a heading.
            m = (re.match(rf"^\|\s*({prefix}-\d+[a-z]?)\s*\|", line)
                 or re.match(rf"^#{{2,3}} ({prefix}-\d+[a-z]?)\s+—", line))
            if m:
                key, title = m.group(1), _title(line, m.group(1))
                # Twice in ONE table is always wrong, even with the same title:
                # PR #26 added a second R-20 row with different figures, and the
                # title check waved it through because both rows were called
                # "Load CompLib in full". Listing an item in "Now" and again
                # under "Held" is fine -- that is two tables.
                if line.lstrip().startswith("|"):
                    if key in in_table:
                        fails.append(f"{path.relative_to(ROOT)}:{n}: {key} appears "
                                     f"twice in the same table (line {in_table[key]})")
                    else:
                        in_table[key] = n
                prev = seen.get(key)
                if prev and title and prev[1] and title != prev[1]:
                    fails.append(
                        f"{path.relative_to(ROOT)}:{n}: {key} names two different "
                        f"items — {prev[1]!r} at line {prev[0]}, {title!r} here")
                elif not prev:
                    seen[key] = (n, title)
        defined[prefix] = seen

    known = {k for s in defined.values() for k in s}
    for prefix, path in REGISTERS.items():
        if not path.exists():
            continue
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for ref in ID.findall(line):
                if ref not in known:
                    fails.append(f"{path.relative_to(ROOT)}:{n}: references {ref}, "
                                 f"which is not defined in any roadmap")
    return fails, defined


def main():
    fails = []
    docs = sorted((ROOT / "docs").rglob("*.md")) + [ROOT / "README.md"]
    for path in docs:
        fails += check_tables(path)
    print(f"  {'FAIL' if fails else 'ok  '}  {len(docs)} markdown file(s): tables render")
    for f in fails:
        print(f"          {f}")

    id_fails, defined = check_ids()
    fails += id_fails
    counts = " · ".join(f"{p}-nn: {len(v)}" for p, v in defined.items())
    print(f"  {'FAIL' if id_fails else 'ok  '}  item IDs unique and resolvable "
          f"({counts})")
    for f in id_fails:
        print(f"          {f}")

    if fails:
        print(f"\n{len(fails)} problem(s).")
        return 1
    print("\nEvery table renders, and every item reference names exactly one item.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
