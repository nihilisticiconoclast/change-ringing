#!/usr/bin/env python3
"""
Refuse a branch that is too stale to review, or that reintroduces rejected work.

    python scripts/check_branch_safety.py --head origin/some-branch
    python scripts/check_branch_safety.py --base origin/main --head HEAD --max-behind 15

Exits non-zero on a problem, so it can gate a pull request.

Why this exists, and what the problem actually turned out to be
---------------------------------------------------------------
Five branches in a row -- PRs #7, #9, #11, #12 and feature/data-insights -- were
cut from the same commit, `5e29df8`, and by the time each arrived main had moved
24 commits past it. Reviewing each one by hand took longer than the contribution
was worth, and the same rejected files kept coming back.

**The first version of this script checked for the wrong thing.** It was written
on the belief that merging those branches would DELETE work -- `site_chrome.py`,
`verify_chrome.py`, two published pages, three schema files. That belief came
from reading `git diff --stat main <branch>`, which reports 2.2 million deletions
for one of them.

That diff is not what a merge does. It is a two-dot diff between two trees, so it
counts every file main has gained since the branch point as "deleted". A real
merge is three-way: it uses the merge base, and a file the branch never touched
survives. Test-merged all three branches into a scratch worktree to check:

    branch                              deletions  conflicts  rejected files re-added
    feature/gemini-footnote-occasions           0         20                        4
    cleanup/repo-audit-and-consistency          0         26                        4
    feature/data-insights                       0         16                        1

Zero deletions, every time. The danger was imaginary; the cost is real but it is
a different cost. So this checks the two things the evidence actually shows:

  1. **Conflict load.** A branch 24 commits behind produces 16-26 conflicted
     files, each needing a human decision. That is the tax, and it scales with
     staleness.
  2. **Rejected work coming back.** Files that were reviewed and deliberately not
     merged reappear as clean additions in the next PR from the same stale base,
     where they look like new contributions. This has happened three times with
     `create_pr.py` and `rebuild_corpus.py`.

A genuine deletion relative to the merge base is still checked, because that one
would be real -- it just was not what was happening.

Declaring intent
----------------
To delete a file on purpose, or to revive a previously rejected one, say so in
the pull request body or the branch's latest commit message:

    DELETES: scripts/old_thing.py
    REVIVES: scripts/create_pr.py    # and say why in the PR body

Both are then allowed for exactly those paths.
"""
import argparse
import re
import subprocess
import sys

DECLARE_RE = r"^\s*{}:\s*(.+)$"

# Files reviewed and deliberately not merged, with the reason and where it was
# given. A branch that re-adds one of these is not contributing it, it is
# resurfacing it -- so the check names the previous decision rather than just
# saying no. Remove an entry here if the decision is genuinely reversed.
REJECTED = {
    "scripts/create_pr.py":
        "PR #9 -- extracts a GitHub token from the credential store; out of scope",
    "scripts/inspect_branches_prs.py":
        "PR #12 -- same, and TypeErrors when no credential is present",
    "scripts/rebuild_corpus.py":
        "PR #9 -- superseded by scripts/rebuild_all.py, which fails loudly",
    "schema/005_init_complib.sql":
        "PR #7 -- number collision; 005 is performance_methods, CompLib is 006",
}


def git(*args, check=True):
    out = subprocess.run(["git", *args], capture_output=True, text=True)
    if check and out.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} failed:\n{out.stderr.strip()}")
    return out.stdout.strip()


def declared(text, keyword):
    paths = set()
    for m in re.finditer(DECLARE_RE.format(keyword), text or "", re.MULTILINE | re.IGNORECASE):
        paths.update(p.strip() for p in m.group(1).replace(",", " ").split() if p.strip())
    return paths


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--base", default="origin/main")
    ap.add_argument("--head", default="HEAD")
    ap.add_argument("--max-behind", type=int, default=15,
                    help="fail if the merge base is more than this many commits behind "
                         "(default: 15; the branches that caused trouble were at 24)")
    ap.add_argument("--body", default="", help="PR body, scanned for DELETES:/REVIVES:")
    args = ap.parse_args()

    merge_base = git("merge-base", args.base, args.head)
    behind = int(git("rev-list", "--count", f"{merge_base}..{args.base}") or 0)
    ahead = int(git("rev-list", "--count", f"{merge_base}..{args.head}") or 0)
    log = git("log", "--format=%B", f"{merge_base}..{args.head}") if ahead else ""

    ok_delete = declared(args.body, "DELETES") | declared(log, "DELETES")
    ok_revive = declared(args.body, "REVIVES") | declared(log, "REVIVES")

    changed = git("diff", "--name-only", f"{merge_base}..{args.head}").splitlines()
    deleted = git("diff", "--name-only", "--diff-filter=D",
                  f"{merge_base}..{args.head}").splitlines()
    undeclared_deletes = sorted(set(p for p in deleted if p) - ok_delete)
    revived = sorted((set(changed) & set(REJECTED)) - ok_revive)

    print(f"base        {args.base} ({git('rev-parse','--short',args.base)})")
    print(f"head        {args.head} ({git('rev-parse','--short',args.head)})")
    print(f"merge base  {git('rev-parse','--short',merge_base)} -- "
          f"{behind} behind, {ahead} ahead")
    print(f"changed     {len(changed)} file(s); {len(deleted)} deletion(s)")

    problems = []

    if behind > args.max_behind:
        problems.append(
            f"Cut from a base {behind} commits behind {args.base} (limit {args.max_behind}).\n\n"
            f"  This does not destroy anything -- a three-way merge keeps what main gained.\n"
            f"  What it costs is conflicts: at 24 commits behind, the last three branches\n"
            f"  produced 16, 20 and 26 conflicted files, each needing a human decision.\n\n"
            f"      git fetch origin && git rebase origin/main\n\n"
            f"  Note that GitHub's PR page shows the base branch TIP, not the merge base,\n"
            f"  so a stale branch looks current there. Trust `git merge-base`."
        )

    if revived:
        lines = "\n".join(f"      {p}\n          previously: {REJECTED[p]}" for p in revived)
        problems.append(
            f"Reintroduces {len(revived)} file(s) that were reviewed and not merged:\n{lines}\n\n"
            f"  These arrive looking like new contributions because the branch predates\n"
            f"  the decision. If you disagree with the decision, say so and revive it\n"
            f"  deliberately:\n\n"
            f"      REVIVES: {' '.join(revived)}"
        )

    if undeclared_deletes:
        shown = "\n".join(f"      {p}" for p in undeclared_deletes[:20])
        more = (f"\n      ... and {len(undeclared_deletes)-20} more"
                if len(undeclared_deletes) > 20 else "")
        problems.append(
            f"Deletes {len(undeclared_deletes)} file(s) relative to its own merge base:\n"
            f"{shown}{more}\n\n"
            f"      DELETES: {' '.join(undeclared_deletes[:3])}"
            f"{' ...' if len(undeclared_deletes) > 3 else ''}"
        )

    if not problems:
        print("\nOK -- base current enough, no revived rejects, no undeclared deletions.")
        return 0

    print(f"\n{'='*72}")
    for i, p in enumerate(problems, 1):
        print(f"\n  {i}. {p}")
    print(f"\n{'='*72}")
    print("Branch safety check FAILED.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
