#!/usr/bin/env python3
"""
Unified Corpus & Visualisation Pipeline Orchestrator.

Executes the complete reproducible pipeline (following Lesson 14: 'Commit the recipe, not the output'):
1. Builds/syncs local database replica from committed CSVs (scripts/build_local_db.py)
2. Re-runs multi-signal ringer identity resolution (scripts/resolve_ringer_identities.py)
3. Re-runs footnote occasion classification (scripts/classify_footnote_occasions.py)
4. Rebuilds all HTML visualisations in docs/ (scripts/rebuild_all.py)
5. Verifies complete corpus integrity and query plans (scripts/verify_corpus.py)

Usage:
    python scripts/rebuild_corpus.py
    python scripts/rebuild_corpus.py --skip-inference  # Just rebuild DB and HTML views
"""
import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).parent.parent

def run_step(step_name: str, cmd: list):
    print(f"\n{'='*70}\n>>> Step: {step_name}\n{'='*70}", flush=True)
    t0 = time.time()
    res = subprocess.run(cmd, cwd=str(ROOT), text=True)
    elapsed = time.time() - t0
    if res.returncode != 0:
        print(f"FAILED: {step_name} (exited with code {res.returncode})", file=sys.stderr)
        sys.exit(res.returncode)
    print(f"COMPLETED: {step_name} in {elapsed:.1f}s", flush=True)

def main():
    parser = argparse.ArgumentParser(description="Rebuild entire corpus, derived inference datasets, and HTML visualisations.")
    parser.add_argument("--skip-inference", action="store_true", help="Skip re-running heavy ringer/footnote resolution")
    parser.add_argument("--local-db", default="local_corpus.db", help="Path to local database output")
    args = parser.parse_args()

    t_start = time.time()
    print("Starting Change Ringing Corpus & Visualisation Automated Pipeline...", flush=True)

    # 1. Build Local Replica Database
    run_step("1. Build Offline Replica DB", [
        sys.executable, "scripts/build_local_db.py", "--out", args.local_db
    ])

    if not args.skip_inference:
        # 2. Ringer Identity Resolution
        run_step("2. Resolve Ringer Identities", [
            sys.executable, "scripts/resolve_ringer_identities.py",
            "--db", args.local_db,
            "--out", "data/ringer_identity_candidates.csv"
        ])

        # 3. Footnote Occasion Classification
        run_step("3. Classify Footnote Occasions", [
            sys.executable, "scripts/classify_footnote_occasions.py",
            "--local-db", args.local_db,
            "--out", "data/footnote_occasions.csv"
        ])

    # 4. Rebuild All HTML Visualisations
    run_step("4. Rebuild All HTML Visualisations", [
        sys.executable, "scripts/rebuild_all.py"
    ])

    # 5. Verify Corpus Integrity
    run_step("5. Verify Corpus Integrity", [
        sys.executable, "scripts/verify_corpus.py", "--local-db", args.local_db
    ])

    total_time = time.time() - t_start
    print(f"\n{'='*70}\n>>> SUCCESS: Entire Corpus & Visualisations Pipeline Completed in {total_time:.1f}s\n{'='*70}", flush=True)

if __name__ == "__main__":
    main()
