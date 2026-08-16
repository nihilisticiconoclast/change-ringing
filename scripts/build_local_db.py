#!/usr/bin/env python3
"""
Build a complete offline replica of the corpus, with zero Turso access.

Usage:
    python scripts/build_local_db.py                      # Dove + Methods
    python scripts/build_local_db.py --bellboard-since 2026-08-01
    python scripts/build_local_db.py --out my_copy.db --keep-cache

Everything this database contains is reproducible from public sources plus
artefacts committed to this repository, so nobody needs to read from Turso to
develop against it:

  Dove's Guide      -- public CSVs, https://dove.cccbr.org.uk
  CCCBR Methods     -- public XML,  https://methods.cccbr.org.uk
  schema/001..007   -- in this repo
  location linkage  -- data/method_location_adjudication.csv, in this repo

The one exception is BellBoard. Its corpus is only reachable through an API
that throttles by silently truncating responses, so it is not fetched unless
you ask with --bellboard-since, and even then only for the window you name.
A replica without it is still useful for anything touching Dove or the
Methods Library; a replica with a recent window matches what production
holds: the complete 2012-2024 BellBoard record, 293,471 performances.

The replica uses an embedded libSQL connection rather than the stdlib sqlite3
module, deliberately. sqlite3 accepts SQL that libSQL rejects -- see the
module docstring in scripts/db.py -- so testing against sqlite3 gives false
confidence. This build is intended to be a real check.

If libsql is not installed the build still runs, on stdlib sqlite3, and warns.
The replica it produces is correct; what is lost is the dialect checking, so
a page or loader validated that way has been checked less strictly than one
validated with libsql present.
"""
import argparse
import csv
import subprocess
import sys
from pathlib import Path

try:
    import libsql

    HAVE_LIBSQL = True
except ImportError:
    import sqlite3 as libsql

    HAVE_LIBSQL = False

ROOT = Path(__file__).parent.parent
SCRIPTS = ROOT / "scripts"
SCHEMA_DIR = ROOT / "schema"
ADJUDICATION = ROOT / "data" / "method_location_adjudication.csv"
LOC_KEY = lambda b, t, c: f"{b or ''}|{t or ''}|{c or ''}"


def run(cmd):
    """Run a script under this interpreter. `cmd` is the script and its args --
    do NOT include sys.executable, run() adds it.

    Echo the argv that actually runs, prefix included. The version that printed
    `cmd` alone hid a caller which passed sys.executable itself: the echoed line
    read correctly while the real argv had the interpreter twice, and the error
    that came back ("source code cannot contain null bytes") pointed at
    /usr/local/bin/python3 rather than at the caller."""
    argv = [sys.executable, *[str(c) for c in cmd]]
    print(f"\n$ {' '.join(argv)}")
    result = subprocess.run(argv)
    if result.returncode != 0:
        raise SystemExit(f"step failed: {' '.join(argv)}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="local_corpus.db", help="Path for the replica")
    ap.add_argument("--cache", default=".local-build-cache",
                    help="Where downloaded source files are kept")
    ap.add_argument("--keep-cache", action="store_true",
                    help="Reuse previously downloaded sources instead of refetching")
    ap.add_argument("--bellboard-since", metavar="YYYY-MM-DD",
                    help="Also ingest BellBoard performances changed on or after this "
                         "date. Omitted by default: BellBoard throttles, and a replica "
                         "is useful without it.")
    ap.add_argument("--skip-adjudication", action="store_true",
                    help="Leave method_performances.dove_tower_id unpopulated")
    ap.add_argument("--skip-method-linkage", action="store_true",
                    help="Do not resolve performances to methods "
                         "(schema/005, scripts/resolve_performance_methods.py)")
    args = ap.parse_args()

    if not HAVE_LIBSQL:
        print(
            "WARNING: libsql not installed; building with stdlib sqlite3.\n"
            "  The replica will be correct, but will not reject libSQL dialect\n"
            "  errors the way production does. pip install -r requirements.txt",
            file=sys.stderr,
        )

    out = Path(args.out)
    cache = Path(args.cache)
    cache.mkdir(parents=True, exist_ok=True)

    if out.exists():
        print(f"Removing existing {out}")
        out.unlink()

    csv_dir = cache / "dove-csvs"
    if not args.keep_cache or not (csv_dir / "dove.csv").exists():
        run([SCRIPTS / "fetch_dove_csvs.py", "--out-dir", csv_dir])
    else:
        print(f"Reusing cached Dove CSVs in {csv_dir}")

    run([SCRIPTS / "migrate_csv_to_turso.py", "--csv-dir", csv_dir,
         "--local-db", out, "--reset"])

    run([SCRIPTS / "ingest_methods.py", "--init", "--local-db", out])

    # BellBoard data ingestion
    bb_dir = ROOT / "data" / "bellboard"
    bb_perf_csvs = sorted(list(bb_dir.glob("performances_*.csv"))) if bb_dir.exists() else []

    if args.bellboard_since:
        run([SCRIPTS / "ingest_bellboard.py", "--init", "--local-db", out,
             "--changed-since", args.bellboard_since])
    elif bb_perf_csvs:
        print(f"\nIngesting committed BellBoard corpus from {bb_dir} ({len(bb_perf_csvs)} yearly files)...")
        conn = libsql.connect(str(out))
        conn.executescript((SCHEMA_DIR / "002_init_bellboard.sql").read_text())
        
        # csv.DictReader returns '' for an empty cell. Storing that instead of
        # NULL silently breaks every IS NULL check downstream: after the first
        # committed-corpus load, "dove_tower_id IS NULL" matched zero rows while
        # 15,939 performances genuinely had no tower, so coverage read 100%
        # against a true 83%. Empty means unknown here, so it becomes NULL.
        nz = lambda v: None if v == "" else v

        def load(path, table, verb="INSERT"):
            """Load one committed CSV into one table. Returns rows loaded.

            The three copies of this that used to sit inline differed only in
            table name and verb -- and the fourth, flags, was simply never
            written. 25,030 committed flag rows sat unread through every build
            because the loop that would have loaded them did not exist, and
            nothing noticed: performance_flags reported 0 and 0 was inside the
            expected range. scripts/verify_corpus.py now compares every table
            against its CSVs, which is what surfaced it."""
            if not path.exists():
                return 0
            with open(path, encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
            if not rows:
                return 0
            flds = list(rows[0].keys())
            cols = ", ".join('"' + c + '"' for c in flds)
            conn.executemany(
                f"{verb} INTO {table} ({cols}) "
                f"VALUES ({', '.join(['?'] * len(flds))})",
                [[nz(r.get(k)) for k in flds] for r in rows],
            )
            return len(rows)

        totals = {"performances": 0, "performance_ringers": 0,
                  "performance_footnotes": 0, "performance_flags": 0}
        for p_csv in bb_perf_csvs:
            yr = p_csv.stem.split("_")[-1]
            totals["performances"] += load(p_csv, "performances", "INSERT OR REPLACE")
            totals["performance_ringers"] += load(
                bb_dir / f"ringers_{yr}.csv", "performance_ringers")
            totals["performance_footnotes"] += load(
                bb_dir / f"footnotes_{yr}.csv", "performance_footnotes")
            totals["performance_flags"] += load(
                bb_dir / f"flags_{yr}.csv", "performance_flags")

        conn.commit()
        conn.close()
        print(f"  Ingested from {len(bb_perf_csvs)} years: "
              + ", ".join(f"{v:,} {k.replace('performance_', '')}"
                          for k, v in totals.items()))
    else:
        # Create the tables even when not populating them, so queries and
        # schema checks against the replica behave the same as production.
        conn = libsql.connect(str(out))
        conn.executescript((SCHEMA_DIR / "002_init_bellboard.sql").read_text())
        conn.commit()
        conn.close()
        print("\nBellBoard tables created but left empty "
              "(pass --bellboard-since to populate).")

    conn = libsql.connect(str(out))
    conn.executescript((SCHEMA_DIR / "004_read_cost_indexes.sql").read_text())
    # Deduplicated tower projections. Every tower-level join should use these
    # rather than `dove` or `towers` directly -- see decisions/001.
    conn.executescript((SCHEMA_DIR / "007_init_tower_views.sql").read_text())
    conn.commit()

    # CompLib compositions. Loaded from the committed CSVs in data/complib/ so
    # the replica is reproducible from the repository without hitting the API.
    # The API walk that produced those CSVs is scripts/ingest_complib.py; this
    # is its offline mirror, the same shape as the BellBoard CSV load above.
    complib_dir = ROOT / "data" / "complib"
    if (complib_dir / "compositions.csv").exists():
        run([SCRIPTS / "load_complib_csv.py", "--init", "--local-db", out])
    else:
        # Create the tables empty so schema checks behave the same as a full build.
        conn = libsql.connect(str(out))
        conn.executescript((SCHEMA_DIR / "006_init_complib.sql").read_text())
        conn.commit()
        print("\nCompLib tables created but left empty "
              "(no committed CSVs in data/complib/).")

    if not args.skip_adjudication and ADJUDICATION.exists():
        accepted = [
            d for d in csv.DictReader(open(ADJUDICATION, encoding="utf-8"))
            if d["decision"] == "accept"
        ]
        conn.executescript(
            'DROP TABLE IF EXISTS "_loc_map";'
            'CREATE TABLE "_loc_map" ("k" TEXT PRIMARY KEY, "tower_id" INTEGER);'
        )
        rows = [[LOC_KEY(d["building"], d["town"], d["county"]),
                 int(d["candidate_tower_id"])] for d in accepted]
        for i in range(0, len(rows), 4000):
            chunk = rows[i : i + 4000]
            conn.execute(
                'INSERT OR REPLACE INTO "_loc_map" ("k","tower_id") VALUES '
                + ", ".join(["(?, ?)"] * len(chunk)),
                [v for r in chunk for v in r],
            )
        conn.execute(
            'UPDATE "method_performances" SET "dove_tower_id" = ('
            '  SELECT m."tower_id" FROM "_loc_map" m WHERE m."k" = '
            "    COALESCE(\"method_performances\".\"building\",'') || '|' ||"
            "    COALESCE(\"method_performances\".\"town\",'')     || '|' ||"
            "    COALESCE(\"method_performances\".\"county\",''))"
        )
        conn.executescript('DROP TABLE IF EXISTS "_loc_map";')
        conn.commit()
        print(f"\nApplied {len(accepted)} adjudicated tower links.")

    # Performance -> method linkage. Only meaningful when BellBoard rows exist,
    # so it is skipped rather than run against an empty table -- a resolver that
    # reports 0 links because there was nothing to link looks identical to one
    # that reports 0 because it is broken.
    if not args.skip_method_linkage:
        n_perf = conn.execute("SELECT COUNT(*) FROM performances").fetchone()[0]
        if n_perf:
            conn.executescript(
                (SCHEMA_DIR / "005_init_performance_methods.sql").read_text())
            conn.commit()
            conn.close()
            # run() already prepends sys.executable. Passing it here too made
            # argv [python3, python3, resolver.py, ...], so Python was handed its
            # own ELF binary as a source file and died with "source code cannot
            # contain null bytes" -- while the echoed command line above looked
            # perfectly correct, because run() prints cmd without the prefix it
            # adds. The linkage step has therefore never run inside a build; the
            # populated tables came from running the resolver by hand.
            run([str(ROOT / "scripts" / "resolve_performance_methods.py"),
                 "--local-db", str(out), "--reset"])
            conn = libsql.connect(str(out))
        else:
            conn.executescript(
                (SCHEMA_DIR / "005_init_performance_methods.sql").read_text())
            conn.commit()
            print("\nMethod-linkage tables created but left empty "
                  "(no BellBoard performances loaded).")

    print(f"\n{'='*60}\nOffline replica ready: {out}\n{'='*60}")
    for t in ("dove", "bells", "towers", "frames", "founders", "regions", "changes",
              "methods", "method_performances", "performances"):
        try:
            n = conn.execute(f'SELECT COUNT(*) FROM "{t}"').fetchall()[0][0]
            print(f"  {t:22s} {n:>7,}")
        except Exception:
            print(f"  {t:22s}  (absent)")
    linked = conn.execute(
        'SELECT COUNT(*) FROM "method_performances" WHERE "dove_tower_id" IS NOT NULL'
    ).fetchall()[0][0]
    print(f"  {'  of which tower-linked':22s} {linked:>7,}")
    conn.close()

    print(f"\nUse it with any script:  --local-db {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
