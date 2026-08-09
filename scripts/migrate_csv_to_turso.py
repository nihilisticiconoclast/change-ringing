#!/usr/bin/env python3
"""
Load the seven Dove's Guide CSVs into a Turso (libSQL) database.

Prerequisites:
    pip install libsql pandas
    export TURSO_DATABASE_URL="libsql://<your-db>.turso.io"
    export TURSO_AUTH_TOKEN="<your-token>"

Usage:
    python scripts/migrate_csv_to_turso.py --csv-dir /path/to/csvs

Source data: Dove's Guide for Church Bell Ringers, https://dove.cccbr.org.uk
Licence: CC BY-SA 4.0 -- see data/SOURCES.md for attribution requirements.

This script is idempotent for schema (CREATE TABLE IF NOT EXISTS-style guards
are not used deliberately -- re-running against a populated database is
expected to fail loudly rather than silently duplicate rows; drop and
re-create if you need a clean reload).
"""
import argparse
import os
import re
import sys
from pathlib import Path

import pandas as pd
import libsql

FILES = ["bells", "changes", "dove", "founders", "frames", "regions", "towers"]

# Bind-parameter budget per INSERT statement, kept well under SQLite's 32766.
PARAM_BUDGET = 16000


def clean_cols(df: pd.DataFrame) -> pd.DataFrame:
    """Match the sanitisation used when the schema in schema/001_init_dove_bells.sql
    was generated, so DataFrame columns line up with the target table columns."""
    df.columns = [
        re.sub(r"[^0-9a-zA-Z_]", "_", c.strip()).strip("_") for c in df.columns
    ]
    return df


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--csv-dir",
        required=True,
        help="Directory containing bells.csv, changes.csv, dove.csv, founders.csv, "
        "frames.csv, regions.csv, towers.csv",
    )
    parser.add_argument(
        "--schema",
        default=str(Path(__file__).parent.parent / "schema" / "001_init_dove_bells.sql"),
        help="Path to the schema SQL file to apply before loading data",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Drop the seven Dove tables (and dependent views) before loading. "
        "Required to re-run against a populated database: Dove's export is a "
        "full snapshot, so a refresh is a drop-and-reload, not an append.",
    )
    args = parser.parse_args()

    url = os.environ.get("TURSO_DATABASE_URL")
    token = os.environ.get("TURSO_AUTH_TOKEN")
    if not url or not token:
        print(
            "ERROR: set TURSO_DATABASE_URL and TURSO_AUTH_TOKEN in the environment.",
            file=sys.stderr,
        )
        return 1

    csv_dir = Path(args.csv_dir)
    missing = [f for f in FILES if not (csv_dir / f"{f}.csv").exists()]
    if missing:
        print(f"ERROR: missing CSVs in {csv_dir}: {missing}", file=sys.stderr)
        return 1

    conn = libsql.connect(database=url, auth_token=token)

    with open(args.schema) as f:
        schema_sql = f.read()

    # Only ever drop objects this schema file declares, so a --reset cannot
    # take out tables or views someone else added to the database.
    owned = re.findall(
        r'CREATE\s+(TABLE|VIEW)\s+"?([A-Za-z0-9_]+)"?', schema_sql, re.IGNORECASE
    )
    existing = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type IN ('table','view')"
        ).fetchall()
    }
    clashes = [name for _, name in owned if name in existing]

    if clashes and not args.reset:
        print(
            f"ERROR: these objects already exist: {', '.join(sorted(clashes))}.\n"
            "Dove's export is a full snapshot, so refreshing it means dropping and\n"
            "reloading -- appending would duplicate every row. Re-run with --reset\n"
            "to drop the schema's own tables and views first.",
            file=sys.stderr,
        )
        return 1

    if args.reset:
        if clashes:
            print(f"Resetting: dropping {len(clashes)} existing object(s) ...")
            # Views first: dropping a table out from under a view leaves the
            # view behind as a broken definition.
            for kind, name in sorted(owned, key=lambda o: o[0].upper() != "VIEW"):
                if name in existing:
                    conn.execute(f'DROP {kind.upper()} IF EXISTS "{name}"')
            conn.commit()
        else:
            print("Reset requested; nothing to drop.")

    print(f"Applying schema from {args.schema} ...")
    # executescript handles statement splitting itself. Splitting on ";" by hand
    # breaks on semicolons inside the schema's own -- comments.
    conn.executescript(schema_sql)
    conn.commit()

    for name in FILES:
        path = csv_dir / f"{name}.csv"
        df = pd.read_csv(path, encoding="utf-8-sig", low_memory=False)
        df = clean_cols(df)
        cols = list(df.columns)
        row_tuple = "(" + ", ".join("?" for _ in cols) + ")"
        col_list = ", ".join(f'"{c}"' for c in cols)
        insert_prefix = f'INSERT INTO "{name}" ({col_list}) VALUES '

        # Keep each statement under SQLite's variable ceiling (32766 for
        # 3.32+); PARAM_BUDGET leaves generous headroom.
        batch_size = max(1, min(500, PARAM_BUDGET // len(cols)))

        print(f"Loading {name}.csv -> {len(df)} rows ...")
        # Convert NaN to None so libsql binds NULL. The astype(object) is load
        # bearing: .where(..., None) on a float64 column coerces None straight
        # back to NaN, leaving NaN in the params. Local SQLite hides this by
        # storing NaN as NULL, but Turso serialises it to JSON null and rejects
        # it against the column's f64 type.
        records = df.astype(object).where(pd.notna(df), None).values.tolist()
        # One multi-row INSERT per batch, committed once per table. The client's
        # executemany() issues a round trip per row against a remote primary
        # (measured at ~4 rows/s, and it stalls outright on long runs); folding
        # the rows into a single VALUES list runs at ~1300 rows/s.
        for i in range(0, len(records), batch_size):
            batch = records[i : i + batch_size]
            sql = insert_prefix + ", ".join([row_tuple] * len(batch))
            conn.execute(sql, [v for row in batch for v in row])
        conn.commit()
        print(f"  done: {name}")

    print("Migration complete. Verifying row counts ...")
    for name in FILES:
        n = conn.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0]
        print(f"  {name}: {n}")

    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
