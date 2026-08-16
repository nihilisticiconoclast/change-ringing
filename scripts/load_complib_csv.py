#!/usr/bin/env python3
"""
Load the committed CompLib CSVs into the database.

The API walk that produced `data/complib/*.csv` is run by
`scripts/ingest_complib.py` against the live `api.complib.org` endpoint and is
not repeatable in CI or on a machine without network access. This loader reads
the committed CSVs the same way `build_local_db.py` reads the committed
BellBoard CSVs, so a local replica can be rebuilt from the repository alone.

The CSVs are the corpus; the database is a build product of them. Writes are
INSERT OR REPLACE on CompLib's composition id (child rows cleared before
reinsert), so re-runs converge -- the same idempotency contract as the API
loader.

Usage:
    python scripts/load_complib_csv.py --init --local-db local_corpus.db
    python scripts/load_complib_csv.py --reset --local-db local_corpus.db

Apply schema/006_init_complib.sql first (or use --init).
"""
import argparse
import csv
import re
import sqlite3
from pathlib import Path

import db

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = ROOT / "schema" / "006_init_complib.sql"
DATA = ROOT / "data" / "complib"
COMPOSITIONS_CSV = DATA / "compositions.csv"
COMP_METHODS_CSV = DATA / "composition_methods.csv"

# Empty CSV cells read as '' by DictReader; stored as NULL so IS NULL checks
# behave the same as the API loader, which writes None for missing fields.
nz = lambda v: None if v == "" else v


def as_int(v):
    if v is None or v == "":
        return None
    s = str(v).strip()
    if s.lstrip("-").isdigit():
        return int(s)
    return None


# Columns whose schema type is INTEGER: CSV stores them as text, so coerce
# them back, matching what ingest_complib.parse_composition wrote.
INT_COLS_COMPOSITIONS = {
    "composition_id", "stage", "length", "extents", "backstroke_start",
}
INT_COLS_COMP_METHODS = {
    "composition_id", "position", "row_stage", "method_stage",
    "complib_method_id",
}


def load_csv(conn, path, table, int_cols):
    if not path.exists():
        print(f"  {path.name}: not found, skipping")
        return 0
    with open(path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        return 0
    flds = list(rows[0].keys())
    cols = ", ".join('"' + c + '"' for c in flds)

    def coerce(row):
        return [as_int(row[k]) if k in int_cols else nz(row[k]) for k in flds]

    conn.executemany(
        f'INSERT OR REPLACE INTO "{table}" ({cols}) '
        f"VALUES ({', '.join(['?'] * len(flds))})",
        [coerce(r) for r in rows],
    )
    return len(rows)


def main() -> int:
    ap = argparse.ArgumentParser(description="Load committed CompLib CSVs")
    ap.add_argument("--init", action="store_true",
                    help="Apply schema/006_init_complib.sql before loading")
    ap.add_argument("--schema", default=str(SCHEMA),
                    help="Path to 006_init_complib.sql schema file")
    ap.add_argument("--reset", action="store_true",
                    help="Drop existing CompLib tables before loading")
    db.add_db_args(ap)
    args = ap.parse_args()

    conn = db.connect(args)

    with open(args.schema, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    owned = re.findall(
        r'CREATE\s+(TABLE|VIEW)\s+"?([A-Za-z0-9_]+)"?', schema_sql, re.IGNORECASE
    )
    existing = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type IN ('table','view')"
        ).fetchall()
    }

    if args.reset:
        clashes = [name for _, name in owned if name in existing]
        if clashes:
            print(f"Resetting: dropping {len(clashes)} existing object(s) "
                  f"({', '.join(clashes)}) ...")
            for kind, name in sorted(owned, key=lambda o: 0 if o[0].lower() == "view" else 1):
                if name in existing:
                    conn.execute(f'DROP {kind.upper()} IF EXISTS "{name}"')
            conn.commit()
        print(f"Applying schema from {args.schema} ...")
        conn.executescript(schema_sql)
        conn.commit()
    elif args.init or not any(
        name in existing for name in ("compositions", "composition_methods")
    ):
        print(f"Applying schema from {args.schema} ...")
        conn.executescript(schema_sql)
        conn.commit()

    print("Loading committed CompLib CSVs ...")
    # Clear child rows first so a re-run converges (same contract as the API
    # loader: composition_methods are cleared per composition, but a full reload
    # from CSV replaces everything, so truncate both in dependency order).
    conn.execute('DELETE FROM "composition_methods"')
    conn.execute('DELETE FROM "compositions"')
    conn.commit()

    n1 = load_csv(conn, COMPOSITIONS_CSV, "compositions", INT_COLS_COMPOSITIONS)
    n2 = load_csv(conn, COMP_METHODS_CSV, "composition_methods", INT_COLS_COMP_METHODS)
    conn.commit()

    print(f"  compositions:        {n1:,}")
    print(f"  composition_methods: {n2:,}")

    # Verify against the source-of-truth CSV row counts.
    actual1 = conn.execute('SELECT COUNT(*) FROM "compositions"').fetchone()[0]
    actual2 = conn.execute('SELECT COUNT(*) FROM "composition_methods"').fetchone()[0]
    print(f"\nDatabase holds {actual1:,} compositions and {actual2:,} "
          f"composition-method rows.")

    ok = actual1 == n1 and actual2 == n2
    if not ok:
        print("MISMATCH: database row count does not match the CSVs.",
              flush=True)
        return 1
    print("OK -- database matches the committed CSVs.")
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
