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

The SQL behind it lives in `queries/` — and `build_atlas.py` reads those files
rather than holding its own copies, so what is recorded is what actually ran.
`queries/findings/` holds one query per claim made on the page, so each figure
can be checked instead of taken on trust.

## Status

- [x] Dove's Guide bulk CSVs (towers, bells, frames, founders, dove, changes,
      regions) audited and schema-mapped
- [x] Working SQLite build, joins and a first query verified
- [x] Schema exported and migration script written
- [x] Database provisioned on Turso and loaded with all seven Dove tables
      (owner-managed, see `docs/CONNECTING.md`)
- [x] BellBoard schema, ingestion script and incremental sync (see
      `schema/002_init_bellboard.sql`); first window loaded
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
- [x] BellBoard historical backfill runner -- resumable and checkpointed
      (PR #2, usage below), now with a **completeness gate** (PR #5): each
      window's fetched row count is checked against the count BellBoard's
      `search.php` reports for that window, and a window that comes up short
      is retried and (if still short) failed rather than checkpointed; the
      run exits non-zero on any shortfall. `export.php` honours `from`/`to`,
      not `date_from`/`date_to`, and returns results newest-first. The earlier
      run captured 55,000 rows against a true corpus of 336,654 (measured via
      `search.php`), stopping early without erroring -- see
      `docs/decisions/002-backfill-count-discrepancy.md` and Task 5 of the
      Vibe roadmap. **The backfill is now complete: 293,471 performances
      spanning 2012-01-01 to 2024-12-31**, thirteen years, which is the whole of
      BellBoard's near-complete era. Twelve of the thirteen years agree with
      `search.php` to the record; 2022 is one performance short of a count taken
      today, because BellBoard grows retrospectively and that record was filed
      after 2022 was fetched. Per-year counts, and which years were re-checked
      when, are in `data/SOURCES.md`. Loading this to *production* still waits
      for the Turso freeze to lift on 2026-09-01.
- [x] Performance -> method linkage (`schema/005`,
      `scripts/resolve_performance_methods.py`) -- 116,862 of 156,513 performances
      (74.7%) now carry at least one method link, 205,825 links in all. The hard
      part was the 15,497 performances naming several methods at once
      ("Spliced Surprise Major (8m)"), whose constituents are free text in
      `details`; the method string states how many to find, which makes every row
      self-checking. 39,651 are recorded as unresolved with the reason and the
      counts, most of them not methods at all (tolling, call changes).
      First question it answers: **70.6% of the 10,838 Major methods in the
      library were not rung once in seven years** -- 3,188 of them were. Over the
      four years 2021-24 alone the figure was 81.6%, so three more years of
      corpus found roughly a thousand more Major methods in use, and the
      "unrung" tail is smaller than a shorter window made it look.
- [ ] Method extension lineage from place notation -- `extension_construction`
      is populated for only 1,851 of 25,055 methods
- [ ] Fallback resolution for the ~2% of *tower* performances with no
      `dove-tower-id` (the handbell-in-a-private-house records are not
      resolvable in principle and are out of scope)
- [x] Join semantics for towers holding more than one ring -- decided in
      `docs/decisions/001-ring-vs-tower-joins.md` and **adopted**. Neither
      `dove` (7,262 rows, 7,249 TowerIDs) nor `towers` (15,722 rows, 15,402
      TowerIDs) is a tower register; both are installation registers, so joining
      either on `TowerID` fans out, and joining `dove` also silently drops
      everything outside its ringing subset. Both errors ran in the same query
      and partly cancelled, which is why it went unnoticed. Tower-level
      questions now join `v_towers_unique` (`schema/007`); ring-level questions
      use `RingID`, which BellBoard supplies as `dove_ring_id` and the Methods
      Library does not. Measured on adoption: `v_tower_performances` 80,231 ->
      80,058, `v_first_tower_peals` 25,351 -> 25,340.
- [ ] CompLib linkage -- CompLib's search payload carries free-text
      method titles only, but `/composition/{id}/rows` returns a `methodid`
      for single-method compositions that maps to the CCCBR `method_id` by
      `'m' || methodid` (opt-in via `--fetch-method-ids`); spliced
      compositions remain free-text for Gemini/Claude to resolve.
- [x] First analytical output -- the Founder Atlas (see above)
- [x] The Rhythm of Ringing -- the week, the year, and the 24 days that carry
      21% of it; corrected the September and Wednesday claims made in
      `docs/IDEAS.md` and in this README
- [x] CompLib ingestion -- the fourth corpus (`schema/006`,
      `scripts/ingest_complib.py`): 86,039 compositions from the
      `api.complib.org` JSON API, with `perpage` capped at 25 (a max
      the OpenAPI spec omits). See `data/SOURCES.md`.
- [ ] Ringer identity resolution (needs the backfill run first)

## Roadmap

`docs/ROADMAP.md` — one ordered list across all three agents. Correctness work
comes before analysis, because an analysis built on a corpus with a silent gap
has to be redone.

## The Blue Line Atlas

Every method drawn as the path a bell traces through it — 20,679 of them, from
place notation verified against the library's own published lead heads.

**https://nihilisticiconoclast.github.io/change-ringing/methods.html**

Built by `scripts/build_method_atlas.py` on top of `scripts/notation.py`, a
place-notation parser that agrees with the CCCBR library on 97.4% of all 25,066
methods and over 99.7% at Minor and Major.

## First Rung

Three centuries of method invention — 23,874 methods with a date on which they were
first rung, from 1684 to 2026.

**https://nihilisticiconoclast.github.io/change-ringing/invention.html**

166 methods were first rung before 1900; 12,680 since the year 2000. The shape has
three things a steady-accumulation story would miss:

- **1940 to 1945 is a hard zero.** Seventeen new methods in 1939, then 0, 3, 0, 0,
  4, 0. Church bells were silenced across Britain and reserved as an invasion
  warning, and the collection simply stops. Three of those years produced none at
  all, which happens in no other year after 1889.
- **Methods arrive in batches.** The largest single day is 17 October 1993 at Stow
  Bardolph, Norfolk — a village — where **562 methods were first rung in one peal**,
  more than the whole of 1684–1899 produced. 3,321 methods, 14% of the collection,
  debuted on a day that introduced 60 or more at once, so an "invention rate" is
  close to meaningless.
- **The pandemic produced a new kind of first, not new methods.** Ringing Room, the
  browser platform, carries 1,142 first-performance events and only 115 method
  debuts. The CCCBR library grew four event types to record keyboard ringing, and
  1,137 of those 1,138 events are 2020 or later.

And one finding that needed guarding: of the 7,645 methods first rung in 1975–99,
the peak era, only **13.1%** were rung at all in 2021–24, against 72–82% for
methods first rung before 1900. Both bounds are published (13.1% and 16.2% on a
deliberately over-generous count) because the method linkage's own 74.7% coverage
could otherwise have manufactured the result.

## The Rhythm of Ringing

Four years of the national record, day by day — and a correction. This
repository recorded that "September is the busiest ringing month (12,067
performances) and nobody knows why". It is not, and the corpus knew why all
along: 49% of September's performances fall in the eleven days between the death
of Elizabeth II and her state funeral, and the reason is written in the footnote
text hundreds of bands filed independently.

**https://nihilisticiconoclast.github.io/change-ringing/rhythm.html**

24 days carry **21.0%** of the four years 2021-24 — the window that page is
still restricted to, while the corpus now runs 2018-24. They are found by rule — 3.5×
the median of the same weekday nearby — and named by the corpus's own most-
repeated footnotes, so no list of national events is hand-entered anywhere. Two
further columns then separate them into celebration, remembrance, a death, and
the funerals that are both: whether the bells were *tolling*, and whether the
footnote says *half-muffled*. Remembrance Sunday's muffled rate is 73%, 74%,
72%, 74% across 2021-24 against a 5.7% baseline. And "99 Tolling" records the
age of the person who died, in the field reserved for method names, in a corpus
with no age column anywhere.

Built by `scripts/build_rhythm_page.py`; SQL in `queries/rhythm/`; the claims
are checkable in `queries/findings/`.

## Ideas

`docs/IDEAS.md` — five visualisation options and a set of insight seams, each
with measured feasibility, and each now annotated with what happened when it was
built. Two of the three headline figures for option B were wrong, and the
struck-through originals are left in place rather than edited away. Still
standing: 70% of the 9,169 methods rung in 2021-24 were rung exactly once,
and the ten busiest towers account for only 3.4% of activity, which is far less
concentrated than expected.

## Lessons learnt

`docs/LESSONS.md` — what this project taught, written for the next one rather
than this one. Choosing work where verification is cheap, giving agents an
instrument rather than a warning, and why a fix that went from 18 minutes to 19
seconds saved no money at all.

## Historic peal records: Felstead

`docs/felstead-enquiry.md` -- a **drafted, unsent** enquiry to the CCCBR about the
Felstead database, which holds "over 360,000 towerbell peals" going back to the
1800s (the tower sampled starts in 1875). It would take the corpus from a
four-year window to a century and a half, for peals.

The join needs no name matching and was already in our data: BellBoard publishes
a `towerbase-id`, present on 132,034 of 156,513 performances across 5,891 towers,
and Felstead's lookup takes exactly that identifier. Twelve sampled identifiers
were probed by hand and all twelve resolved.

**Nothing has been fetched beyond 16 manual page loads while establishing that.**
Felstead states no licence, publishes no API and has no robots.txt, and it
represents several thousand hours of volunteer transcription. Permission first.

## Site navigation

Every page's nav bar and footer come from `scripts/site_chrome.py` — one ordered
list of pages, expanded into `<!--NAV:page.html-->` and `<!--FOOTER:page.html-->`
markers at build time. Nothing else in the repository hard-codes a list of pages,
and `apply_chrome` raises if a marker is missing.

`python scripts/verify_chrome.py` checks the built pages and exits non-zero if any
of them disagrees: same nine links, same order, exactly one marked as current, and
a link back here. Run it after building.

This exists because the site drifted twice. Nav bars diverged as pages were added
one at a time; then, once those were corrected by hand, the footers turned out to
be worse — two pages linked to two different subsets of the site and five had no
footer at all.

## Repository layout

```
schema/     -- SQL schema (tables, indexes, views), source of truth for structure
scripts/    -- migration and ingestion scripts
docs/       -- architecture, agent division of labour, connection instructions
data/       -- NOT the raw CSVs (see data/SOURCES.md) -- provenance and licensing only
.github/    -- scheduled refresh: Dove weekly, BellBoard daily
docs/vendor -- pinned third-party JS, so every page opens offline (see its README)
scripts/site_chrome.py -- the one definition of the nav bar and footer
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

### Just query it — one command, no credentials

The corpus is **not** committed. `data/change-ringing.db` was tracked briefly
and removed: at ~40 MB it was heading for GitHub's 100 MB file limit, and a
binary that changes wholesale on every rebuild sits in git history forever.
Build your own instead — it takes about 90 seconds and needs nothing but
Python:

```
pip install -r requirements.txt
python scripts/build_local_db.py --out data/change-ringing.db
```

Then open it in any SQLite tool — DB Browser for SQLite, DBeaver, TablePlus, or
a VS Code extension such as SQLite Viewer or SQLTools. It is a standard SQLite
file; nothing Turso-specific is needed to read it.

> **It is not MIT-licensed.** The code in this repository is; the data is
> CC BY-SA 4.0, inherited from Dove's Guide, and that carries attribution and
> share-alike obligations. Read `data/LICENCE-DATA.md` before republishing
> anything derived from it.

Because it is built rather than downloaded, it is always current — Dove is a
live source and drifts. If a large binary ever does need sharing, attach it to
a GitHub Release rather than committing it: downloadable from the repository
page, absent from git history.

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

## BellBoard historical backfill

The corpus currently holds only a small recent window of BellBoard performances.
To load the full historical record back to 2012, use the resumable backfill runner:

```bash
# Run a full backfill (resumable, checkpointed)
python scripts/backfill_bellboard.py

# Run a specific date range
python scripts/backfill_bellboard.py --start 2020-01-01 --end 2020-12-31

# Resume from the last checkpoint
python scripts/backfill_bellboard.py --resume

# Customize window size (default 30 days) and delays
python scripts/backfill_bellboard.py --window-days 60 --delay 5 --page-delay 3
```

The runner:
- Uses dated windows (`from`/`to` parameters) rather than `changed_since` to ensure
a proper historical walk
- Checkpoints each window as completed, so a resumed run skips finished windows
- Handles BellBoard throttling (which silently truncates responses) by backing
off and re-fetching short pages
- Maintains idempotent writes (INSERT OR REPLACE) so overlapping windows converge

See `scripts/backfill_bellboard.py` for full options and the throttling strategy.

## Getting started

See `docs/CONNECTING.md` for how to point any of the three working agents
(Claude Code, Gemini CLI, Mistral Vibe) at the live database, and
`docs/AGENTS.md` for which agent is best suited to which part of the work
and why.
