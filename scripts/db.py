"""
Shared database connection handling for this project's scripts.

Two things live here: the --local-db switch that lets every loader target a
local file instead of Turso, and the interlock that stops a script reaching
production by accident.

Why local mode uses libsql rather than sqlite3
----------------------------------------------
It would be easier to open local files with the stdlib sqlite3 module, and the
first version of ingest_methods.py did. That is a trap. Three bugs in this
project were invisible under sqlite3 and only appeared against Turso, and one
of them -- a double-quoted SQL string literal, which sqlite3 silently accepts
as a string and libSQL rejects as an unresolvable identifier -- shipped to
production because local testing had passed.

An embedded libsql connection rejects it exactly as the server does. Using
libsql for local work therefore makes the offline replica a real check rather
than an approximate one.

One difference remains: NaN parameter binding is accepted by both the stdlib
and embedded libsql, because the rejection happens in the Hrana JSON layer
that only a remote connection uses. Converting NaN to None is still something
you must get right by inspection -- see the comment in migrate_csv_to_turso.py.

The production interlock
------------------------
Scripts refuse to open a remote connection unless
CHANGE_RINGING_ALLOW_PRODUCTION=1 is set. The database is metered on rows read
and has been frozen once already after a 591-million-read day, so the default
path is local and reaching production is a deliberate act.
"""
import os
import sys

try:
    import libsql
except ImportError:
    import sqlite3 as libsql

ALLOW_ENV = "CHANGE_RINGING_ALLOW_PRODUCTION"


def add_db_args(parser):
    parser.add_argument(
        "--local-db",
        metavar="PATH",
        help="Target a local SQLite/libSQL file instead of Turso. The offline "
        "replica built by scripts/build_local_db.py is the intended default "
        "for development; see docs/CONNECTING.md.",
    )
    return parser


def connect(args):
    """Open a connection based on --local-db, or Turso if explicitly allowed."""
    local = getattr(args, "local_db", None)
    if local:
        print(f"Using local database: {local}")
        return libsql.connect(local)

    url = os.environ.get("TURSO_DATABASE_URL")
    token = os.environ.get("TURSO_AUTH_TOKEN")
    if not url or not token:
        print(
            "ERROR: set TURSO_DATABASE_URL and TURSO_AUTH_TOKEN, or pass "
            "--local-db PATH to work against an offline replica.",
            file=sys.stderr,
        )
        raise SystemExit(1)

    if os.environ.get(ALLOW_ENV) != "1":
        print(
            f"REFUSING to connect to production.\n"
            f"  This database is metered on rows read and is currently frozen "
            f"(see README).\n"
            f"  Work offline:   --local-db local_corpus.db\n"
            f"  Build one with: python scripts/build_local_db.py\n"
            f"  To override deliberately: {ALLOW_ENV}=1",
            file=sys.stderr,
        )
        raise SystemExit(2)

    print(f"Connecting to production Turso database ({ALLOW_ENV}=1 set).")
    return libsql.connect(database=url, auth_token=token)
