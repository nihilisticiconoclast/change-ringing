# Connecting to the database

The live database is Turso (hosted libSQL, SQLite-compatible). This repo
holds schema and code; Turso holds the actual data. Nobody should commit a
`.db` file here -- see `.gitignore`.

## One-time setup (owner)

1. Create the database: `turso db create change-ringing`
2. Get the URL: `turso db show change-ringing --url`
3. Create a token: `turso db tokens create change-ringing`
4. Apply the schema and load data:
   ```
   export TURSO_DATABASE_URL="libsql://change-ringing-<org>.turso.io"
   export TURSO_AUTH_TOKEN="<token>"
   python scripts/fetch_dove_csvs.py --out-dir ./dove-csvs
   python scripts/migrate_csv_to_turso.py --csv-dir ./dove-csvs
   ```
   Dove publishes the CSVs at stable URLs, so the load does not depend on a
   pre-existing local copy. If you already have one, skip the fetch step and
   point `--csv-dir` at it.
5. Share `TURSO_DATABASE_URL` and a token with each agent environment as
   below. Prefer creating a separate token per agent/environment
   (`turso db tokens create change-ringing`) over sharing one token, so
   access can be revoked individually if needed.

## Connecting from each agent

All three tools reach the database the same way -- two environment
variables, then either the `libsql` Python client or the `turso` CLI
directly. Nothing agent-specific is required.

**Environment variables (all agents):**
```
export TURSO_DATABASE_URL="libsql://change-ringing-<org>.turso.io"
export TURSO_AUTH_TOKEN="<token>"
```

**Python (any agent, e.g. for ingestion scripts):**
```python
import os, libsql
conn = libsql.connect(
    database=os.environ["TURSO_DATABASE_URL"],
    auth_token=os.environ["TURSO_AUTH_TOKEN"],
)
rows = conn.execute("SELECT * FROM v_ringing_towers LIMIT 5").fetchall()
```

**CLI (quick queries, any agent with the `turso` CLI installed):**
```
turso db shell change-ringing "SELECT COUNT(*) FROM dove"
```

## Work offline by default

Production is metered on rows read and is currently frozen. The scripts refuse
to open a remote connection unless `CHANGE_RINGING_ALLOW_PRODUCTION=1` is set;
the intended path is a local replica:

```
python scripts/build_local_db.py --out local_corpus.db
python scripts/ingest_methods.py --local-db local_corpus.db
```

`build_local_db.py` reconstructs the corpus from Dove's public CSVs, the CCCBR
methods XML, the schema files, and the adjudication record in `data/` -- all
public or committed, none of it read from Turso. BellBoard is the exception
and stays empty unless you ask for a window with `--bellboard-since`.

The replica opens with an embedded libSQL connection rather than stdlib
`sqlite3`. That is deliberate: `sqlite3` accepts SQL that libSQL rejects, and
a double-quoted string literal reached production precisely because local
testing under `sqlite3` had passed. One gap remains -- NaN parameter binding
is accepted by both, because the rejection happens in the Hrana JSON layer
that only a remote connection uses.

## A note on read cost

Turso meters **rows read**, and that number is not proportional to how long a
query takes. This database holds roughly 130,000 rows and billed 591 million
reads in a single day. Two statements caused nearly all of it:

- `SELECT COUNT(*) FROM v_first_tower_peals` -- the planner drove the join off
  `event_type` rather than `method_id`, walking 15,813 rows once per method:
  396 million reads for one count. Fixed by the composite index in
  `schema/004_read_cost_indexes.sql`.
- The location adjudication matched on three columns wrapped in `COALESCE`,
  which no index can serve: 139 million reads per run, and it was run twice.

The trap worth internalising: **batching a slow loop into one statement fixes
wall-clock time and can leave read cost completely unchanged.** The 18-minute
and 19-second versions of that adjudication write read exactly the same 139
million rows. Latency and read cost are separate problems and only one of them
announces itself.

Before running anything that touches a whole table, check the plan:

```sql
EXPLAIN QUERY PLAN <your statement>;
```

`SCAN` inside a correlated subquery, or `SEARCH ... USING INDEX` on a column
whose range is large, means you are paying rows-read proportional to the
product of two tables. Join on a single indexed key, and avoid wrapping join
columns in functions -- `COALESCE(a,'') = COALESCE(b,'')` defeats every index.

## A note on join fan-out

`dove.TowerID` is not unique: 7,262 rows carry 7,249 distinct TowerIDs,
because 13 towers hold more than one ring. Joining on `TowerID` alone
duplicates rows for those towers. Use `RingID` where the question is about a
specific ring, and deduplicate where it is about a tower.

## A note on concurrent writes

libSQL's replication is read-optimised (embedded replicas sync from a
single primary). At this project's scale that's not a practical
constraint, but the working pattern should be: agents write straight to
the primary over HTTP (the pattern above), not via a local synced replica.
Avoid two agents running a bulk write step at the same moment -- coordinate
through `docs/AGENTS.md` and this repo's issue tracker rather than relying
on the database to arbitrate.
