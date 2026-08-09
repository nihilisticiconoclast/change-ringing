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

    print(f"Applying schema from {args.schema} ...")
    with open(args.schema) as f:
        schema_sql = f.read()
    for statement in schema_sql.split(";"):
        statement = statement.strip()
        if statement:
            conn.execute(statement)
    conn.commit()

    for name in FILES:
        path = csv_dir / f"{name}.csv"
        df = pd.read_csv(path, encoding="utf-8-sig", low_memory=False)
        df = clean_cols(df)
        cols = list(df.columns)
        placeholders = ", ".join("?" for _ in cols)
        col_list = ", ".join(f'"{c}"' for c in cols)
        insert_sql = f'INSERT INTO "{name}" ({col_list}) VALUES ({placeholders})'

        print(f"Loading {name}.csv -> {len(df)} rows ...")
        # Convert NaN to None so libsql binds NULL rather than the literal string "nan"
        records = df.where(pd.notna(df), None).values.tolist()
        for i in range(0, len(records), 500):
            batch = records[i : i + 500]
            for row in batch:
                conn.execute(insert_sql, row)
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
