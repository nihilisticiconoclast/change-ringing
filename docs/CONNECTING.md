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
   python scripts/migrate_csv_to_turso.py --csv-dir /path/to/dove/csvs
   ```
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

## A note on concurrent writes

libSQL's replication is read-optimised (embedded replicas sync from a
single primary). At this project's scale that's not a practical
constraint, but the working pattern should be: agents write straight to
the primary over HTTP (the pattern above), not via a local synced replica.
Avoid two agents running a bulk write step at the same moment -- coordinate
through `docs/AGENTS.md` and this repo's issue tracker rather than relying
on the database to arbitrate.
