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

    HAVE_LIBSQL = True
except ImportError:
    # Fallback so the scripts still run where libsql is not installed. It comes
    # at a real cost, so it announces itself rather than degrading quietly:
    # stdlib sqlite3 accepts SQL that libSQL rejects, which is the whole reason
    # local mode uses libsql. Under this fallback a local run is a weaker check
    # than the module docstring above promises.
    import sqlite3 as libsql

    HAVE_LIBSQL = False

ALLOW_ENV = "CHANGE_RINGING_ALLOW_PRODUCTION"


def _warn_fallback():
    if not HAVE_LIBSQL:
        print(
            "WARNING: libsql is not installed; falling back to stdlib sqlite3.\n"
            "  Local runs will NOT catch libSQL dialect errors -- notably a\n"
            "  double-quoted string literal, which sqlite3 accepts and libSQL\n"
            "  rejects. That exact bug reached production once already.\n"
            "  Install it for a real check:  pip install -r requirements.txt",
            file=sys.stderr,
        )


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
        _warn_fallback()
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

    if not HAVE_LIBSQL:
        # sqlite3.connect has no auth_token parameter, so without libsql this
        # would fail with an opaque TypeError. Say why instead.
        print(
            "ERROR: libsql is required to reach Turso and is not installed.\n"
            "  pip install -r requirements.txt",
            file=sys.stderr,
        )
        raise SystemExit(1)

    print(f"Connecting to production Turso database ({ALLOW_ENV}=1 set).")
    return libsql.connect(database=url, auth_token=token)
