# Roadmap: Mistral Vibe

A queue rather than a single task, so work can continue without waiting for a
new brief each time. **Do one task per pull request**, in order, and stop at
the end of each for review — the later tasks are deliberately sketched rather
than fully specified, because what they should say depends on what the earlier
ones find.

| # | Task | State |
| --- | --- | --- |
| 1 | BellBoard historical backfill runner | Merged, but **the run failed** — see Task 5 |
| 2 | CompLib ingestion | **Done** — see brief below |
| 3 | Corpus integrity checker | **Done** — PR #10, merged with four changes; see below |
| 5 | Backfill completeness gate | **Merged** — reviewed, three fixes applied on merge; see below |
| 4 | Ring-level join semantics | **Unblocked** — spec at `docs/decisions/001-ring-vs-tower-joins.md` |

---

## Standing constraints — read before every task

> **WORK OFFLINE. THE LIVE DATABASE IS FROZEN UNTIL 2026-09-01.** Turso
> breached its daily row-read limit. The scripts enforce this: they refuse a
> remote connection unless `CHANGE_RINGING_ALLOW_PRODUCTION=1`, and you should
> not set it.
>
> ```
> pip install -r requirements.txt
> python scripts/build_local_db.py --out local_corpus.db
> ```
>
> Builds a full replica in ~90 seconds from public sources and committed
> files: 7,262 towers, 63,894 bells, 25,055 methods, 30,734 first-performance
> events, 22,111 adjudicated tower links. Every script takes `--local-db`.
> Alternatively `data/change-ringing.db` is a committed snapshot you can query
> directly. Verify against one of those and say so in the PR.

**Constraints this codebase has already paid for.** Each cost real debugging
time; none are hypothetical.

- **Never `conn.executemany()` against Turso.** 4.1 rows/s measured, and it
  stalls on long runs. Multi-row `INSERT ... VALUES` runs at ~1300 rows/s.
  Reuse `insert_many()` from `scripts/bellboard_common.py`.
- **Never double-quote a SQL string literal.** libSQL treats it as an
  identifier and rejects the query; stdlib sqlite3 accepts it. That asymmetry
  put a bug in production.
- **Watch rows read, not wall-clock.** 591 million reads in one day came from
  two ordinary-looking statements. `EXPLAIN QUERY PLAN` anything that touches a
  whole table; a `SCAN` inside a correlated subquery means you are paying the
  product of two tables. Batching fixes latency and can leave read cost
  untouched — two versions of the same update took 18 minutes and 19 seconds
  and read identically.
- **Keep statements under SQLite's 32766 bind-parameter ceiling.**
- **Writes must be idempotent.** `INSERT OR REPLACE` on the source's own ID,
  child rows cleared before reinsert, so re-runs converge.
- **`dove.TowerID` is not unique** — 13 towers hold more than one ring — so
  joining on it alone inflates counts. See `docs/CONNECTING.md`.
- **A local run is a weaker check than production.** Three bugs here were
  invisible locally. Say what you verified and how, rather than "verified".

---

## Task 2 — CompLib ingestion *(done)*

**Done.** The API the brief was unsure about exists and is well
documented: `https://api.complib.org`, with an OpenAPI 3.0 spec at
`https://complib.org/complib.api.yml` (rendered as Redoc at
`/api`; the `/api` HTML page is a client-rendered shell, which is
why an earlier check concluded the API was undocumented -- the
spec is the YAML file that shell loads).

Deliverables: `schema/006_init_complib.sql` (the brief said 005,
but that slot is taken by `005_init_performance_methods.sql`),
`scripts/ingest_complib.py` (`--init`, `--reset`, `--local-db`,
matching the other loaders), and a CompLib section in
`data/SOURCES.md`. The loader caches pages to `complib-cache/` and
rate-limits (0.5s/page) so re-runs do not re-hit the API.

**What the API offers (verified 2026-08-15):**
- `/composition/search?page=N&perpage=N` returns
  `{count, page, perpage, compositions[]}`; `count` is **86,039**.
- The OpenAPI spec says `perpage` defaults to 25 but does not state
  a maximum; the server enforces one -- `perpage > 25` returns HTTP
  400 `"perpage maximum 25"`. A full walk is ~3,400+ pages.
- A composition's `methodDefinitions[]` carry free-text method
  `title` and `placeNotation`, **not** a CCCBR method id.
- `/composition/{id}/rows` returns a `methodid` for single-method
  compositions (null for spliced). That integer maps to the CCCBR
  `method_id` by `'m' || methodid` (11/12 sampled resolved). It is
  recorded as `complib_method_id`; `method_id` is populated by that
  exact lookup only, never by fuzzy matching. Opt-in via
  `--fetch-method-ids` because it costs one extra request per comp.

**Row counts from a real run** (bounded, against the local replica):
4 search pages = 100 compositions, 196 method-definition rows;
with `--fetch-method-ids`, 54 single-method compositions got a
CompLib method id and 39 of 196 method-definition rows resolved to
a CCCBR `method_id`. Re-runs converge (idempotent). The full
86,039-composition load is not run here -- it is ~3,400 pages and
the loader is designed for it, but the PR establishes the pipeline
and verifies it on a bounded slice.

Original brief, retained for reference:

Add composition data as the fourth corpus. Read `data/SOURCES.md`,
`schema/003_init_methods.sql` and `scripts/ingest_methods.py` first — this
should look like a sibling of the methods loader.

**Source:** https://complib.org, which documents an API and includes an
auto-proving engine. Establish what the API actually offers before designing
around it, and **say in the PR what you found**, including anything the docs
claim that turns out not to work. Two precedents: BellBoard's docs omit that
`from`/`to` are the working date parameters, and `date_from`/`date_to` silently
return zero rather than erroring.

**Deliverables**
1. `schema/005_init_complib.sql` — tables, indexes, and a view if one is
   genuinely useful.
2. `scripts/ingest_complib.py` — with `--local-db`, `--init` and `--reset`,
   matching the existing loaders.
3. A section in `data/SOURCES.md` recording provenance, licence and coverage.
4. Row counts from a real run against a local replica, in the PR description.

**The linkage that matters.** A composition is *of* a method. If CompLib
carries a method identifier that matches the CCCBR library, say so and use it —
that would make this an integer join, as BellBoard's `dove-tower-id` did. If it
carries only free-text method titles, **do not attempt fuzzy matching**: load
the text, leave a nullable `method_id`, and say so. Name resolution is
Gemini's, and adjudication is Claude Code's.

**Be gentle with the API.** Rate-limit, cache downloads to disk, and do not
re-fetch per record. Assume it throttles until you have evidence otherwise.

**Out of scope:** do not modify `schema/001`–`004` or any existing loader
beyond what CompLib needs; do not touch `data/method_location_*.csv`; do not
take on the Gemini roadmap.

---

## Task 3 — Corpus integrity checker *(done — PR #10)*

**Merged 2026-08-15** as `scripts/verify_corpus.py`, with four changes made on
merge. The submission was good: it covered everything the sketch asked for, it
exits non-zero, and — unusually — it came with a negative test. Verified before
merging rather than taken on trust: clean replica 49 checks / 0 failures /
exit 0, and a deliberately corrupted copy 3 failures / exit 1.

The four changes:

1. **A missing view was a SKIP; now it FAILs** unless it belongs to a migration
   listed as optional. Found by deleting `v_towers_unique` — the entire artefact
   of decision 001, the thing the checker most exists to defend — from a copy:
   the run reported SKIP and exited 0.
2. **`_plan_has_bad_scan()` was dead code that always returned False.** Its
   docstring described the right rule — a `SCAN` on the *outer* driving table is
   normal, it is an inner un-indexed scan that multiplies — while the live
   inlined check implemented a cruder one that FAILs on any bare `SCAN`. That
   crude rule turns a correctness fix into a red build: moving
   `v_tower_performances` onto `v_towers_unique` produces `CO-ROUTINE
   v_towers_unique / SCAN d`, where `d` is the co-routine, not a table. Replaced
   with `bad_scans()`, which implements the docstring: a non-driving bare `SCAN`
   of a name that is actually in `sqlite_master`.
3. **The join identity joined a hand-written `SELECT DISTINCT TowerID FROM
   towers` rather than `v_towers_unique`.** An inline equivalent passes happily
   while the real view is broken or missing — the check is worth having only if
   it exercises the object the rest of the codebase joins (lesson 20).
4. **Added `check_csv_agreement`** — the replica must hold exactly the rows the
   committed CSVs hold. This is the check that found a live defect: after the
   2020 backfill merged, the CSVs said 106,756 performances and the replica said
   96,067, and so did the README, because it had been written from the replica.
   Every other check passed on that database — it was internally perfect and a
   year out of date. A range check cannot catch that; only comparing the
   database against the thing it is built from can.

### Original Task 3 brief, retained

`scripts/verify_corpus.py`: one command that checks a database — local or, one
day, production — and reports anything wrong. Motivated by how many real
defects this project has shipped and caught late.

It should at minimum cover: expected row counts per table with tolerances;
orphaned foreign keys (`dove_tower_id` values absent from `towers`);
`dove.TowerID` fan-out; missing indexes from `schema/004`; literal `"nan"`
strings in text columns; and `EXPLAIN QUERY PLAN` assertions on the shipped
views, so a plan regression is caught before it costs a read budget again.

Exit non-zero on failure so it can gate CI later. Full brief when Task 2 lands.

## Task 4 — Ring-level join semantics *(unblocked)*

Spec: `docs/decisions/001-ring-vs-tower-joins.md`. Implement to it.

Two findings there will save a wrong turn. Neither `dove` nor `towers` is a
tower register — both repeat `TowerID`, `towers` far worse — so "join `towers`
instead" inflates by 1,439 rows rather than fixing 19. And the current join
silently *drops* 160 records as well as duplicating 19.

Acceptance test: `method_performances` joined to the new `v_towers_unique` must
return exactly **22,111**, the number of rows carrying a `dove_tower_id`. A join
cannot create or destroy a linked record, so anything else is wrong.

---

## Task 5 — Backfill completeness gate *(merged, with three fixes)*

> **Reviewed and merged 2026-08-15.** The mechanism is right and the external
> claims check out: I re-queried `search.php` live and got 25,267 for 2024 and
> 1,792 for January 2024, matching this write-up exactly. The full range now reads
> 336,689 rather than 336,654 — not a discrepancy, the corpus grew by 35 in five
> days, which is worth knowing about a denominator that moves.
>
> Three things were changed on merge; the account below is Vibe's and is otherwise
> unedited.
>
> 1. **The gate measured completeness with a row count that included duplicates.**
>    `store_performances` returned `len(perf_rows)`, and duplicates are appended to
>    that list, so a window returning 1,000 unique records plus 800 duplicates of
>    them measured 1,800 against an expected 1,792, passed, and was checkpointed
>    complete with 792 records missing. That is the exact pathology this task's own
>    size-signal investigation identifies. It now returns and gates on
>    `len(seen_ids)`, and a window containing any duplicate at all fails rather
>    than passing on its unique count.
> 2. **The 5% tolerance had no measurement behind it.** Measured on merge across
>    six windows: `search.php` and `export.php` agree exactly, every time. Default
>    is now 0, with `--window-tolerance` to raise it and a comment recording the
>    measurement rather than an assumption.
> 3. **`None` meant two different things** — "no performances" and "the regex did
>    not match". `process_window` treated both as complete, so a BellBoard template
>    change would have turned every window into a silent pass.
>    `fetch_expected_count` now raises on a body it cannot parse and reserves
>    `None` for the page that actually says no performances match.

### Vibe's account, as submitted

**Done.** `scripts/bellboard_common.py` gained `fetch_expected_count`,
which parses the "Found N performances" count BellBoard's `search.php`
renders in HTML (verified: 25,267 for 2024, 1,792 for Jan 2024, None
for an empty window). `scripts/backfill_bellboard.py` now:

1. Asks `search.php` for each window's expected count before fetching,
   and refuses to checkpoint a window whose fetched total falls more
   than 5% short (retrying with a longer cool-off, then failing).
2. Compares the DB row count for the whole range against `search.php`'s
   corpus count at the end, and exits non-zero on a material shortfall.
3. Bumps the checkpoint to `version: 2`, so a checkpoint from the
   broken run (which marked truncated windows complete) is discarded
   rather than resumed. `--reset-checkpoint` discards explicitly.
4. Counts duplicate `perf_id`s within a window to surface the
   re-fetching that inflated the original run's raw artefact.

Definition of done met: a bounded run over January 2024 loaded
1,792 rows (matching `search.php` exactly) and exited 0; an
artificially truncated window (one page, 1,000 of 1,792) was not
checkpointed and exited 1. The full backfill is not run here — it is a
long job and cannot reach production until 2026-09-01.

**Size-signal investigation.** The broken run produced ~2.0 KB/row
against Gemini's ~1.0 KB/row while holding fewer unique records. The
committed `data/bellboard/` CSVs — the same export format — measure
~0.5 KB/row even including ringers, footnotes and flags, so the
discrepancy is not an artefact of the format. Clean `export.php`
pagination is non-overlapping (Jan 2024: 1,792 unique IDs across two
pages, zero duplicates), so pages do not overlap each other within a
window under normal operation. That leaves overlapping *date windows*
(the loop not advancing, or `changed_since` semantics leaking in) as
the cause: the same performances re-fetched, collapsing via
`INSERT OR REPLACE` in the DB but inflating the raw cache. The gate's
per-window duplicate counter and final range count would both surface
this.

Original brief, retained for reference:

The backfill runner is merged and the run it produced is **wrong**: 55,000 rows
against a true corpus of **336,654**. It captured 16% and reported success.
Full adjudication with the measurements is in
`docs/decisions/002-backfill-count-discrepancy.md`.

This is not a criticism of the runner's design — it was defeated by a server
that truncates silently, which is the hazard the brief led with. What it lacks
is a way to *know* it was truncated.

**Ground truth, measured 2026-08-09.** BellBoard's `search.php` reports a
result count for any window, cheaply, in the HTML:

```
https://bb.ringingworld.co.uk/search.php?from=2023-01-01&to=2023-12-31
  -> "25,859 performances"
```

2023: 25,859 · 2024: 25,267 · 2012-01-01 to 2026-08-09: **336,654**.

**What to add**

1. **A per-window expected count.** Before fetching a window, ask `search.php`
   what it holds. After fetching, compare. A window that returns materially
   fewer rows than advertised is throttled, not finished.
2. **Refuse to checkpoint a short window.** Retry it with a longer cool-off;
   after repeated failures, stop the run and exit non-zero. Silence is the bug
   — a truncated run must be loud.
3. **A final total check.** At the end, compare rows loaded against the
   corpus count for the full range and report both. Do not print a success
   message when they disagree.
4. **Discard the existing checkpoint file.** It marks windows complete that are
   not, so a resumed run would inherit the gap. Start clean.
5. **Investigate the size signal.** The run produced ~2.0 KB per row against
   Gemini's ~1.0 KB, while holding fewer unique records — consistent with the
   same performances being fetched repeatedly, which would happen if windows
   are not advancing or `changed_since` semantics have leaked into the window
   loop. Confirm or rule this out and say which in the PR.

**Definition of done:** a bounded run over one known window — 2024, say —
loading a row count that matches 25,267, and a demonstration that an
artificially truncated window causes a non-zero exit rather than a checkpoint.
Do not attempt the full backfill in the PR; it is a long job and the freeze
means it cannot reach production until 2026-09-01 regardless.

---

## Task 6 — Place-notation parser *(withdrawn — already built)*

Claude Code needed this for the Blue Line Atlas and wrote it:
`scripts/notation.py`, verified on 24,404 of 25,066 methods against the
library's published `lead_head`. Not yours to redo. Noted here rather than
deleted so nobody wonders where the task went.

---

## Task 7 — A ringing career, from the bell people stand behind *(after item 20)*

**Done.** `queries/findings/ringing_careers.sql` plus `docs/ringing_careers.md`.
Three findings, on the cohort of 5,657 canonical ringers (50+ tower-bell
appearances, 5+ year span): the median ringer rings sixteen appearances
before a first conducted peal; almost nobody settles on one bell (8.5% ring
half or more of their appearances on it, drift from first-10 to last-10 apps
is −0.0032, a wash); and roughly six in ten ringers first seen in 2013–17
have no reported appearance five years later. The SQL groups raw names
(the identity CSV is a file, not a table, and the query must prepare in CI);
the doc gives the canonical-id figures, 99.8% of rows resolve, and the two
agree on every structural finding.

Original brief, retained for reference:

`performance_ringers.bell` is populated on **1,897,741 rows** and nothing in this
project has ever read it. It is the most underused column in the corpus.

Every ringer knows the progression: you learn on the treble, move to the inside
bells, and the tenor or the conducting comes later. Nobody has watched it happen
to real people at scale. **6,563 ringers have 50 or more appearances spanning
five or more years** — enough to trace an individual arc.

### Three questions, and the third needs care

1. **How long is the apprenticeship?** Appearances before a first conducted peal.
2. **Is the progression real?** Or do most people find a bell and stay on it for
   twenty years? I would bet on the second; measure it rather than assume either.
3. **What does leaving look like?** A ringer's last appearance is in the data.

On the third: **an absence is not a death or a resignation, it is an absence.**
Publish attrition as a cohort rate — "of ringers first seen in 2014, N% have no
appearance after 2020" — never as a statement about an individual, and never a
list of names. The corpus cannot distinguish someone who stopped ringing from
someone who moved, changed name, or rings at a tower that does not report.

### Data notes, measured

- `bell` holds single bells (`'1'`, `'11'`) and handbell pairs (`'1-2'`, and
  runs up to `'1-2-3-4-5-6-7-8-9-10-11-12-13-14'`). Handle both; the pairs are
  handbell performances and are a different activity.
- Bell number alone is not comparable across towers: the tenor of a six is the
  6, of a twelve the 12. **Normalise by the number of bells rung** or the
  comparison is meaningless.
- Identity comes from `data/ringer_identity_candidates.csv`, 55,326 canonical
  entities. It is a candidate dataset with unmeasured accuracy; say so.

### Deliver

`queries/findings/ringing_careers.sql` plus a short `docs/ringing_careers.md`
with the numbers and the caveats above. A page can come later if the finding
justifies one.

**Branch fresh from `main`.** `scripts/check_branch_safety.py` runs on every pull
request and fails a branch cut from a stale base.
