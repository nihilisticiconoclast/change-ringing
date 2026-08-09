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
  schema/001..004   -- in this repo
  location linkage  -- data/method_location_adjudication.csv, in this repo

The one exception is BellBoard. Its corpus is only reachable through an API
that throttles by silently truncating responses, so it is not fetched unless
you ask with --bellboard-since, and even then only for the window you name.
A replica without it is still useful for anything touching Dove or the
Methods Library; a replica with a recent window matches what production
currently holds, which is a single window rather than the full history.

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
    print(f"\n$ {' '.join(str(c) for c in cmd)}")
    result = subprocess.run([sys.executable, *cmd])
    if result.returncode != 0:
        raise SystemExit(f"step failed: {' '.join(str(c) for c in cmd)}")


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
        
        total_p, total_r = 0, 0
        for p_csv in bb_perf_csvs:
            yr = p_csv.stem.split("_")[-1]
            r_csv = bb_dir / f"ringers_{yr}.csv"
            fn_csv = bb_dir / f"footnotes_{yr}.csv"

            # Load performances
            with open(p_csv, encoding="utf-8") as f:
                p_rows = list(csv.DictReader(f))
                if p_rows:
                    flds = list(p_rows[0].keys())
                    conn.executemany(
                        f"INSERT OR REPLACE INTO performances ({', '.join(flds)}) VALUES ({', '.join(['?']*len(flds))})",
                        [[r.get(k) for k in flds] for r in p_rows]
                    )
                    total_p += len(p_rows)

            # Load ringers
            if r_csv.exists():
                with open(r_csv, encoding="utf-8") as f:
                    r_rows = list(csv.DictReader(f))
                    if r_rows:
                        flds = list(r_rows[0].keys())
                        conn.executemany(
                            f"INSERT INTO performance_ringers ({', '.join(flds)}) VALUES ({', '.join(['?']*len(flds))})",
                            [[r.get(k) for k in flds] for r in r_rows]
                        )
                        total_r += len(r_rows)

            # Load footnotes
            if fn_csv.exists():
                with open(fn_csv, encoding="utf-8") as f:
                    fn_rows = list(csv.DictReader(f))
                    if fn_rows:
                        flds = list(fn_rows[0].keys())
                        conn.executemany(
                            f"INSERT INTO performance_footnotes ({', '.join(flds)}) VALUES ({', '.join(['?']*len(flds))})",
                            [[r.get(k) for k in flds] for r in fn_rows]
                        )

        conn.commit()
        conn.close()
        print(f"  Ingested {total_p:,} performances and {total_r:,} ringers from {len(bb_perf_csvs)} years.")
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
    conn.commit()

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
