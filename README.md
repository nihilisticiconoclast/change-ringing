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
