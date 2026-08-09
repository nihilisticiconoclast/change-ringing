# Change Ringing

A queryable corpus for English change ringing: towers, bells, frames, founders
and (once ingested) the performance record from BellBoard. Built to fill a real
gap -- the underlying data is unusually open (Dove's Guide, the CCCBR Methods
Library, BellBoard's API, CompLib), but nobody maintains a linked, queryable
version of it. See `docs/RATIONALE.md` for the fuller case.

This is not a scoring or forecasting project. There is no held-out test set
and no ground truth to validate against -- the value here is custodial and
interpretive: a corpus a ringer, a tower captain, or a researcher could
actually use.

## The Founder Atlas

The project's first analytical output: 51,451 attributed bells across 12,635
towers, mapped by the foundry tradition that cast them, then joined to the
methods first rung on them.

**https://nihilisticiconoclast.github.io/change-ringing/**

Rebuild it with `python scripts/build_atlas.py`, which reads a local database
(never Turso) and writes `docs/index.html` — one self-contained file, no
external requests. The page is served by GitHub Pages from `main` / `docs`.

## Status

- [x] Dove's Guide bulk CSVs (towers, bells, frames, founders, dove, changes,
      regions) audited and schema-mapped
- [x] Working SQLite build, joins and a first query verified
- [x] Schema exported and migration script written
- [x] Database provisioned on Turso and loaded with all seven Dove tables
      (owner-managed, see `docs/CONNECTING.md`)
- [x] BellBoard schema, ingestion script and incremental sync (see
      `schema/002_init_bellboard.sql`); first window loaded
- [ ] BellBoard historical backfill (the corpus back to 2012)
- [x] Tower -> Dove ID linkage -- largely a non-problem: BellBoard publishes
      `dove-tower-id` on each performance, so this is an integer join, not a
      name match. ~94% of performances carry it and 99.5% of those resolve.
      See the header of `schema/002_init_bellboard.sql`.
- [x] CCCBR Methods Library schema, ingestion script, and verification
      (see `schema/003_init_methods.sql` and `scripts/ingest_methods.py`);
      loaded to Turso -- 25,055 methods, 30,734 first-performance events
- [x] CCCBR Methods first-performance location resolution candidates and analysis
      (see `data/method_location_candidates.csv` and `docs/method_location_resolution.md`)
- [x] Adjudicated `data/method_location_candidates.csv` into
      `method_performances.dove_tower_id` -- 22,111 of 30,734 first-performance
      records (71.9%) linked to a Dove tower; decisions recorded in
      `data/method_location_adjudication.csv`
- [ ] Method extension lineage from place notation -- `extension_construction`
      is populated for only 1,851 of 25,055 methods
- [ ] Fallback resolution for the ~2% of *tower* performances with no
      `dove-tower-id` (the handbell-in-a-private-house records are not
      resolvable in principle and are out of scope)
- [ ] Decide join semantics for the 13 Dove towers holding more than one ring.
      `dove.TowerID` is **not unique** (7,262 rows, 7,249 distinct TowerIDs) --
      Farnham S Andrew, for instance, has both a full-circle and a lightweight
      ring under TowerID 11301. Joining on `TowerID` alone therefore fans out
      and silently inflates counts: `v_first_tower_peals` gains 11 rows this
      way. Tower-level questions should join against a deduplicated tower list
      or `towers`; ring-level questions should use `RingID`, which BellBoard
      supplies as `dove_ring_id` but the Methods Library does not.
- [ ] CompLib linkage
- [ ] First analytical output (method/performance atlas, ringer-lineage tool,
      or method-genealogy tool -- see `docs/RATIONALE.md`)

## Repository layout

```
schema/     -- SQL schema (tables, indexes, views), source of truth for structure
scripts/    -- migration and ingestion scripts
docs/       -- architecture, agent division of labour, connection instructions
data/       -- NOT the raw CSVs (see data/SOURCES.md) -- provenance and licensing only
.github/    -- scheduled refresh: Dove weekly, BellBoard daily
```

## Database freeze (2026-08-09)

The Turso database breached its daily row-read limit at 591 million reads.
**Nothing now touches it unattended:** both scheduled workflows have had their
`schedule:` triggers removed and run only on manual dispatch, and both agent
task briefs carry a freeze notice telling them not to query production.

The cause is understood and fixed -- two unindexed joins, see the read-cost
section of `docs/CONNECTING.md` and `schema/004_read_cost_indexes.sql`. The
freeze is about not spending anything further while the budget is reviewed,
not about an unresolved fault.

To lift it: restore the `schedule:` blocks in `.github/workflows/` (the
original cron lines are preserved in comments there) and remove the notices
from `docs/tasks/`.

### Just query it — no build, no credentials

`data/change-ringing.db` is a committed snapshot of the whole corpus. Clone the
repo and open it in any SQLite tool — DB Browser for SQLite, DBeaver, TablePlus,
or a VS Code extension such as SQLite Viewer or SQLTools. It is a standard
SQLite file; nothing Turso-specific is needed to read it.

> **It is not MIT-licensed.** The code in this repository is; the data is
> CC BY-SA 4.0, inherited from Dove's Guide, and that carries attribution and
> share-alike obligations. Read `data/LICENCE-DATA.md` before republishing
> anything derived from it.

The snapshot is dated. Dove is a live source, so rebuild with
`scripts/build_local_db.py` when currency matters, and don't re-commit the
snapshot casually — each version adds ~40 MB to git history permanently.

### Work offline instead

The freeze costs almost nothing, because the whole corpus rebuilds locally
from public sources plus files committed here:

```
pip install -r requirements.txt
python scripts/build_local_db.py --out local_corpus.db
```

About 90 seconds, and every script then takes `--local-db local_corpus.db`.
The replica matches production: 7,262 towers, 63,894 bells, 25,055 methods,
30,734 first-performance events, and the same 22,111 adjudicated tower links.
BellBoard is left empty unless you pass `--bellboard-since YYYY-MM-DD`, since
it is the one source that throttles rather than publishing a bulk file.

Two things make this a real check rather than an approximation. The replica
uses an embedded libSQL connection rather than stdlib `sqlite3`, which accepts
SQL that libSQL rejects -- that difference is how a double-quoted string
literal reached production. And `EXPLAIN QUERY PLAN` works against it, so
query cost can be assessed before anything runs for real.

Reaching production now requires `CHANGE_RINGING_ALLOW_PRODUCTION=1`. Without
it the scripts refuse to connect, so an accidental production run is no longer
possible.

## Keeping the data current

Two GitHub Actions workflows keep the database fresh without anyone running
anything locally. Both need `TURSO_DATABASE_URL` and `TURSO_AUTH_TOKEN` as
repository secrets, and both can be run on demand from the Actions tab.

| Workflow | Schedule | Strategy |
| --- | --- | --- |
| `refresh-dove.yml` | Mondays 04:17 UTC | Full drop-and-reload -- Dove publishes a snapshot, not a changelog |
| `sync-bellboard.yml` | Daily 03:42 UTC | Incremental via BellBoard's `changed_since` |

The raw Dove CSVs are not committed here. They're licensed CC BY-SA 4.0 and
live in Turso, the actual database; this repo holds the code and schema that
build and query it. See `data/SOURCES.md` for where to get them and the
attribution required if this project's outputs are ever published.

## Getting started

See `docs/CONNECTING.md` for how to point any of the three working agents
(Claude Code, Gemini CLI, Mistral Vibe) at the live database, and
`docs/AGENTS.md` for which agent is best suited to which part of the work
and why.
