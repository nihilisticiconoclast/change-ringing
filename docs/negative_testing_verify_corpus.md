# Negative Testing the Corpus Integrity Checker

> **Summary:** Every one of `verify_corpus.py`'s 51 checks, deliberately
> broken in isolation, with the ones that could not be made to fail recorded
> rather than hidden.
> Delivers Roadmap item **[R-44](ROADMAP.md)** / Vibe task **V-9**.
> Tests: [`tests/test_verify_corpus_negative.py`](../tests/test_verify_corpus_negative.py)
> | Fixture: [`tests/verify_corpus_fixture.py`](../tests/verify_corpus_fixture.py)

---

## 1. Why this task exists

`scripts/verify_corpus.py` is the most load-bearing file in the repository,
and until now its 51 checks were assertions nobody had falsified. Three
times already, a check in this project has reported green at the exact moment
it stopped working:

- PR #21 — a circular oracle that validated a classifier against itself;
- PR #24 — a hardcoded name string standing in for a measured lookup;
- PR #26 — the CompLib CSV-agreement check reporting `SKIP` when
  `compositions.csv` was moved aside, while 86,054 rows sat in the database:
  the exact condition the check existed to catch.

A check that cannot fail is worse than no check: it reports success and
stops anyone looking. So the brief for R-44 was to break each check
deliberately, confirm it fails, and **record which ones could not be made to
fail** — knowing which checks are decorations is worth more than proving the
ones that work.

The prediction was recorded first, as H30 in
[`HYPOTHESES.md`](HYPOTHESES.md): given that history, a fair share of the 51
would turn out to be decorations. The measurement said otherwise.

## 2. What was measured

### The fixture

Each break needs a database that everything *else* in the checker still
accepts — otherwise a FAIL proves nothing about the check it was aimed at.
The real replica takes ~90 seconds and a network to build (which is why CI
cannot run the data checks at all, R-27), so
[`tests/verify_corpus_fixture.py`](../tests/verify_corpus_fixture.py) builds
the smallest database the checker calls healthy:

- the **committed schema files** (`schema/001`–`007`) are applied as-is, so
  the fixture cannot drift from the schema the way a retyped CREATE TABLE
  list would;
- a handful of rows per table, shaped around the checker's own invariants:
  `dove` repeats one TowerID across two rings and `towers` across a
  full-circle ring *and* a chime (decision 001's fan-out), `performances`
  carries a handbell row with no tower and a drift orphan under the 5,000
  ceiling (the shapes decision 001 documents), and the CSVs under `data/`
  match the table rows exactly (csv-agreement is exact, not a range);
- builds and all 51 checks run in **~0.12 seconds**, no network, so the
  suite runs in CI on every pull request.

The baseline is 51 checks, 0 failures, no SKIP the fixture could have
avoided.

### The method

58 tests, one break each: drop a table, empty a table, delete or add rows
against the committed CSVs, make a TowerID unique, orphan an adjudicated
link, flood orphans past the drift ceiling, redefine `v_towers_unique` so the
join drops or inflates, write a literal `'nan'`, drop the read-cost indexes,
delete a CSV while its rows stay loaded. Each test asserts the target check
reports FAIL **and nothing unexpected does** — collateral is named per break
(dropping a table also drops its indexes and orphans its CSVs), so a FAIL
that belongs to damage rather than the break fails the test.

## 3. The results

**45 of 51 arms FAIL cleanly when broken.** Every table, view and
read-cost-index existence check; the empty-table arm of every row-count
check; all six BellBoard and both CompLib csv-agreement checks, in both
directions (missing rows and extra rows) plus the absent-CSV-with-rows-loaded
hole from PR #26; both TowerID fan-out checks; both orphan checks (the
adjudicated zero, and the drift ceiling); both join-identity checks, broken
in both directions (a view that drops linked records, and a view that
inflates the join); the nan check; and all four plan assertions, including
the 396M-rows-read regression shape (composite index dropped, single-column
indexes left in place).

### The six that cannot be made to FAIL — the decorations, named

The four **optional-corpus table** checks and the two **optional-view**
checks:

| Check | Break tried | What happens |
| --- | --- | --- |
| `table performance_methods` | dropped from a populated database | `SKIP` |
| `table performance_method_unresolved` | dropped from a populated database | `SKIP` |
| `table compositions` | dropped from a populated database | `SKIP` — but `csv agreement compositions` FAILs, so the loss is caught |
| `table composition_methods` | dropped from a populated database | `SKIP` — but `csv agreement composition_methods` FAILs |
| `view v_performance_methods` | dropped from a populated database | `SKIP` |
| `view v_composition_methods` | dropped from a populated database | `SKIP` |

The root cause is the same for all six: `OPTIONAL_TABLES` and
`OPTIONAL_VIEWS` in `verify_corpus.py` decide absence is benign, and the
database alone cannot distinguish "this migration was never applied" from
"this migration was applied and then lost". Nothing in a bare SQLite file
records which of the two it is looking at.

Is this a defect? Mostly no. For the two CompLib tables the committed CSV
means csv-agreement catches any real loss, so the SKIP costs nothing. For
`performance_methods`, `performance_method_unresolved` and the two optional
views, there is no committed artifact to compare against — a checker that
sees only the database has no way to know the table once held rows, and
reporting FAIL on every database that legitimately skipped schema/005 would
break the valid builds. The honest fix is provenance, not a stricter guess:
when R-48 commits the remaining sources the way `data/complib/*.csv` is
committed, these arms can be exact the way the CompLib ones now are. Until
then, a SKIP that sometimes means "lost" is a known limit, pinned by
`TestOptionalCorpusArms` so it cannot silently change.

### Six breaks make the checker crash rather than report

Dropping `dove`, `towers`, `methods`, `method_performances`,
`performances` or `v_towers_unique` makes a *later* check raise
(`sqlite3.OperationalError`, e.g. `check_orphan_soft_fks` querying a `dove`
that no longer exists, or `check_query_plans` EXPLAINing a view whose source
is gone). As shipped, `main()` aborts at the first traceback: the exit code
is non-zero — loud, and gating still works — but the report is truncated, so
checks after the crash are never run.

The fixture's `run_checks()` isolates each check function and records a
crash as `crash: <function>` with status FAIL, so the rest of the report
still runs and the tests can name the crash in their expected sets. Whether
`verify_corpus.py` itself should catch per-check exceptions is left as a
 judgement for review: a truncated report that is always loud is defensible,
 and "fixing" it might hide a crash behind a FAIL line that reads calmer
 than the truth.

### The arms that cannot FAIL on any non-empty database, by design

The `INFO` arm of each row-count range check (a non-empty count outside its
committed range) can never FAIL — and should not: the sources genuinely
grow, and a range check that FAILs on growth turns every corpus refresh
into a red build. The FAIL arm is the empty table, which is exactly the
failure mode that shipped (`performance_flags` reported 0 for weeks because
0 was inside the expected range; the fix made an empty table a FAIL). That
asymmetry is the right trade and is documented in the checker itself; the
empty-table FAIL arms are all proven here.

## 4. What a reviewer should check first

The claim "45 of 51 FAIL cleanly" is only as good as the fixture. The
weakest points, in order:

1. **The fixture is small, and planners change their minds on small
   tables.** The plan assertions pass on 3–5 rows where the real replica has
   thousands; a query plan that serves a five-row table without an index
   would make the fixture *more* permissive than the real database, not less.
   The suite was also run against the real replica
   (`build_local_db.py --out local_corpus.db`, 51 checks, the one known
   R-48 failure) to confirm the checker itself behaves identically; the
   breaks are fixture-only by design.
2. **The collateral sets are measured, not guessed** — each is the exact
   non-PASS output of a probe run. If a future change to the checker makes
   a break trip one more or one fewer check, the test fails and says which.
3. **The six crashes are recorded, not fixed.** If review prefers
   `verify_corpus.py` to report a clean FAIL for each, the change is
   contained in the fixture's `run_checks()` expected sets.

## 5. Verification

- `python tests/test_verify_corpus_negative.py` — 58 tests, all pass,
  ~5 seconds, no network, no replica needed.
- `python scripts/run_tests.py` — 135 tests, all pass (8 pre-existing skips
  awaiting a replica at the gitignored `data/change-ringing.db`, R-27).
- `python scripts/build_local_db.py --out local_corpus.db` then
  `python scripts/verify_corpus.py --local-db local_corpus.db` — 51 checks;
  the one failure is the known R-48 orphan drift (9 adjudicated links cite
  Dove-removed TowerID 25219), present on a fresh rebuild of `main` before
  this PR and unrelated to it.
- `python scripts/verify_docs.py`, `python scripts/verify_chrome.py`,
  `python -m compileall -q scripts/` — clean.
