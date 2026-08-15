#!/usr/bin/env python3
"""
Ingest CompLib (Composition Library) compositions into the database.

CompLib publishes a JSON API at https://api.complib.org, documented by an
OpenAPI spec at https://complib.org/complib.api.yml (rendered at
https://complib.org/api via Redoc). This loader walks the composition corpus
page by page and loads it, mirroring the structure of ingest_methods.py.

Prerequisites:
    pip install libsql
    # For production: export TURSO_DATABASE_URL, TURSO_AUTH_TOKEN, and CHANGE_RINGING_ALLOW_PRODUCTION=1
    # For local: use --local-db PATH (a replica built by build_local_db.py)
    # apply schema/006_init_complib.sql first (or use --init)

Usage:
    # Create the CompLib tables (once) and ingest into a local replica:
    python scripts/ingest_complib.py --init --local-db local_corpus.db

    # Drop and reload (idempotent; writes are INSERT OR REPLACE on CompLib's id):
    python scripts/ingest_complib.py --reset --local-db local_corpus.db

    # Bounded run for testing -- fetch only N pages of 25:
    python scripts/ingest_complib.py --local-db local_corpus.db --max-pages 4

    # Also fetch each composition's /rows to record CompLib's methodid and
    # resolve the CCCBR method_id by the 'm'+id rule. This costs one extra
    # request per composition, so it is off by default:
    python scripts/ingest_complib.py --local-db local_corpus.db --fetch-method-ids

Source: Composition Library, https://complib.org
API: https://api.complib.org (OpenAPI: https://complib.org/complib.api.yml)

What the API actually offers (verified 2026-08-15, and where it differs from
the spec):
- GET /composition/search?page=N&perpage=N returns {count, page, perpage,
  compositions[]}. The spec says perpage defaults to 25; it does NOT state a
  maximum, but the server enforces one: perpage > 25 returns HTTP 400
  "perpage maximum 25". So a full corpus of ~86,000 compositions is ~3,400+
  pages at 25/page.
- A Composition carries methodDefinitions[], each with a free-text method
  `title` and `placeNotation` -- NOT a CCCBR method identifier.
- GET /composition/{id}/rows returns a `methodid` for single-method
  compositions (null for spliced). That integer corresponds to the CCCBR
  method_id by method_id = 'm' || methodid (11/12 sampled resolved). It is
  recorded as complib_method_id; method_id is populated by that exact lookup
  only, never by fuzzy matching.

Be gentle with the API: page responses are cached to disk under --cache-dir
(default complib-cache/), the per-page delay defaults to 0.5s, and the search
order is whatever CompLib returns (not sequential ids), so all pages must be
walked.
"""
import argparse
import io
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import db

DEFAULT_API_BASE = "https://api.complib.org"
DEFAULT_CACHE_DIR = "complib-cache"
DEFAULT_PAGE_DELAY = 0.5  # seconds between search pages
DEFAULT_ROWS_DELAY = 0.3  # seconds between /rows fetches in the enrichment pass
PERPAGE = 25  # server-enforced maximum; see module docstring
PARAM_BUDGET = 16000
USER_AGENT = (
    "change-ringing-corpus/0.1 (+https://github.com/nihilisticiconoclast/change-ringing)"
)


def fetch_bytes(url, retries=4):
    """Fetch a URL with retries. Returns bytes; raises RuntimeError on failure."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    delay = 2
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                return resp.read()
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            if attempt == retries - 1:
                raise RuntimeError(f"Failed to fetch {url} after {retries} attempts: {exc}") from exc
            print(f"  fetch failed ({exc}); retrying in {delay}s", file=sys.stderr)
            time.sleep(delay)
            delay *= 2
    raise RuntimeError("unreachable")


def cache_path_for(cache_dir, kind, key):
    """Stable filesystem path for a cached fetch. kind in {'search','rows'}."""
    safe = re.sub(r"[^0-9A-Za-z._-]", "_", str(key))
    return Path(cache_dir) / kind / f"{safe}.json"


def fetch_json_cached(url, cache_dir, kind, key, delay, retries=4, use_cache=True):
    """Fetch JSON, caching to disk so re-runs do not re-hit the API.

    A cached file is reused as-is when use_cache is set; otherwise the URL is
    fetched, stored, and returned. The delay is applied after a real fetch
    only (cache hits cost nothing).
    """
    p = cache_path_for(cache_dir, kind, key) if cache_dir else None
    if use_cache and p and p.exists():
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    raw = fetch_bytes(url, retries)
    if p:
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "wb") as f:
            f.write(raw)
    if delay:
        time.sleep(delay)
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"could not parse JSON from {url}: {exc}") from exc


def insert_many(conn, table, cols, rows):
    """Multi-row INSERT OR REPLACE under the SQLite bind-parameter budget.

    Mirrors bellboard_common.insert_many / ingest_methods.insert_many:
    executemany() costs a round trip per row against a remote primary, so a
    single multi-VALUES statement is used instead, batched to stay under the
    32766 / PARAM_BUDGET ceiling.
    """
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


COMPOSITION_COLS = [
    "composition_id", "library", "derived_title", "title", "opus", "stage",
    "length", "date_composed", "extents", "backstroke_start",
    "call_default_specifier", "calling", "method_calling", "method_details",
    "partheads", "coursehead_masks", "notes", "ingested_at",
]

COMP_METHOD_COLS = [
    "composition_id", "position", "name", "method_title", "mnemonic",
    "place_notation", "method_place_notation", "row_stage", "method_stage",
    "complib_method_id", "method_id",
]


def as_int(v):
    if v is None:
        return None
    if isinstance(v, bool):
        return int(v)
    s = str(v).strip()
    if s.lstrip("-").isdigit():
        return int(s)
    return None


def json_join(v):
    """Compact a list to a '|' -joined string for storage, or NULL."""
    if v is None:
        return None
    if isinstance(v, str):
        return v or None
    if isinstance(v, (list, tuple)):
        parts = [str(x) for x in v if x is not None]
        return "|".join(parts) if parts else None
    return None


def parse_composition(c, now_iso):
    """Flatten one composition JSON dict into a compositions row."""
    return [
        as_int(c.get("id")),
        c.get("library"),
        c.get("derivedTitle"),
        c.get("title"),
        c.get("opus") or None,
        as_int(c.get("stage")),
        as_int(c.get("length")),
        c.get("dateComposed") or None,
        as_int(c.get("extents")),
        1 if c.get("backstrokeStart") else 0,
        c.get("callDefaultSpecifier"),
        c.get("calling"),
        c.get("methodCalling"),
        c.get("methodDetails"),
        json_join(c.get("partheads")),
        json_join(c.get("courseheadMasks")),
        c.get("notes") or None,
        now_iso,
    ]


def parse_method_definitions(comp_id, c):
    """Flatten a composition's methodDefinitions into child rows.

    method_id (the CCCBR soft reference) is left NULL here and filled by
    resolve_method_ids() once complib_method_id is known, because the
    methodid comes from the /rows endpoint, not the search payload.
    """
    rows = []
    for pos, md in enumerate(c.get("methodDefinitions") or []):
        rows.append([
            comp_id,
            pos,
            md.get("name") or None,
            md.get("title") or None,
            md.get("mnemonic") or None,
            md.get("placeNotation") or None,
            md.get("methodPlaceNotation") or None,
            as_int(md.get("rowStage")),
            as_int(md.get("methodStage")),
            None,   # complib_method_id -- filled from /rows if --fetch-method-ids
            None,   # method_id -- filled by resolve_method_ids()
        ])
    return rows


def fetch_search_page(api_base, page, cache_dir, delay, use_cache=True):
    """Fetch one page of /composition/search, returning the parsed dict."""
    url = f"{api_base}/composition/search?page={page}&perpage={PERPAGE}"
    return fetch_json_cached(url, cache_dir, "search", f"page_{page:06d}", delay, use_cache=use_cache)


def fetch_rows(api_base, comp_id, cache_dir, delay, use_cache=True):
    """Fetch /composition/{id}/rows, returning the parsed dict (or None)."""
    url = f"{api_base}/composition/{comp_id}/rows"
    try:
        return fetch_json_cached(url, cache_dir, "rows", f"comp_{comp_id}", delay, use_cache=use_cache)
    except RuntimeError as exc:
        print(f"  WARN: could not fetch rows for composition {comp_id}: {exc}",
              file=sys.stderr)
        return None


def resolve_method_ids(conn, comp_method_rows):
    """Populate the CCCBR method_id on child rows by the 'm'+complib_method_id
    exact-identifier rule, where complib_method_id is known.

    This is NOT fuzzy title matching: it is a direct identifier lookup, the
    same shape of linkage as BellBoard's dove-tower-id. Rows whose
    complib_method_id is NULL (spliced compositions, or rows fetched without
    --fetch-method-ids) keep method_id NULL, leaving the free-text
    method_title as the only linkage for downstream resolution.
    """
    # Build {complib_method_id: 'm'+id} only for ids present in the methods
    # table, so unresolved ids stay NULL without per-row queries.
    ids = {r[9] for r in comp_method_rows if r[9] is not None}
    if not ids:
        return comp_method_rows
    present = set()
    for chunk_start in range(0, len(ids), 400):
        chunk = list(ids)[chunk_start:chunk_start + 400]
        placeholders = ",".join("?" for _ in chunk)
        rows = conn.execute(
            f'SELECT "method_id" FROM "methods" '
            f'WHERE "method_id" IN ({placeholders})',
            [f"m{i}" for i in chunk],
        ).fetchall()
        present.update(r[0] for r in rows)
    out = []
    for r in comp_method_rows:
        cmid = r[9]
        mid = None
        if cmid is not None and f"m{cmid}" in present:
            mid = f"m{cmid}"
        out.append(r[:9] + [cmid, mid])
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest CompLib compositions")
    parser.add_argument(
        "--init",
        action="store_true",
        help="Apply schema/006_init_complib.sql before ingesting",
    )
    parser.add_argument(
        "--schema",
        default=str(Path(__file__).parent.parent / "schema" / "006_init_complib.sql"),
        help="Path to 006_init_complib.sql schema file",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Drop existing CompLib tables declared in schema before loading",
    )
    parser.add_argument(
        "--api-base",
        default=DEFAULT_API_BASE,
        help=f"CompLib API base URL (default: {DEFAULT_API_BASE})",
    )
    parser.add_argument(
        "--cache-dir",
        default=DEFAULT_CACHE_DIR,
        help=f"Directory for cached API responses (default: {DEFAULT_CACHE_DIR})",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Do not read or write the on-disk cache (always fetch from the API)",
    )
    parser.add_argument(
        "--page-delay",
        type=float,
        default=DEFAULT_PAGE_DELAY,
        help=f"Seconds between search page fetches (default: {DEFAULT_PAGE_DELAY})",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=0,
        help="Maximum search pages to fetch (0 = no limit, useful for testing)",
    )
    parser.add_argument(
        "--max-compositions",
        type=int,
        default=0,
        help="Maximum compositions to load (0 = no limit, useful for testing)",
    )
    parser.add_argument(
        "--fetch-method-ids",
        action="store_true",
        help="Also fetch /composition/{id}/rows per composition to record "
             "CompLib's methodid and resolve the CCCBR method_id by the "
             "'m'+id rule. Costs one extra request per composition.",
    )
    parser.add_argument(
        "--rows-delay",
        type=float,
        default=DEFAULT_ROWS_DELAY,
        help=f"Seconds between /rows fetches (default: {DEFAULT_ROWS_DELAY})",
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

    if args.reset:
        if clashes:
            print(f"Resetting: dropping {len(clashes)} existing object(s) ({', '.join(clashes)}) ...")
            # Drop views before tables; schema declares the view last among
            # owned objects, so dropping in reverse creation order is safe.
            for kind, name in sorted(owned, key=lambda o: 0 if o[0].lower() == "view" else 1):
                if name in existing:
                    conn.execute(f'DROP {kind.upper()} IF EXISTS "{name}"')
            conn.commit()
        print(f"Applying schema from {args.schema} ...")
        conn.executescript(schema_sql)
        conn.commit()
    elif args.init or not any(name in existing for name in ("compositions", "composition_methods")):
        print(f"Applying schema from {args.schema} ...")
        conn.executescript(schema_sql)
        conn.commit()

    use_cache = not args.no_cache
    cache_dir = args.cache_dir

    # --- Walk the search pages ---
    total_count = None
    comp_rows = []
    comp_method_rows = []
    pages_fetched = 0
    now_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")

    # Fetch page 1 to learn the corpus count and validate the API.
    print(f"Fetching search page 1 from {args.api_base}/composition/search ...")
    data = fetch_search_page(args.api_base, 1, cache_dir, args.page_delay, use_cache)
    pages_fetched += 1
    total_count = data.get("count")
    perpage = data.get("perpage", PERPAGE)
    print(f"  Corpus reports {total_count:,} compositions; perpage={perpage} "
          f"(server max 25).")

    def accumulate(page_data):
        nonlocal comp_method_rows
        comps = page_data.get("compositions") or []
        for c in comps:
            cid = as_int(c.get("id"))
            if cid is None:
                continue
            comp_rows.append(parse_composition(c, now_iso))
            comp_method_rows.extend(parse_method_definitions(cid, c))

    accumulate(data)

    # The API's page count for a full walk. Stop early if --max-pages or
    # --max-compositions is set.
    if total_count and perpage:
        full_pages = (total_count + perpage - 1) // perpage
    else:
        full_pages = 1

    page_limit = args.max_pages if args.max_pages else full_pages
    print(f"  Will fetch up to {page_limit} page(s) "
          f"({'all' if not args.max_pages else '--max-pages ' + str(args.max_pages)}).")

    page = 2
    incomplete = None      # set to a reason string if the walk stops early
    while page <= page_limit:
        if args.max_compositions and len(comp_rows) >= args.max_compositions:
            print(f"  Reached --max-compositions {args.max_compositions}; stopping.")
            break
        print(f"  Fetching search page {page}/{full_pages} ...")
        try:
            pdata = fetch_search_page(args.api_base, page, cache_dir, args.page_delay, use_cache)
        except RuntimeError as exc:
            # Write what we have -- the cache and the loaded rows are worth
            # keeping, and a resumed run reuses them -- but REMEMBER that the
            # corpus is incomplete, and exit non-zero at the end.
            #
            # This used to break and `return 0`. A run that failed on page 40 of
            # 3,442 reported success and left a partial CompLib load in the
            # database, which is indistinguishable from a complete one to anyone
            # querying it afterwards. That is the same shape as the backfill that
            # captured 16% of BellBoard and exited clean (decision 002), and the
            # reason bellboard_common has a completeness gate at all.
            print(f"  ERROR fetching page {page}: {exc}", file=sys.stderr)
            print(f"  Stopping at page {page} of {full_pages}. Loaded pages are "
                  f"still written, but THIS LOAD IS INCOMPLETE and the run will "
                  f"exit non-zero.", file=sys.stderr)
            incomplete = f"fetch failed on page {page} of {full_pages}: {exc}"
            break
        pages_fetched += 1
        comps = pdata.get("compositions") or []
        if not comps:
            print(f"  Empty page {page}; reached the end of the corpus.")
            break
        accumulate(pdata)
        if len(comps) < perpage:
            # Last page is allowed to be short.
            break
        page += 1

    if args.max_compositions and len(comp_rows) > args.max_compositions:
        comp_rows = comp_rows[:args.max_compositions]
        keep_ids = {r[0] for r in comp_rows}
        comp_method_rows = [r for r in comp_method_rows if r[0] in keep_ids]

    print(f"\nFetched {pages_fetched} page(s); "
          f"parsed {len(comp_rows):,} compositions and "
          f"{len(comp_method_rows):,} method-definition rows.")

    # --- Optional enrichment: /rows per composition for the methodid ---
    if args.fetch_method_ids:
        print("\nFetching /composition/{id}/rows to record CompLib method ids ...")
        done = 0
        for r in comp_rows:
            cid = r[0]
            rows_data = fetch_rows(args.api_base, cid, cache_dir, args.rows_delay, use_cache)
            if rows_data is None:
                continue
            cmid = as_int(rows_data.get("methodid"))
            if cmid is None:
                continue
            # Attach to the first (primary) method-definition row for this comp.
            for mr in comp_method_rows:
                if mr[0] == cid:
                    mr[9] = cmid  # complib_method_id
                    break
            done += 1
            if done % 200 == 0:
                print(f"  ... {done:,} /rows fetches done")
        print(f"  Recorded CompLib method ids for {done:,} composition(s).")

        # Resolve the CCCBR method_id by the exact 'm'+id rule.
        print("Resolving CCCBR method_id by the 'm'+complib_method_id rule ...")
        comp_method_rows = resolve_method_ids(conn, comp_method_rows)
        resolved = sum(1 for r in comp_method_rows if r[10] is not None)
        print(f"  Resolved {resolved:,} of {len(comp_method_rows):,} "
              f"method-definition rows to a CCCBR method_id.")
    else:
        # Even without /rows, attempt resolution from any complib_method_id
        # already on the rows (none in the search-only path, but harmless).
        comp_method_rows = resolve_method_ids(conn, comp_method_rows)

    # --- Idempotent write ---
    print("\nWriting data to database ...")
    comp_ids = [r[0] for r in comp_rows]
    for chunk_start in range(0, len(comp_ids), 400):
        chunk = comp_ids[chunk_start:chunk_start + 400]
        id_list = ",".join(str(i) for i in chunk)
        conn.execute(
            f'DELETE FROM "composition_methods" WHERE "composition_id" IN ({id_list})'
        )
    insert_many(conn, "compositions", COMPOSITION_COLS, comp_rows)
    insert_many(conn, "composition_methods", COMP_METHOD_COLS, comp_method_rows)
    conn.commit()

    print("Ingestion complete. Verifying summary statistics ...\n")
    n_comps = conn.execute('SELECT COUNT(*) FROM "compositions"').fetchone()[0]
    n_cm = conn.execute('SELECT COUNT(*) FROM "composition_methods"').fetchone()[0]
    print(f"Total compositions in database: {n_comps:,}")
    print(f"Total composition-method rows:   {n_cm:,}")
    if args.fetch_method_ids:
        n_resolved = conn.execute(
            'SELECT COUNT(*) FROM "composition_methods" WHERE "method_id" IS NOT NULL'
        ).fetchone()[0]
        n_cmid = conn.execute(
            'SELECT COUNT(*) FROM "composition_methods" WHERE "complib_method_id" IS NOT NULL'
        ).fetchone()[0]
        print(f"  with a CompLib method id:      {n_cmid:,}")
        print(f"  resolved to a CCCBR method_id: {n_resolved:,}")

    print("\nCompositions by stage (top 10):")
    for stage, count in conn.execute(
        'SELECT COALESCE("stage", -1), COUNT(*) FROM "compositions" '
        'GROUP BY "stage" ORDER BY COUNT(*) DESC LIMIT 10'
    ).fetchall():
        print(f"  stage {stage:<4} {count:>6}")

    print("\nCompositions by library:")
    for lib, count in conn.execute(
        'SELECT COALESCE("library", \'(none)\'), COUNT(*) FROM "compositions" '
        'GROUP BY "library" ORDER BY COUNT(*) DESC'
    ).fetchall():
        print(f"  {lib:<12} {count:>6}")

    if args.fetch_method_ids and n_cm:
        print("\nTop 10 linked CCCBR methods by composition count:")
        for title, count in conn.execute(
            'SELECT m."title", COUNT(*) c FROM "composition_methods" cm '
            'JOIN "methods" m ON m."method_id" = cm."method_id" '
            'WHERE cm."method_id" IS NOT NULL '
            'GROUP BY m."method_id" ORDER BY c DESC LIMIT 10'
        ).fetchall():
            print(f"  {title:<35} {count:>6}")

    conn.close()

    if incomplete:
        print(f"\nINCOMPLETE LOAD: {incomplete}\n"
              f"  {len(comp_rows):,} compositions were written and the page cache is\n"
              f"  intact, so re-running resumes cheaply. Exiting non-zero so a\n"
              f"  caller cannot mistake a partial corpus for a whole one.",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
