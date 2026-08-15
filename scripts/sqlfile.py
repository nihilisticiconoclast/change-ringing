#!/usr/bin/env python3
"""
Read a recorded .sql file and split it into statements. The only copy.

    from sqlfile import statements, statement
    statements(path)        -> ["SELECT ...", "SELECT ..."]
    statement(path, 0)      -> the first one

Why this is its own module
--------------------------
Splitting a .sql file on ';' before stripping '--' comments breaks on any
semicolon inside a comment, and on any apostrophe too, because the fragment
after the split is no longer valid SQL. The comment in `build_rhythm_page.py`
recorded that this bug "has now appeared three times in this project".

It then appeared a fourth time, in the CI check written to catch exactly this
class of problem -- which reported eight healthy queries as syntax errors,
`near "81"`, `near "he"`, `near "these"`, all of them fragments of English prose
out of a comment.

Four copies of a fix is not a fix. The four builders and the CI check now call
this, so the next place that reads a query file gets the correct behaviour by
default rather than by remembering.
"""
from pathlib import Path


def strip_comments(text):
    """Remove whole-line '--' comments. Trailing comments are left alone:
    they are still inside their statement, where they are harmless."""
    return "\n".join(
        line for line in text.splitlines() if not line.strip().startswith("--")
    )


def statements(path):
    """Every non-empty statement in a .sql file, comments stripped first."""
    body = strip_comments(Path(path).read_text(encoding="utf-8"))
    return [s.strip() for s in body.split(";") if s.strip()]


def statement(path, index=0):
    """One statement, by position."""
    return statements(path)[index]
