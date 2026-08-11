# Queries

The SQL behind the corpus, kept as files rather than buried in scripts so the
figures on the atlas can be traced back to the statement that produced them.

Run any of them against the committed snapshot with no setup:

```
sqlite3 data/change-ringing.db < queries/findings/rudhall_territory.sql
```

or open `data/change-ringing.db` in DB Browser for SQLite, DBeaver, TablePlus,
or a VS Code SQLite extension, and paste. Nothing here needs Turso — see
`docs/CONNECTING.md` for why the live database is frozen until 2026-09-01.

## `atlas/` — what builds the page

These are not a copy of the queries the atlas uses. They **are** the queries:
`scripts/build_atlas.py` reads these files at build time. A `queries/` folder
that duplicates the real thing is worse than none, because it looks
authoritative while quietly going stale — so the duplication is removed rather
than managed.

| File | Produces |
| --- | --- |
| `01_bells_by_founder_group.sql` | Every attributed bell with its coordinates and foundry tradition — the map and the timeline |
| `02_first_peals_by_foundry.sql` | The three-corpus join: methods first rung on each tradition's bells |
| `03_foundry_group_metadata.sql` | The foundry cards — working life, firms, output, home town |
| `04_corpus_totals.sql` | The four headline figures, and the deliberately-unlinked count |

Aggregation happens in Python, not SQL: dominant tradition per tower,
quarter-century bucketing, and casting years, which need extracting from free
text (`Cast_Date` holds `c1897`, `(1834`, `[1902`). The SQL fetches rows; the
script shapes them.

## `findings/` — the claims in the prose

One file per assertion made on the atlas page or in the commit history, so
each can be checked rather than taken on trust.

| File | Checks |
| --- | --- |
| `busiest_towers_for_first_peals.sql` | Loughborough's Bell Foundry Tower tops first-peals at 507 |
| `rudhall_territory.sql` | Rudhall is regional — the Severn valley and Welsh marches |
| `founder_reach_by_methods.sql` | Why the `Group` column matters: Taylor under two names |
| `first_peals_by_decade.sql` | Post-war growth in new methods |
| `unlinked_performances.sql` | The 8,623 records deliberately left unlinked, and why |

## Two things that will bite you

**`dove.TowerID` is not unique.** 7,262 rows carry 7,249 distinct IDs, because
13 towers hold more than one ring — Farnham S Andrew has a full-circle and a
lightweight ring under `TowerID 11301`. Joining on it alone fans out and
inflates counts, while silently dropping 160 towers that are present in `towers`
but not in `dove`. **Use `v_towers_unique` as the default join target for towers.** 
Use `v_dove_towers` when you explicitly need Dove's narrower ringing subset. 
Use `RingID` only where the question is strictly about a specific ring.

**Founder counts overlap and must not be summed.** A ring usually mixes
founders, so a first-peal can count towards more than one tradition. The
figures are per-tradition reach, not a partition of the total.
