# Task brief: BellBoard historical backfill runner (Mistral Vibe)

Dispatch as a single bounded coding task, delivered as a pull request against
`main`. Do not push directly, and do not run the backfill itself as part of
the PR -- the deliverable is the runner, not the loaded data.

Verified against the live sources and the live database as of 2026-08-09.

Paste from the horizontal rule onward.

---

> **DATABASE FREEZE IN EFFECT (2026-08-09).** The Turso database breached its
> daily row-read limit. Until the owner lifts this freeze, **do not run
> anything against the live database** -- no loads, no exploratory queries, no
> verification runs. Write the code and say in the PR that it is unverified
> against production for this reason. That is an accepted answer right now; a
> PR that quietly ran against production is not.

You are working on `nihilisticiconoclast/change-ringing`. The database holds
three corpora already: Dove's Guide (7,262 ringing towers, 63,894 bells),
the CCCBR Methods Library (25,055 methods, 30,734 first-performance events),
and BellBoard performances -- but only **1,401** of those, a single recent
window. The whole point of the BellBoard corpus is the historical record, and
it is missing.

Read `README.md`, `docs/CONNECTING.md`, `data/SOURCES.md` and, most
importantly, `scripts/ingest_bellboard.py` -- you are extending its capability,
and it already solves most of the hard parts.

## Deliverable

`scripts/backfill_bellboard.py` -- a resumable, checkpointed, politeness-aware
runner that walks the BellBoard corpus back through time and loads it using the
existing ingestion logic. Import and reuse `ingest_bellboard.py`'s parsing and
insert helpers; do not fork them. If that means refactoring shared pieces into
importable functions, do that as part of this PR and keep the existing script's
CLI behaviour unchanged.

Plus a short section in `README.md` describing how to run and resume it.

## Why this needs its own runner

`ingest_bellboard.py --changed-since` works, but it is built for a small daily
delta. A backfill differs in three ways that matter:

1. **It cannot be assumed to finish in one process.** It must checkpoint
   progress durably and resume from where it stopped, without redoing
   completed work and without leaving a gap if it is killed mid-page.
2. **It must be gentle over a long run.** See the throttling section below --
   this is the part most likely to go wrong.
3. **Its size is unknown.** Nobody has measured the corpus. Your runner should
   be able to report progress and be stopped and restarted freely, rather than
   depending on an up-front estimate.

## Critical: BellBoard throttling

**BellBoard answers sustained querying by silently truncating responses, not by
returning an error status.** This was measured directly: a request that
returned 1,000 performances returned 12 a few minutes later, HTTP 200 both
times, with no error body. A naive loop reads a short page as "end of data" and
stops early, producing a partial corpus that looks complete.

`ingest_bellboard.py` already handles this -- a short page triggers a cool-off
and one re-fetch, and only a re-fetch returning the same count is treated as
genuinely final. **Preserve that behaviour and strengthen it for long runs.** At
minimum: keep the inter-page delay (default 3s, do not lower it), and treat
repeated short pages as a signal to back off harder rather than to finish.

Be conservative. This is someone else's server and a backfill is the most
demanding thing this project will ever ask of it. A backfill that takes a day
and is correct beats one that takes an hour and gets throttled into silently
dropping half the corpus.

## Approach

`changed_since` orders by modification date, which is the wrong axis for a
historical walk -- an old performance edited last week sorts as recent. Use
dated windows instead, and make the window the checkpoint unit: record each
window as pending/complete in a small local state file (or a table, your
choice -- justify it), so a resumed run skips completed windows. Windows should
be small enough that losing one to a crash is cheap.

Note that `export.php` rejects `pagesize` above 10,000 with HTTP 413, and that
`date_from`/`date_to` are **not** valid `export.php` parameters -- I tried them
and got zero results. Establish which date parameters the endpoint actually
honours before building on an assumption, and say in the PR what you found.
`search.php` accepts a different parameter set from `export.php`; the API notes
at https://bb.ringingworld.co.uk/help/api.php are incomplete and explicitly
invite questions.

## Critical: constraints already paid for in this codebase

These are not hypothetical; each cost real debugging time here.

- **Never use `conn.executemany()` against Turso.** Measured at 4.1 rows/s, and
  it stalls outright on long runs. Multi-row `INSERT ... VALUES (...),(...)`
  runs at ~1300 rows/s. Reuse the existing `insert_many()` helper.
- **Keep statements under SQLite's 32766 bind-parameter ceiling** by deriving
  batch size from a parameter budget, as the existing scripts do.
- **Never use double quotes for a SQL string literal.** libSQL treats them as
  identifiers and rejects the query; local SQLite silently falls back to
  treating them as strings. This exact bug shipped in the last PR and only
  surfaced against production.
- **`--local-db` testing is necessary but not sufficient.** Three separate bugs
  in this project were invisible locally and only appeared against Turso: the
  NaN-to-NULL coercion, the double-quoted literal, and `executemany` stalling.
  Do not report a loader as verified on the strength of a local run.
- **Writes must stay idempotent.** `INSERT OR REPLACE` on BellBoard's own ID,
  child rows cleared before reinsert. Overlapping windows must converge, not
  duplicate -- this is what makes resumption safe.

- **Watch rows read, not just wall-clock time.** Turso meters rows read. This
  database holds ~130,000 rows and billed 591 million reads in one day, from
  two statements that both looked ordinary: a view whose join the planner drove
  off a low-selectivity column (396 million reads for a single `COUNT(*)`), and
  an update matching on three `COALESCE`-wrapped columns, which no index can
  serve (139 million per run). Run `EXPLAIN QUERY PLAN` on anything that
  touches a whole table. A `SCAN` inside a correlated subquery means you are
  paying the product of two tables.
- **Batching fixes latency, not read cost.** The two versions of that update
  took 18 minutes and 19 seconds and read exactly the same 139 million rows.
  Do not assume a fast script is a cheap one.
- **`dove.TowerID` is not unique** -- 13 towers hold more than one ring -- so
  joining on it alone fans out and inflates counts. See `docs/CONNECTING.md`.

## Explicitly out of scope

- Do not run the full backfill and commit the results. Demonstrate the runner
  on a bounded window and report what you observed.
- Do not modify `schema/001_*`, `002_*`, `003_*`, `scripts/migrate_csv_to_turso.py`,
  `scripts/ingest_methods.py` or `scripts/resolve_method_locations.py`.
  Refactoring `ingest_bellboard.py` for reuse is in scope; changing what it
  does is not.
- Do not touch `data/method_location_candidates.csv` -- another task owns it.
- **Do not take on the Gemini task in `docs/tasks/`.** The previous PR did both
  agents' work in one branch, which defeated the point of splitting them. Stay
  inside this brief.

## Definition of done

A PR against `main` containing the runner, whose description reports: which
date parameters `export.php` actually honours, a bounded demonstration run with
real numbers (windows completed, performances loaded, throttle events observed),
what the checkpoint format is and how to resume, and your best estimate of the
full corpus size with the evidence behind it. If you could not determine the
corpus size, say so plainly rather than guessing -- an honest unknown is more
useful here than a confident number.
