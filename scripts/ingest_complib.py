#!/usr/bin/env python3
"""
Ingest the Composition Library (CompLib) into the Turso database (or local SQLite).

Prerequisites:
    pip install libsql
    export TURSO_DATABASE_URL="libsql://<your-db>.turso.io"
    export TURSO_AUTH_TOKEN="<your-token>"

Usage:
    # Ingest directly into Turso:
    python scripts/ingest_complib.py --init

    # Ingest into a local SQLite database for offline validation:
    python scripts/ingest_complib.py --init --local-db local_corpus.db

Source: Composition Library (CompLib), https://complib.org
API endpoint: https://api.complib.org/composition/search

Performance notes:
    Multi-row INSERT statements are used instead of executemany() to batch network
    round trips to Turso, maintaining a 16000 parameter budget per statement.
    Writes are idempotent: child rows are purged before re-inserting to prevent
    orphan/stale entries.
    Downloads are cached to data/complib/ to avoid hammering the API.
"""
import argparse
import json
import re
import db
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_API_URL = "https://api.complib.org/composition/search"
PARAM_BUDGET = 16000
USER_AGENT = (
    "change-ringing-corpus/0.1 (+https://github.com/nihilisticiconoclast/change-ringing)"
)


def fetch_json(url: str, retries: int = 3) -> bytes:
    """Download the JSON from the CompLib API."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    delay = 2
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                return resp.read()
        except (urllib.error.URLError, TimeoutError) as exc:
            if attempt == retries - 1:
                raise
            print(f"  download failed ({exc}); retrying in {delay}s ...", file=sys.stderr)
            time.sleep(delay)
            delay *= 2
    raise RuntimeError("Download failed: unreachable")


def insert_many(conn, table: str, cols: list, rows: list):
    """Multi-row INSERT OR REPLACE adhering to the SQLite parameter budget."""
    if not rows:
        return
    col_list = ", ".join(f'"{c}"' for c in cols)
    tup = "(" + ", ".join("?" for _ in cols) + ")"
    batch_size = max(1, min(500, PARAM_BUDGET // len(cols)))
    for i in range(0, len(rows), batch_size):
        batch = rows[i : i + batch_size]
        sql = (
            f'INSERT OR REPLACE INTO "{table}" ({col_list}) VALUES '
            + ", ".join([tup] * len(batch))
        )
        conn.execute(sql, [v for row in batch for v in row])


COMP_COLS = [
    "comp_id",
    "library",
    "title",
    "derived_title",
    "opus",
    "method_details",
    "date_composed",
    "stage",
    "length",
    "calling",
    "method_calling",
    "notes",
    "ingested_at",
]

COMPOSER_COLS = [
    "comp_id",
    "position",
    "role",
    "name",
]

METHOD_COLS = [
    "comp_id",
    "position",
    "method_title",
    "method_id",
]


def parse_page(data: dict):
    """Extract rows from a page of compositions."""
    now_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")
    comp_rows = []
    composer_rows = []
    method_rows = []

    for c in data.get("compositions", []):
        comp_id = c.get("id")
        if not comp_id:
            continue

        comp_rows.append([
            comp_id,
            c.get("library"),
            c.get("title"),
            c.get("derivedTitle"),
            c.get("opus"),
            c.get("methodDetails"),
            c.get("dateComposed"),
            c.get("stage"),
            c.get("length"),
            c.get("calling"),
            c.get("methodCalling"),
            c.get("notes"),
            now_iso,
        ])

        for pos, composer in enumerate(c.get("composerDetails", [])):
            composer_rows.append([
                comp_id,
                pos,
                composer.get("role"),
                composer.get("name"),
            ])

        for pos, method in enumerate(c.get("methodDefinitions", [])):
            method_rows.append([
                comp_id,
                pos,
                method.get("title"),
                None,  # method_id unpopulated pending resolution
            ])

    return comp_rows, composer_rows, method_rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest CompLib")
    parser.add_argument(
        "--init",
        action="store_true",
        help="Apply schema/005_init_complib.sql before ingesting",
    )
    parser.add_argument(
        "--schema",
        default=str(Path(__file__).parent.parent / "schema" / "005_init_complib.sql"),
        help="Path to 005_init_complib.sql schema file",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Drop existing complib tables declared in schema before loading",
    )
    parser.add_argument(
        "--limit-pages",
        type=int,
        default=None,
        help="Limit the number of pages to fetch (useful for dev/testing)",
    )
    db.add_db_args(parser)
    args = parser.parse_args()

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
    clashes = [name for _, name in owned if name in existing]

    if clashes and not (args.reset or args.init):
        pass
    elif args.reset:
        if clashes:
            print(f"Resetting: dropping {len(clashes)} existing object(s) ({', '.join(clashes)}) ...")
            for kind, name in sorted(owned, key=lambda o: o[0].upper() != "VIEW"):
                if name in existing:
                    conn.execute(f'DROP {kind.upper()} IF EXISTS "{name}"')
            conn.commit()
        print(f"Applying schema from {args.schema} ...")
        conn.executescript(schema_sql)
        conn.commit()
    elif args.init or not any(name in existing for name in ("compositions", "composition_composers", "composition_methods")):
        print(f"Applying schema from {args.schema} ...")
        conn.executescript(schema_sql)
        conn.commit()

    cache_dir = Path(__file__).parent.parent / "data" / "complib"
    cache_dir.mkdir(parents=True, exist_ok=True)

    page = 1
    per_page = 25
    total_pages = 1
    
    print("Fetching and parsing compositions from CompLib API ...")

    all_comp_rows = []
    all_composer_rows = []
    all_method_rows = []

    while page <= total_pages:
        if args.limit_pages and page > args.limit_pages:
            break
            
        cache_file = cache_dir / f"page_{page:04d}.json"
        
        if cache_file.exists():
            with open(cache_file, "rb") as f:
                raw_data = f.read()
        else:
            url = f"{DEFAULT_API_URL}?page={page}"
            raw_data = fetch_json(url)
            with open(cache_file, "wb") as f:
                f.write(raw_data)
            time.sleep(1) # Gentle with API
            
        data = json.loads(raw_data)
        
        if page == 1:
            total_count = data.get("count", 0)
            total_pages = (total_count + per_page - 1) // per_page
            print(f"  Total compositions: {total_count} ({total_pages} pages)")
            
        comp_rows, composer_rows, method_rows = parse_page(data)
        all_comp_rows.extend(comp_rows)
        all_composer_rows.extend(composer_rows)
        all_method_rows.extend(method_rows)
        
        print(f"  Processed page {page}/{total_pages}", end="\r")
        page += 1

    print(f"\n  Parsed {len(all_comp_rows):,} compositions.")

    print("Writing data to database ...")
    comp_ids = [r[0] for r in all_comp_rows]
    for chunk in (comp_ids[i : i + 400] for i in range(0, len(comp_ids), 400)):
        id_list = ",".join(f"{mid}" for mid in chunk)
        conn.execute(f'DELETE FROM "composition_composers" WHERE "comp_id" IN ({id_list})')
        conn.execute(f'DELETE FROM "composition_methods" WHERE "comp_id" IN ({id_list})')

    insert_many(conn, "compositions", COMP_COLS, all_comp_rows)
    insert_many(conn, "composition_composers", COMPOSER_COLS, all_composer_rows)
    insert_many(conn, "composition_methods", METHOD_COLS, all_method_rows)
    conn.commit()
    print("Ingestion complete. Verifying summary statistics ...\n")

    n_comps = conn.execute('SELECT COUNT(*) FROM "compositions"').fetchone()[0]
    n_meths = conn.execute('SELECT COUNT(*) FROM "composition_methods"').fetchone()[0]
    print(f"Total compositions in database: {n_comps:,}")
    print(f"Total composition_methods in database: {n_meths:,}\n")

    conn.close()
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
