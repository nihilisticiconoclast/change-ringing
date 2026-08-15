#!/usr/bin/env python3
"""
Rebuild everything derived: the replica, the inferred datasets, the nine pages.

One command, in dependency order, that fails loudly at the first broken step.

    python scripts/rebuild_all.py                  # everything
    python scripts/rebuild_all.py --pages-only     # just docs/, from the existing DB
    python scripts/rebuild_all.py --skip-inference # DB + pages, no re-inference

Why this exists
---------------
The pipeline was nine commands in a particular order held in someone's head, and
the order is not guessable: the pages read the database, the database needs the
method linkage applied, and the linkage needs the CSVs loaded. Getting it wrong
does not error -- it republishes a page against a stale database, which looks
exactly like a page that is fine.

Why it fails loudly
-------------------
The first version of this script, from Gemini's PR #9, looped over the builders
like this:

    res = subprocess.run(['python', script], capture_output=True, text=True)
    if res.returncode != 0:
        print(f'Error in {script}: {res.stderr}')

-- printed the error, kept going, and exited 0. Its caller then announced
"SUCCESS: Entire Pipeline Completed". So a run in which every single page failed
to build was indistinguishable, by exit code, from a clean one, and the whole
value of an orchestrator is that its exit code means something. Output is also
not captured here: a rebuild is a thing you watch, and swallowing stdout to
reprint it on failure loses the progress of the step that hung.

STEPS is the list, and it is the only list. Adding a page means adding a line
here, the same way adding a page means adding a line to site_chrome.PAGES.
"""
import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB = "data/change-ringing.db"


def steps(db, skip_inference):
    """(label, argv, phase) in dependency order. phase is 'data' or 'pages'."""
    out = [
        ("Build the replica from committed CSVs",
         ["build_local_db.py", "--out", db, "--keep-cache"], "data"),
    ]
    if not skip_inference:
        out += [
            ("Resolve ringer identities",
             ["resolve_ringer_identities.py", "--db", db,
              "--out", "data/ringer_identity_candidates.csv"], "data"),
            ("Classify footnote occasions",
             ["classify_footnote_occasions.py", "--local-db", db,
              "--out", "data/footnote_occasions.csv"], "data"),
        ]
    # The nine published pages, in the order site_chrome.PAGES lists them.
    out += [
        ("Founder Atlas          -> docs/index.html",     ["build_atlas.py"], "pages"),
        ("Method Lineage         -> docs/lineage.html",   ["build_lineage_atlas.py"], "pages"),
        ("Blue Line Atlas        -> docs/methods.html",   ["build_method_atlas.py"], "pages"),
        ("First Rung             -> docs/invention.html", ["build_invention_page.py"], "pages"),
        ("Rhythm of Ringing      -> docs/rhythm.html",    ["build_rhythm_page.py"], "pages"),
        ("Ringer Constellation   -> docs/ringers.html",   ["build_ringers_page.py"], "pages"),
        ("The Occasions Archive  -> docs/occasions.html", ["build_occasions_page.py"], "pages"),
        ("The Temporal Nexus     -> docs/nexus.html",     ["build_nexus_page.py"], "pages"),
        ("Sacred Geometry        -> docs/geometry.html",  ["build_geometry_page.py"], "pages"),
        # Both verifiers run last and both can fail the build. verify_chrome
        # catches a nav or footer that drifted; verify_corpus catches a database
        # the pages were just built against that should not have been trusted.
        ("Verify nav and footer are identical on all nine pages",
         ["verify_chrome.py"], "pages"),
        ("Verify corpus integrity",
         ["verify_corpus.py", "--local-db", db], "pages"),
    ]
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[1].strip())
    ap.add_argument("--local-db", default=DEFAULT_DB,
                    help=f"replica path (default: {DEFAULT_DB})")
    ap.add_argument("--pages-only", action="store_true",
                    help="rebuild docs/ from the existing database, nothing else")
    ap.add_argument("--skip-inference", action="store_true",
                    help="rebuild the database and pages, but do not re-run the "
                         "ringer and footnote resolvers")
    ap.add_argument("--dry-run", action="store_true",
                    help="print the plan and exit")
    args = ap.parse_args()

    plan = steps(args.local_db, args.skip_inference)
    if args.pages_only:
        plan = [s for s in plan if s[2] == "pages"]

    if args.dry_run:
        for i, (label, argv, _) in enumerate(plan, 1):
            print(f"{i:2d}. {label}\n    scripts/{' '.join(argv)}")
        return 0

    t0 = time.time()
    for i, (label, argv, _) in enumerate(plan, 1):
        print(f"\n{'=' * 72}\n[{i}/{len(plan)}] {label}\n{'=' * 72}", flush=True)
        t = time.time()
        # Output is deliberately NOT captured -- see the module docstring.
        res = subprocess.run([sys.executable, f"scripts/{argv[0]}", *argv[1:]],
                             cwd=str(ROOT))
        if res.returncode != 0:
            print(f"\nFAILED at step {i}/{len(plan)}: {label}\n"
                  f"  scripts/{' '.join(argv)}\n"
                  f"  exit {res.returncode}\n\n"
                  f"Stopping here. Later steps read what this one produces, so "
                  f"running them now would build on a broken input -- which is "
                  f"the failure this script exists to make impossible.",
                  file=sys.stderr)
            return res.returncode
        print(f"  ok ({time.time() - t:.1f}s)", flush=True)

    print(f"\n{'=' * 72}\nAll {len(plan)} steps passed in {time.time() - t0:.0f}s.")
    print("Rebuilt: the replica, the derived CSVs, and all nine pages in docs/.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
