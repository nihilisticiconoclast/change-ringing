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
- [ ] Database provisioned on Turso (owner-managed, see `docs/CONNECTING.md`)
- [ ] BellBoard performance data ingested
- [ ] Tower name -> TowerID entity resolution (BellBoard's free-text tower
      names against Dove's canonical IDs)
- [ ] Ringer name resolution across decades of performances
- [ ] CCCBR Methods Library / CompLib linkage
- [ ] First analytical output (method/performance atlas, ringer-lineage tool,
      or method-genealogy tool -- see `docs/RATIONALE.md`)

## Repository layout

```
schema/     -- SQL schema (tables, indexes, views), source of truth for structure
scripts/    -- migration and ingestion scripts
docs/       -- architecture, agent division of labour, connection instructions
data/       -- NOT the raw CSVs (see data/SOURCES.md) -- provenance and licensing only
```

The raw Dove CSVs are not committed here. They're licensed CC BY-SA 4.0 and
live in Turso, the actual database; this repo holds the code and schema that
build and query it. See `data/SOURCES.md` for where to get them and the
attribution required if this project's outputs are ever published.

## Getting started

See `docs/CONNECTING.md` for how to point any of the three working agents
(Claude Code, Gemini CLI, Mistral Vibe) at the live database, and
`docs/AGENTS.md` for which agent is best suited to which part of the work
and why.
