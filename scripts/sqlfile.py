#!/usr/bin/env python3
"""
Read a recorded .sql file and split it into statements. The only copy.

    from sqlfile import statements, statement
    statements(path)        -> ["SELECT ...", "SELECT ..."]
    statement(path, 0)      -> the first one

Why this is its own module
--------------------------
Splitting a .sql file on ';' without regard for comments breaks on any semicolon
inside one: the fragment after the split is no longer valid SQL. The comment in
`build_rhythm_page.py` recorded that this bug "has now appeared three times in
this project".

It has since appeared twice more, which is why this exists.

  * The fourth was in the CI step written to catch broken SQL. It split inline
    and reported eight healthy queries as syntax errors -- `near "81"`,
    `near "he"`, `near "these"` -- fragments of English prose from comments.

  * The fifth was in the first version of THIS module, which stripped only
    whole-line comments and claimed in its own docstring that trailing ones were
    "harmless". They are not. This line, from a recorded query:

        AND p.duration NOT LIKE '%m%'   -- 'Nh MM'; the bare '45m' rows are quarters

    carries a semicolon in a trailing comment and split the statement in half.
    The CI check caught it, which is the system working, but only after the
    module written to end the bug reintroduced it.

So the stripper below is a small scanner rather than a line filter: it walks the
text once, tracks whether it is inside a quoted string, and removes `--` to
end-of-line only when it is not. That handles the trailing case and the
apostrophe case together, which no line-based version can.
"""
from pathlib import Path


def strip_comments(text):
    """Remove `--` comments, whole-line and trailing, respecting string literals.

    A `--` inside a quoted string is data, not a comment: `WHERE note = 'a--b'`
    must survive intact. SQL escapes a quote by doubling it ('' inside a string),
    which this handles by simply toggling on every quote -- a doubled quote
    toggles off then on again and lands in the right state.
    """
    out = []
    i, n = 0, len(text)
    in_string = False
    while i < n:
        ch = text[i]
        if in_string:
            out.append(ch)
            if ch == "'":
                in_string = False
            i += 1
        elif ch == "'":
            in_string = True
            out.append(ch)
            i += 1
        elif ch == "-" and i + 1 < n and text[i + 1] == "-":
            # Comment to end of line. Keep the newline so line structure -- and
            # therefore any error message's line number -- survives.
            j = text.find("\n", i)
            if j < 0:
                break
            i = j
        else:
            out.append(ch)
            i += 1
    return "".join(out)


def statements(path):
    """Every non-empty statement in a .sql file, comments stripped first."""
    return [s.strip() for s in strip_comments(Path(path).read_text(encoding="utf-8")).split(";")
            if s.strip()]


def statement(path, index=0):
    """One statement, by position."""
    return statements(path)[index]


if __name__ == "__main__":
    # Self-test: the two shapes that have actually broken this project.
    cases = [
        ("SELECT 1; -- trailing; with a semicolon\nSELECT 2;", 2),
        ("-- 81% of things don't work\nSELECT 1;", 1),
        ("SELECT 'a--b' AS x;", 1),
        ("SELECT 'it''s fine' AS x; -- and; this\nSELECT 2;", 2),
    ]
    import tempfile, os
    ok = True
    for text, want in cases:
        with tempfile.NamedTemporaryFile("w", suffix=".sql", delete=False) as f:
            f.write(text)
            p = f.name
        got = statements(p)
        os.unlink(p)
        status = "ok " if len(got) == want else "FAIL"
        ok &= len(got) == want
        print(f"  {status} {want} statement(s) from {text!r} -> {got}")
    raise SystemExit(0 if ok else 1)
