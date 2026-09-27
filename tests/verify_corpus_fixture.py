#!/usr/bin/env python3
"""A minimal corpus replica that verify_corpus.py passes, in milliseconds.

The negative tests for R-44 break one check at a time, and each break needs a
database that everything ELSE in the checker still accepts -- otherwise a FAIL
proves nothing about the check it was aimed at. Building the real replica takes
~90 seconds and a network, so this module builds the smallest database the
checker calls healthy instead:

    51 checks -> 0 failures (and no SKIP the fixture could have avoided)

It applies the *committed* schema files rather than a retyped subset, so the
fixture cannot drift from schema/001..007 the way a hand-maintained CREATE
TABLE list would. The rows are then shaped around the invariants the checker
asserts, several of which are traps for a naive fixture:

  - `dove` repeats one TowerID across two rings and `towers` across a
    full-circle ring AND a chime, because the fan-out check FAILs if TowerID
    is ever unique and the join-identity check needs the fan-out to survive
    (decision 001);
  - `method_performances` cites one TowerID Dove has removed -- the R-48
    shape, which the real replica fails today, so the fixture's baseline is
    honest about the one check a fresh rebuild cannot pass;
  - `performances` carries a handbell row with no tower and a drift orphan
    under the 5,000 ceiling, the exact shapes decision 001 documents;
  - the CSV counts under `data/` match the table rows exactly, because
    check_csv_agreement is exact, not a range.

check_csv_agreement reads data/bellboard and data/complib by absolute path
from verify_corpus.py's own location, so running the checker against a
fixture needs the repository around it. `fixture_root()` copies the schema and
a distilled slice of the CSVs into a tempdir laid out like the repository
root; nothing is written to the real repository.
"""
import csv
import importlib.util
import shutil
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_DIR = REPO_ROOT / "schema"

# One row per check the checker reports, so a break can be asserted by the
# check's own name. Header lines for the distilled CSVs; the row bodies are
# written next to the inserts that must agree with them.
BB_PERF_HEADER = ("perf_id,bb_id,association,place,dedication,county,towerbase-id,"
                  "dove_tower_id,dove_ring_id,ring_type,tenor,portable,dumb_bells,"
                  "perf_date,duration,changes,method,title,details,composer,"
                  "composition,bb_timestamp,ingested_at")
BB_RINGER_HEADER = "perf_id,position,bell,name,conductor"
BB_FOOTNOTE_HEADER = "perf_id,position,footnote"
BB_FLAG_HEADER = "perf_id,position,flag_type,bell,flag_text"
CL_COMP_HEADER = ("composition_id,library,derived_title,title,opus,stage,length,"
                  "date_composed,extents,backstroke_start,call_default_specifier,"
                  "calling,method_calling,method_details,partheads,"
                  "coursehead_masks,notes,ingested_at")
CL_CM_HEADER = ("composition_id,position,name,method_title,mnemonic,place_notation,"
                "method_place_notation,row_stage,method_stage,complib_method_id,"
                "method_id")

# The three tower fixtures and their rows, kept together because the whole
# point of decision 001 is that these tables are NOT tower registers.
DOVE_ROWS = [
    # TowerID, RingID, RingType, Place, Dedicn, County, Country, Lat, Long, Bells, DoveID
    (101, 1, "Full circle", "Oxford", "St Mary", "Oxfordshire", "England", 51.75, -1.25, 8, "OXFORD-ST-MARY"),
    (101, 2, "Full circle", "Oxford", "St Mary", "Oxfordshire", "England", 51.75, -1.25, 6, "OXFORD-ST-MARY"),
    (102, 1, "Full circle", "Abingdon", "St Helen", "Berkshire", "England", 51.67, -1.28, 10, "ABINGDON-ST-HELEN"),
]
TOWERS_ROWS = [
    (101, 1, "Full circle", "Oxford", "St Mary", "Oxfordshire", "England", 51.75, -1.25, 8, "OXFORD-ST-MARY"),
    (101, 2, "Full circle", "Oxford", "St Mary", "Oxfordshire", "England", 51.75, -1.25, 6, "OXFORD-ST-MARY"),
    (102, 1, "Full circle", "Abingdon", "St Helen", "Berkshire", "England", 51.67, -1.28, 10, "ABINGDON-ST-HELEN"),
    (103, 1, "Full circle", "Bampton", "St Mary", "Devon", "England", 50.97, -3.48, 8, "BAMPTON-ST-MARY"),
    # A chime: in towers (the superset), not in dove (the ringing subset).
    (103, 2, "Chime", "Bampton", "St Mary", "Devon", "England", 50.97, -3.48, 3, "BAMPTON-ST-MARY"),
]
PERF_ROWS = [
    # perf_id, bb_id, place, dedication, county, dove_tower_id, ring_type,
    # perf_date, changes, method, title
    (1, "P1", "Oxford", "St Mary", "Oxfordshire", 101, "tower", "2024-01-01", 5040, "Plain Bob Major", "5040 Plain Bob Major"),
    (2, "P2", "Abingdon", "St Helen", "Berkshire", 102, "tower", "2024-01-02", 5040, "Bristol Surprise Major", "5040 Bristol Surprise Major"),
    (3, "P3", "Bampton", "St Mary", "Devon", 103, "tower", "2024-01-03", 1280, "Plain Bob Major", "1280 Plain Bob Major"),
    # A handbell performance in a front room: no tower, by design (see the
    # schema/002 note on handbells -- this is not a resolution failure).
    (4, "P4", "33 St Malo Road", None, None, None, "hand", "2024-01-04", 1280, "Plain Bob Minor", "1280 Plain Bob Minor"),
    # Orphan TowerID 999: in neither dove nor towers, under the 5,000 drift
    # ceiling, so the orphan check stays INFO -- the shape decision 001
    # documents and says is not corruption.
    (5, "P5", "Elsewhere", None, None, 999, "tower", "2024-01-05", 1280, "Plain Bob Major", "1280 Plain Bob Major"),
]
MP_ROWS = [
    # method_id, position, event_type, perf_date, town, dove_tower_id
    ("m1", 0, "firstTowerbellPeal", "1930-01-01", "Oxford", 101),
    ("m2", 0, "firstTowerbellPeal", "1969-01-01", "Abingdon", 102),
    # All three links resolve, so the adjudicated-orphan check has a clean
    # zero to be broken in its own negative test. The real replica fails that
    # check today for the R-48 reason (9 of 22,136 links cite TowerID 25219,
    # which Dove has since removed) -- the fixture cannot carry that defect
    # in its baseline or every break would start from a failure.
    ("m2", 1, "firstHandbellPeal", "1970-01-01", "Bampton", 103),
]


def build(path, root):
    """Create a passing database at `path` inside a fake repo `root`.

    `root` is a directory laid out like the repository root (schema/ plus the
    distilled CSVs); `path` is the database file the checker will be pointed
    at. Rows are chosen so every range, join, orphan and plan assertion holds
    at once -- see the module docstring for the shapes that are not obvious.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    import sqlite3
    conn = sqlite3.connect(str(path))
    try:
        for sql in sorted((root / "schema").glob("*.sql")):
            conn.executescript(sql.read_text(encoding="utf-8"))
        _insert(conn, root)
        conn.commit()
    finally:
        conn.close()


def _insert(conn, root):
    cur = conn.cursor()

    cur.executemany(
        'INSERT INTO "dove" ("TowerID","RingID","RingType","Place","Dedicn",'
        '"County","Country","Lat","Long","Bells","DoveID") '
        "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        DOVE_ROWS,
    )
    cur.executemany(
        'INSERT INTO "towers" ("TowerID","RingID","RingType","Place","Dedicn",'
        '"County","Country","Lat","Long","Bells","DoveID") '
        "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        TOWERS_ROWS,
    )

    cur.executemany(
        'INSERT INTO "bells" ("Bell_ID","Place","Dedication","Tower_ID","Ring_ID",'
        '"Collection_Type","Ring_Size","Bell_Role","Note","Founder","Frame_ID") '
        "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        [
            (1, "Oxford", "St Mary", 101, 1, "Full circle", "8", "Tower bell", "A", "Taylor", 1.0),
            (2, "Abingdon", "St Helen", 102, 1, "Full circle", "10", "Tower bell", "B", "Taylor", 2.0),
        ],
    )
    cur.execute(
        'INSERT INTO "frames" ("Frame_ID","Place","Dedication","Tower_ID") VALUES (?,?,?,?)',
        (1, "Oxford", "St Mary", 101),
    )
    cur.execute(
        'INSERT INTO "founders" ("ID","Name","From","To") VALUES (?,?,?,?)',
        (1.0, "Taylor", 1839.0, None),
    )
    cur.execute(
        'INSERT INTO "regions" ("ID","Name","Type","Category") VALUES (?,?,?,?)',
        (1, "Oxfordshire", "County", "Ceremonial"),
    )
    cur.execute(
        'INSERT INTO "changes" ("Date","TowerID","Place","Description_of_change") '
        "VALUES (?,?,?,?)",
        ("2024-01-01", 101, "Oxford", "Ring rehung"),
    )

    cur.executemany(
        'INSERT INTO "methods" ("method_id","title","name","stage","classification",'
        '"notation","lead_head","lead_head_code") VALUES (?,?,?,?,?,?,?,?)',
        [
            ("m1", "Plain Bob Major", "Plain Bob", 8, "Bob", "-18-18-18-18,18", "13456782", "a"),
            ("m2", "Bristol Surprise Major", "Bristol", 8, "Surprise", "-58-14.58-58.36.14-14.58-14-18,18", "14263857", "n"),
        ],
    )
    cur.executemany(
        'INSERT INTO "method_performances" ("method_id","position","event_type",'
        '"perf_date","town","dove_tower_id") VALUES (?,?,?,?,?,?)',
        MP_ROWS,
    )

    cur.executemany(
        'INSERT INTO "performances" ("perf_id","bb_id","place","dedication","county",'
        '"dove_tower_id","ring_type","perf_date","changes","method","title") '
        "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        PERF_ROWS,
    )
    cur.executemany(
        'INSERT INTO "performance_ringers" ("perf_id","position","bell","name","conductor") '
        "VALUES (?,?,?,?,?)",
        [(1, 0, "1", "A Ringer", 1), (2, 0, "1", "B Ringer", 0)],
    )
    cur.execute(
        'INSERT INTO "performance_footnotes" ("perf_id","position","footnote") VALUES (?,?,?)',
        (1, 0, "First peal"),
    )
    cur.execute(
        'INSERT INTO "performance_flags" ("perf_id","position","flag_type","bell") VALUES (?,?,?,?)',
        (1, 0, "simulator", "6"),
    )

    cur.execute(
        'INSERT INTO "performance_methods" ("perf_id","method_id","ord","match_kind",'
        '"confidence","matched_on") VALUES (?,?,?,?,?,?)',
        (1, "m1", 0, "exact_title", "high", "Plain Bob Major"),
    )
    cur.execute(
        'INSERT INTO "performance_method_unresolved" ("perf_id","method_text","reason") '
        "VALUES (?,?,?)",
        (4, "Plain Bob Minor", "no_match"),
    )

    cur.execute(
        'INSERT INTO "compositions" ("composition_id","library","derived_title","title",'
        '"stage","length") VALUES (?,?,?,?,?,?)',
        (10015, "Public", "5056 Plain Bob Major by A Composer", "5056 PB Major", 8, 5056),
    )
    cur.execute(
        'INSERT INTO "composition_methods" ("composition_id","position","name",'
        '"method_title","mnemonic","place_notation","row_stage","method_stage",'
        '"method_id") VALUES (?,?,?,?,?,?,?,?,?)',
        (10015, 0, "Plain Bob", "Plain Bob Major", "P", "-18-18-18-18,18", 8, 8, "m1"),
    )

    # The CSVs check_csv_agreement counts. The header must match the committed
    # format because the checker reads by column name via DictReader.
    bb = root / "data" / "bellboard"
    bb.mkdir(parents=True, exist_ok=True)
    _write_csv(bb / "performances_2024.csv", BB_PERF_HEADER, [
        ["1", "P1", "Guild", "Oxford", "St Mary", "Oxfordshire", "", "101", "1", "tower", "", "", "", "2024-01-01", "", "5040", "Plain Bob Major", "5040 Plain Bob Major", "", "", "", "", ""],
        ["2", "P2", "Guild", "Abingdon", "St Helen", "Berkshire", "", "102", "1", "tower", "", "", "", "2024-01-02", "", "5040", "Bristol Surprise Major", "5040 Bristol Surprise Major", "", "", "", "", ""],
        ["3", "P3", "Guild", "Bampton", "St Mary", "Devon", "", "103", "1", "tower", "", "", "", "2024-01-03", "", "1280", "Plain Bob Major", "1280 Plain Bob Major", "", "", "", "", ""],
        ["4", "P4", "Guild", "33 St Malo Road", "", "", "", "", "", "hand", "", "", "", "2024-01-04", "", "1280", "Plain Bob Minor", "1280 Plain Bob Minor", "", "", "", "", ""],
        ["5", "P5", "Guild", "Elsewhere", "", "", "", "999", "", "tower", "", "", "", "2024-01-05", "", "1280", "Plain Bob Major", "1280 Plain Bob Major", "", "", "", "", ""],
    ])
    _write_csv(bb / "ringers_2024.csv", BB_RINGER_HEADER, [
        ["1", "0", "1", "A Ringer", "1"],
        ["2", "0", "1", "B Ringer", "0"],
    ])
    _write_csv(bb / "footnotes_2024.csv", BB_FOOTNOTE_HEADER, [
        ["1", "0", "First peal"],
    ])
    _write_csv(bb / "flags_2024.csv", BB_FLAG_HEADER, [
        ["1", "0", "simulator", "6", ""],
    ])

    cl = root / "data" / "complib"
    cl.mkdir(parents=True, exist_ok=True)
    _write_csv(cl / "compositions.csv", CL_COMP_HEADER, [
        ["10015", "Public", "5056 Plain Bob Major by A Composer", "5056 PB Major", "", "8", "5056", "", "", "", "", "", "", "", "", "", "", ""],
    ])
    _write_csv(cl / "composition_methods.csv", CL_CM_HEADER, [
        ["10015", "0", "Plain Bob", "Plain Bob Major", "P", "-18-18-18-18,18", "-18-18-18-18,18", "8", "8", "", "m1"],
    ])


def _write_csv(path, header, rows):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(header.split(","))
        w.writerows(rows)


def _load_checker(root):
    """Import verify_corpus with its module rooted at a fake repository.

    verify_corpus resolves SCHEMA_DIR and the CSV directories from its own
    __file__, so the fixture loads a second instance of the module from the
    tempdir copy. db.py is imported the normal way: it only provides the
    connection factory, and its own path resolution does not matter here.
    """
    src = root / "scripts" / "verify_corpus.py"
    scripts_dir = str(root / "scripts")
    sys.path.insert(0, scripts_dir)
    spec = importlib.util.spec_from_file_location("verify_corpus_fixture_under_test", src)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    sys.path.remove(scripts_dir)
    return mod


@contextmanager
def fixture_root():
    """Yield a tempdir laid out like the repository root, then remove it."""
    tmp = Path(tempfile.mkdtemp(prefix="verify-corpus-fixture-"))
    try:
        (tmp / "scripts").mkdir()
        # db.py too: verify_corpus.py imports it at module load, and the copy
        # keeps the fake repository self-contained rather than depending on
        # whichever scripts directory happens to be on sys.path first.
        shutil.copy(REPO_ROOT / "scripts" / "verify_corpus.py", tmp / "scripts" / "verify_corpus.py")
        shutil.copy(REPO_ROOT / "scripts" / "db.py", tmp / "scripts" / "db.py")
        shutil.copytree(SCHEMA_DIR, tmp / "schema")
        yield tmp
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


@contextmanager
def passing_database():
    """Yield (checker module, db path) for a database with zero failures.

    The checker module is rooted at the fixture's fake repository, so its
    check_csv_agreement reads the distilled CSVs beside the database rather
    than the real repository's -- and the real data/ is never touched.
    """
    with fixture_root() as root:
        db_path = root / "fixture.db"
        build(db_path, root)
        yield _load_checker(root), db_path


def run_checks(checker, db_path):
    """Run every check against db_path; return the populated Reporter.

    Calls the check functions directly rather than main(), so a test failure
    is a traceback at the break that caused it instead of a subprocess exit
    code to decode. The Reporter is the checker's own; output is captured so
    51 negative tests do not each print 51 lines, and each check function
    runs inside its own try/except so a check that CRASHES (a broken view
    raising OperationalError mid-EXPLAIN, say) is recorded as
    "crash: <function>" with status FAIL instead of ending the run.

    That is not smoothing over a defect -- it is measuring one. A crash is
    loud (main() would exit non-zero on the traceback) but it truncates the
    report, and the negative tests need to say which checks still ran.
    `rep.names` holds (name, status, detail) for everything recorded.
    """
    import io
    import sqlite3
    from contextlib import redirect_stdout, redirect_stderr

    class _Recording(checker.Reporter):
        def __init__(self):
            super().__init__(quiet=True)
            self.names = []

        def report(self, name, status, detail=""):
            self.names.append((name, status, detail))
            super().report(name, status, detail)

    rep = _Recording()
    conn = sqlite3.connect(str(db_path))
    checks = [
        checker.check_schema_objects,
        checker.check_read_cost_indexes,
        checker.check_row_counts,
        checker.check_csv_agreement,
        checker.check_towerid_fanout,
        checker.check_orphan_soft_fks,
        checker.check_join_identity,
        checker.check_nan_strings,
        checker.check_query_plans,
    ]
    try:
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            for fn in checks:
                try:
                    fn(conn, rep)
                except Exception as e:  # noqa: BLE001 - recorded, see above
                    rep.report(f"crash: {fn.__name__}", checker.Result.FAIL,
                               f"{type(e).__name__}: {e}")
    finally:
        conn.close()
    return rep
