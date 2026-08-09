# Roadmap: Mistral Vibe

A queue rather than a single task, so work can continue without waiting for a
new brief each time. **Do one task per pull request**, in order, and stop at
the end of each for review — the later tasks are deliberately sketched rather
than fully specified, because what they should say depends on what the earlier
ones find.

| # | Task | State |
| --- | --- | --- |
| 1 | BellBoard historical backfill runner | Merged, but **the run failed** — see Task 5 |
| 2 | CompLib ingestion | **Active** — full brief below |
| 3 | Corpus integrity checker | Queued — sketch below |
| 5 | Backfill completeness gate | **Urgent** — brief below |
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

## Task 2 — CompLib ingestion *(active)*

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

## Task 3 — Corpus integrity checker *(queued)*

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

## Task 5 — Backfill completeness gate *(urgent, do this before Task 2)*

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