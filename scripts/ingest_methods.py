#!/usr/bin/env python3
"""
Ingest the CCCBR Methods Library into the Turso database (or local SQLite).

Prerequisites:
    pip install libsql
    export TURSO_DATABASE_URL="libsql://<your-db>.turso.io"
    export TURSO_AUTH_TOKEN="<your-token>"
    # apply schema/003_init_methods.sql first (or use --init)

Usage:
    # Ingest directly into Turso:
    python scripts/ingest_methods.py --init

    # Ingest from a local pre-downloaded XML / zip file:
    python scripts/ingest_methods.py --xml-path ./methods-cache/CCCBR_methods.xml.zip

    # Ingest into a local SQLite database for offline validation:
    python scripts/ingest_methods.py --init --local-db local_corpus.db

Source: Central Council of Church Bell Ringers, https://methods.cccbr.org.uk
XML Specification: Method XML 1.0 (http://www.cccbr.org.uk/methods/schemas/2007/05/methods)

Performance notes:
    Multi-row INSERT statements are used instead of executemany() to batch network
    round trips to Turso, maintaining a 16000 parameter budget per statement.
    Writes are idempotent: child rows in method_performances are purged before
    re-inserting to prevent orphan/stale entries.
"""
import argparse
import io
import os
import re
import sqlite3
import sys
import time
import urllib.error
import urllib.request
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_XML_URL = "https://methods.cccbr.org.uk/xml/CCCBR_methods.xml.zip"
PARAM_BUDGET = 16000
USER_AGENT = (
    "change-ringing-corpus/0.1 (+https://github.com/nihilisticiconoclast/change-ringing)"
)
NS = "{http://www.cccbr.org.uk/methods/schemas/2007/05/methods}"


def text_of(elem):
    """Flatten element text and strip whitespace, returning None if empty."""
    if elem is None:
        return None
    s = "".join(elem.itertext()).strip()
    return s or None


def fetch_xml_bytes(url: str, retries: int = 3) -> bytes:
    """Download the methods XML (or zip archive) from the CCCBR server."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
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


def load_xml_root(xml_path: str = None, url: str = DEFAULT_XML_URL) -> ET.Element:
    """Read XML data from a local file or download from the CCCBR URL."""
    if xml_path:
        path = Path(xml_path)
        if not path.exists():
            raise FileNotFoundError(f"XML file not found: {xml_path}")
        print(f"Reading methods data from local path: {path} ...")
        if path.suffix.lower() == ".zip":
            with zipfile.ZipFile(path) as zf:
                xml_filename = [n for n in zf.namelist() if n.endswith(".xml")][0]
                with zf.open(xml_filename) as f:
                    return ET.parse(f).getroot()
        else:
            with open(path, "rb") as f:
                return ET.parse(f).getroot()

    print(f"Fetching methods archive from {url} ...")
    raw_data = fetch_xml_bytes(url)
    print(f"  downloaded {len(raw_data):,} bytes.")

    if raw_data.startswith(b"PK"):  # Zip archive
        with zipfile.ZipFile(io.BytesIO(raw_data)) as zf:
            xml_filename = [n for n in zf.namelist() if n.endswith(".xml")][0]
            with zf.open(xml_filename) as f:
                return ET.parse(f).getroot()
    else:
        return ET.fromstring(raw_data)


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


METHOD_COLS = [
    "method_id",
    "title",
    "name",
    "stage",
    "classification",
    "cls_plain",
    "cls_little",
    "cls_differential",
    "cls_treble_dodging",
    "length_of_lead",
    "number_of_hunts",
    "huntbell_path",
    "notation",
    "symmetry",
    "lead_head",
    "lead_head_code",
    "fch_groups",
    "rw_ref",
    "extension_construction",
    "notes",
    "ingested_at",
]

PERF_COLS = [
    "method_id",
    "position",
    "event_type",
    "perf_date",
    "society",
    "building",
    "town",
    "county",
    "address",
    "region",
    "country",
    "room",
    "dove_tower_id",
]


def parse_methods_collection(root: ET.Element):
    """Extract method rows and first-performance rows from the XML element tree."""
    now_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")
    method_rows = []
    perf_rows = []

    as_int = lambda v: int(v) if v is not None and str(v).strip().lstrip("-").isdigit() else None

    for ms in root.findall(f"{NS}methodSet"):
        props = ms.find(f"{NS}properties")
        stage = length_of_lead = number_of_hunts = huntbell_path = None
        classification = None
        cls_plain = cls_little = cls_differential = cls_treble_dodging = 0

        if props is not None:
            stage = as_int(text_of(props.find(f"{NS}stage")))
            length_of_lead = as_int(text_of(props.find(f"{NS}lengthOfLead")))
            number_of_hunts = as_int(text_of(props.find(f"{NS}numberOfHunts")))
            huntbell_path = text_of(props.find(f"{NS}huntbellPath"))

            cls_el = props.find(f"{NS}classification")
            if cls_el is not None:
                classification = cls_el.text.strip() if cls_el.text else None
                cls_attrib = cls_el.attrib
                cls_plain = 1 if cls_attrib.get("plain") == "true" else 0
                cls_little = 1 if cls_attrib.get("little") == "true" else 0
                cls_differential = 1 if cls_attrib.get("differential") == "true" else 0
                cls_treble_dodging = 1 if cls_attrib.get("trebleDodging") == "true" else 0

        for m in ms.findall(f"{NS}method"):
            method_id = m.get("id")
            if not method_id:
                continue

            title = text_of(m.find(f"{NS}title")) or ""
            name = text_of(m.find(f"{NS}name"))
            notation = text_of(m.find(f"{NS}notation"))
            symmetry = text_of(m.find(f"{NS}symmetry"))
            lead_head = text_of(m.find(f"{NS}leadHead"))
            lead_head_code = text_of(m.find(f"{NS}leadHeadCode"))
            extension_construction = text_of(m.find(f"{NS}extensionConstruction"))
            notes = text_of(m.find(f"{NS}notes"))

            fch_groups = None
            falseness_el = m.find(f"{NS}falseness")
            if falseness_el is not None:
                fch_groups = text_of(falseness_el.find(f"{NS}fchGroups"))

            rw_ref = None
            ref_el = m.find(f"{NS}references")
            if ref_el is not None:
                rw_ref = text_of(ref_el.find(f"{NS}rwRef"))

            method_rows.append([
                method_id,
                title,
                name,
                stage,
                classification,
                cls_plain,
                cls_little,
                cls_differential,
                cls_treble_dodging,
                length_of_lead,
                number_of_hunts,
                huntbell_path,
                notation,
                symmetry,
                lead_head,
                lead_head_code,
                fch_groups,
                rw_ref,
                extension_construction,
                notes,
                now_iso,
            ])

            perfs_el = m.find(f"{NS}performances")
            if perfs_el is not None:
                for pos, p in enumerate(perfs_el):
                    event_type = p.tag.split("}")[-1]
                    perf_date = text_of(p.find(f"{NS}date"))
                    society = text_of(p.find(f"{NS}society"))

                    loc_el = p.find(f"{NS}location")
                    building = town = county = address = region = country = room = None
                    if loc_el is not None:
                        building = text_of(loc_el.find(f"{NS}building"))
                        town = text_of(loc_el.find(f"{NS}town"))
                        county = text_of(loc_el.find(f"{NS}county"))
                        address = text_of(loc_el.find(f"{NS}address"))
                        region = text_of(loc_el.find(f"{NS}region"))
                        country = text_of(loc_el.find(f"{NS}country"))
                        room = text_of(loc_el.find(f"{NS}room"))

                    perf_rows.append([
                        method_id,
                        pos,
                        event_type,
                        perf_date,
                        society,
                        building,
                        town,
                        county,
                        address,
                        region,
                        country,
                        room,
                        None,  # dove_tower_id initially unpopulated
                    ])

    return method_rows, perf_rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest CCCBR Methods Library")
    parser.add_argument(
        "--init",
        action="store_true",
        help="Apply schema/003_init_methods.sql before ingesting",
    )
    parser.add_argument(
        "--schema",
        default=str(Path(__file__).parent.parent / "schema" / "003_init_methods.sql"),
        help="Path to 003_init_methods.sql schema file",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Drop existing methods tables declared in schema before loading",
    )
    parser.add_argument(
        "--xml-path",
        help="Path to local CCCBR_methods.xml or CCCBR_methods.xml.zip (bypasses download)",
    )
    parser.add_argument(
        "--url",
        default=DEFAULT_XML_URL,
        help="URL to fetch the CCCBR methods XML zip archive",
    )
    parser.add_argument(
        "--local-db",
        help="Target a local SQLite database file instead of remote Turso",
    )
    args = parser.parse_args()

    # Connection management
    if args.local_db:
        print(f"Connecting to local SQLite database: {args.local_db}")
        conn = sqlite3.connect(args.local_db)
    else:
        url = os.environ.get("TURSO_DATABASE_URL")
        token = os.environ.get("TURSO_AUTH_TOKEN")
        if not url or not token:
            print(
                "ERROR: set TURSO_DATABASE_URL and TURSO_AUTH_TOKEN in the environment, "
                "or pass --local-db for local SQLite operations.",
                file=sys.stderr,
            )
            return 1
        import libsql

        conn = libsql.connect(database=url, auth_token=token)

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
        # Tables already exist and neither --reset nor --init was specified
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
    elif args.init or not any(name in existing for name in ("methods", "method_performances")):
        print(f"Applying schema from {args.schema} ...")
        conn.executescript(schema_sql)
        conn.commit()

    # Parse source XML
    root = load_xml_root(xml_path=args.xml_path, url=args.url)
    print("Parsing methods and first-performance events from XML ...")
    method_rows, perf_rows = parse_methods_collection(root)
    print(f"  Parsed {len(method_rows):,} methods and {len(perf_rows):,} performance events.")

    # Idempotent write: delete child rows before reinserting
    print("Writing data to database ...")
    method_ids = [r[0] for r in method_rows]
    for chunk in (method_ids[i : i + 400] for i in range(0, len(method_ids), 400)):
        id_list = ",".join(f"'{mid}'" for mid in chunk)
        conn.execute(f'DELETE FROM "method_performances" WHERE "method_id" IN ({id_list})')

    insert_many(conn, "methods", METHOD_COLS, method_rows)
    insert_many(conn, "method_performances", PERF_COLS, perf_rows)
    conn.commit()
    print("Ingestion complete. Verifying summary statistics ...\n")

    # Verification report
    n_methods = conn.execute('SELECT COUNT(*) FROM "methods"').fetchone()[0]
    n_perfs = conn.execute('SELECT COUNT(*) FROM "method_performances"').fetchone()[0]
    print(f"Total methods in database: {n_methods:,}")
    print(f"Total first performances in database: {n_perfs:,}\n")

    print("Methods by Classification:")
    cls_counts = conn.execute(
        'SELECT COALESCE(classification, "(None / Principle)"), COUNT(*) '
        'FROM "methods" '
        'GROUP BY classification '
        'ORDER BY COUNT(*) DESC'
    ).fetchall()
    for cls_name, count in cls_counts:
        print(f"  {cls_name:<25} {count:>6}")

    print("\nTop 10 First-Performance Event Types:")
    event_counts = conn.execute(
        'SELECT event_type, COUNT(*) '
        'FROM "method_performances" '
        'GROUP BY event_type '
        'ORDER BY COUNT(*) DESC LIMIT 10'
    ).fetchall()
    for ev_name, count in event_counts:
        print(f"  {ev_name:<40} {count:>6}")

    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
