# Inconsistencies and Bugs

> **Status, 2026-08-15.** Raised by Cursor, submitted by Gemini as PR #16, merged
> after **every claim was checked**. Ten of the thirteen documentation items were
> real and are now fixed; two were already stale by the time the audit landed; one
> was wrong. Four code issues were real and three of those are fixed. The rest is
> triaged into `docs/ROADMAP.md` with an owner.
>
> The original text is kept below unedited, with a verdict line under each item,
> because an audit whose own accuracy is not recorded is just another document to
> take on trust. **Nineteen of twenty-three checkable claims held** — a far better
> hit rate than this project's own predictions manage (see `docs/HYPOTHESES.md`),
> which is what you would expect: reading a repository for inconsistency is a much
> easier problem than predicting what data will say.
>
> | | |
> | --- | --- |
> | ✅ **Fixed** | Real, and corrected in the merge commit |
> | 📋 **Triaged** | Real, too big for the merge, now a roadmap item with an owner |
> | ⏳ **Already stale** | Was true when written; overtaken by work landing the same day |
> | ❌ **Not a defect** | Checked and did not reproduce |


## 1. Gaps and Inconsistencies in Documentation

### Stale or contradictory content

1. **`README.md` BellBoard section (lines 345–347)** still says *"The corpus currently holds only a small recent window"* — contradicts the Status section above it (293,471 performances, 2012–2024 complete).
   ✅ **Fixed.** That whole section now says the record is complete and reframes
   the runner as what fetched it.

2. **`docs\tasks\gemini-roadmap.md` header table** says Task 6 backfill is *"Next: 2017 backwards to 2012"* — backfill is finished per `ROADMAP.md`, `SOURCES.md`, and `README` Status.
   ✅ **Fixed.** Table row now reads Done.

3. **Same file, Task 3 section** still marked *"blocked"* on thin data, but the summary table says **Done** and `ROADMAP.md` item 9 says ringer identity is **unblocked**.
   ✅ **Fixed.** Section heading now reads *(done — candidate dataset delivered)*.

4. **Same file, Task 1 section** still titled *"active"* though the table marks it Done.4. **Same file, Task 1 section** still titled *"active"* though the table marks it Done.
   ✅ **Fixed.** Now *(done — PR #3)*.

5. **`README.md` Status checkboxes** still open for CompLib linkage and ringer identity resolution, while roadmaps mark related work done (ingestion merged; identity candidates delivered).
   ✅ **Fixed.** Both ticked, with the ringer-identity entry carrying the caveat
   that its accuracy is unmeasured — ticking it without that would be worse than
   leaving it open.

6. **`scripts/build_local_db.py` docstring** says BellBoard replica is *"a single window rather than the full history"* — committed CSVs now cover 2012–2024.
   ✅ **Fixed.**

7. **Rhythm page window:** README says page is restricted to 2021–24 while also noting corpus runs 2018–24; widening is Claude's explicit next task.
   ⏳ **Already stale in one respect** — the corpus is 2012–24, not 2018–24. The
   substance stands: the Rhythm page is still the one analysis narrower than the
   corpus, deliberately, and it is item 1 in Claude Code's queue.

### Missing or ambiguous references

8. **`docs\tasks\gemini-location-resolution.md`** referenced in three places but **file absent** — location work is done (`method_location_adjudication.csv`), so the brief may have been removed without updating references.
   ✅ **Fixed, and the diagnosis was exactly right.** The brief was deleted in
   86b8252 ("Replace completed task briefs with the next two") once the work
   landed, and three references were left dangling. They now point at
   `docs/method_location_resolution.md`, which is the surviving account.

9. **`data/change-ringing.db`** is **gitignored** (removed after hitting size limits) but `queries\README.md`, both agent roadmaps, and `rebuild_all.py` still describe it as a *"committed snapshot"* you can query directly — you must build it locally instead.
   ✅ **Fixed** in five places. `queries/README.md` now opens with the build
   command instead of a `sqlite3` invocation against a file that is not there.

10. **Generated datasets** (`data/footnote_occasions.csv`, `data/ringer_identity_candidates.csv`) are produced by `rebuild_all.py` but not present in the committed `data/` tree — docs refer to them as if they exist after a rebuild.
   ❌ **Not a defect.** Both are committed and tracked:
   `git ls-files data/` returns `data/footnote_occasions.csv` and
   `data/ringer_identity_candidates.csv`. Only `change-ringing.db` is gitignored.

### Minor count / wording drift

11. Footnote counts oscillate between **113,895** (four-year window / occasions page) and **337,946** (full corpus) across docs — intentional but easy to misread.
   ⏳ **Already stale.** Reconciled earlier the same day; every live figure now
   reads 337,946 and the 113,895 mentions that remain are explicitly historical.

12. **`mistral-vibe-roadmap.md` Task 4** still listed *"unblocked"* though schema/007 and decision 001 are merged.
   ✅ **Fixed.** Now *(done — decision 001 adopted)*.

13. **Untracked working files** in git status (`data/complib/page_*.json`, scratch scripts) suggest an in-progress partial CompLib fetch not yet integrated.
   ⏳ **Already stale.** Working tree is clean; those were transient. `.gitignore`
   gained `data/complib/`, `scratch/`, `*_output.txt` and `*.log` from PR #13, so
   they will not reappear in `git status`.

---

## Verdicts on sections 2–6

Sections 2 to 6 are triage rather than a defect list, so they are annotated here
in one place rather than line by line.

**Fixed in the merge commit**

| Item | What was done |
| --- | --- |
| Bare `except:` in two builders | Narrowed to `(TypeError, ValueError)` with a comment saying what the non-numeric values actually are — handbell pairs like `1-2`, and `changes` being nullable. A bare `except:` also swallows `KeyboardInterrupt`. |
| `fetch_dove_csvs.py` has no retries | Four attempts with exponential backoff. It is the **first** step of `build_local_db.py`, so one transient blip was throwing away the whole ninety-second build. |
| CompLib partial failure exits 0 | **The one genuine correctness bug in this report.** On a mid-corpus page error it logged, broke, wrote partial data and returned 0 — so a run that died on page 40 of 3,442 was indistinguishable from a complete load to anything querying afterwards. It now records the reason, still writes what it has (the cache makes resuming cheap), and **exits 1**. Verified by injecting a failure on page 2: exit code 1, 25 compositions still written. This is the same shape as the backfill that captured 16% of BellBoard and exited clean — see `docs/decisions/002`. |

**Triaged to the roadmap**

| Item | Owner | Roadmap |
| --- | --- | --- |
| No pytest suite; `notation.py`, resolvers and builders untested | **Vibe** | Item 26 |
| CI cannot catch replica staleness — `verify_corpus.py` needs a built database | **Claude Code** | Item 27 |
| Inconsistent DB access: some scripts use stdlib `sqlite3`, ingestion uses `db.py`/libsql | **Vibe** | Item 28 |
| `scratch/` mistakable for authoritative pipelines | **Claude Code** | Item 29 |
| Full CompLib load never run | **Vibe** | Item 20, already open |

**Accepted as-is, with reasons**

- **`executemany` in `build_local_db.py`.** The guidance it appears to violate is
  about a *remote* primary, where `executemany` costs a round trip per row.
  `build_local_db.py` is local-only by construction, and `db.py` refuses a remote
  connection without an environment variable nobody sets. Correct as written.
- **BellBoard deletions not tracked.** A known property of the source, documented
  in `data/SOURCES.md`. There is no deletion feed to consume.
- **The 2022 record shortfall.** One performance, filed upstream after 2022 was
  fetched. Recorded rather than silently corrected, which is the point.

**One item that was simply out of date**

Section 5 says the real oracle "was never delivered". It was delivered the same
day, in PR #14: 400 independently labelled footnotes, overall accuracy **75.5%**,
every per-class figure reproduced on merge. See
`docs/footnote_occasion_accuracy.md`.

---

## 2. Quality Gaps

| Gap | Detail |
| :--- | :--- |
| **No pytest/unittest suite** | Only ad-hoc `scratch/*.py`; `verify_corpus` negative test is manual (corrupt a copy) |
| **Inconsistent DB access** | `classify_footnote_occasions.py`, `fetch_and_export_bellboard.py` use stdlib `sqlite3`; ingestion uses `db.py` / `libsql` |
| **`build_local_db.py` CSV load uses `executemany`** | Fine for embedded local; violates Turso guidance if ever pointed remote |
| **Bare `except:` in some builders** | e.g. `build_nexus_page.py`, `build_occasions_page.py` |
| **CompLib partial failure** | On page fetch error, logs error, breaks loop, still writes partial data, returns 0 — silent incompleteness |
| **`fetch_dove_csvs.py`** | No retries; single `urlretrieve` |
| **BellBoard deletions** | Explicitly not handled — corpus is "complete-plus" |
| **Full CompLib load not committed** | ~86k compositions / ~3,400 pages designed but not run in repo |

---

## 3. Known Issues (from Code, Comments & Docs)

| Issue | Where Documented |
| :--- | :--- |
| **First backfill captured 16% of corpus, reported success** | `docs\decisions\002-backfill-count-discrepancy.md`, Task 5 roadmap |
| **Duplicate counting in completeness gate (fixed on merge)** | Task 5 roadmap |
| **5% window tolerance had no measurement (now 0)** | `bellboard_common.WINDOW_TOLERANCE` |
| **`performance_flags` never loaded until verify caught it** | `build_local_db.py` comment |
| **Empty CSV cells → `''` not `NULL` broke `IS NULL` checks** | `build_local_db.py` |
| **Literal `"nan"` strings from pandas round-trip** | `verify_corpus.check_nan_strings`, `migrate_csv_to_turso.py` |
| **`dove.TowerID` / `towers.TowerID` not unique — join inflation** | `docs\decisions\001`, `CONNECTING.md` |
| **591M row-reads/day from missing indexes + bad plans** | `schema\004` header, verify plan checks |
| **Double-quoted SQL literals: sqlite3 accepts, libSQL rejects** | `db.py` |
| **Method linkage step had double-sys.executable bug (fixed)** | `build_local_db.py` comment |
| **CompLib `methodid` → `'m'+id` resolves ~11/12 sampled; spliced = null** | `ingest_complib.py` docstring |
| **Footnote classifier explicitly unvalidated candidate** | PR #7, `classify_footnote_occasions.py` |

---

## 4. Bug-Prone / Needs-Review Areas

- **`ingest_complib.py` error handling on mid-corpus page failure:** Breaks, writes partial, exits 0. Should probably exit non-zero or refuse commit.
- **`fetch_and_export_bellboard.py` vs `ingest_bellboard.py`:** Two paths; easy to run wrong one (now heavily documented).
- **Replica drift after CSV merge:** Mitigated by `check_csv_agreement`, but CI doesn't run it; relies on local `rebuild_all.py`.
- **`scratch/` analysis scripts:** Ad-hoc scripts accumulate and can easily be mistaken for authoritative pipelines.

---

## 5. Test Coverage Gaps

There is no pytest/unittest suite in the repo. Testing is ad hoc and operational:

| What exists | What it covers | Gap |
| :--- | :--- | :--- |
| **`verify_corpus.py`** | DB integrity, CSV agreement, query plans | Not run in CI; requires built replica |
| **`verify_chrome.py`** | Nav/footer consistency across published pages | Static HTML only; no data correctness |
| **PR CI SQL parse** | Schema + all query files syntax | No data, no result assertions |
| **`check_branch_safety.py`** | Stale-branch / rejected-work detection | Process, not code correctness |
| **`scratch/test_query.py`** | Ad-hoc query print | Not a test; lives in scratch |
| **`scratch/classifier_test.py`, `oracle_eval.py`** | Footnote classifier experiments | Not integrated into CI or verify pipeline |

### Specific untested areas:
- **Ingestion scripts (`ingest_bellboard.py`, `ingest_methods.py`, `ingest_complib.py`):** No automated regression tests.
- **Resolvers (`resolve_performance_methods.py`, `resolve_method_locations.py`, `resolve_ringer_identities.py`):** Oracle exists for spliced methods (~69.7%) but not wired to CI.
- **Page builders:** No snapshot/golden-file tests for embedded JSON output.
- **`notation.py` parser:** Validated manually (99.7% at Minor/Major) but no test file.
- **libSQL vs stdlib sqlite3 divergence:** Documented in `CONNECTING.md`; only partially guarded.
- **Footnote occasion classifier:** Circular self-evaluation reported 100%; real oracle (300 labelled footnotes) never delivered.

---

## 6. Technical Debt Signals

### Active / documented:
- **Caveats scattered:** Roadmap item 12: consolidate across `CONNECTING.md`, `SOURCES.md`, `method_location_resolution.md`, schema headers, commit messages. Partially addressed by `site_chrome.py` but not complete.
- **Rhythm page window lag:** Still 2021–24 while corpus is 2012–24; widening changes anomaly detection materially (`AGENTS.md` queue item #1).
- **Production frozen:** Turso load of full 2012–24 backfill blocked until 2026-09-01; local replica is the only trustworthy build path.
- **CompLib not fully loaded:** Schema exists; 86k compositions available but full ingestion is Vibe roadmap item 20. Three sample JSON pages in `data/complib/` are untracked scratch.
- **Method extension lineage incomplete:** `extension_construction` populated for only 1,851 of 25,055 methods.
- **Performance→method linkage gaps:** 22.1% unresolved; spliced ellipsis expansion stuck at 69.7% (1,487 rows one method short).
- **Footnote classifier unvalidated:** Dataset merged without precision/recall oracle; occasions page uses keyword patterns, classifier CSV unused for measurement.
- **2022 corpus one record short:** 28,212 vs 28,213 on `search.php`; documented, not silently corrected.
- **BellBoard deletions not tracked:** Removed upstream performances persist until full reload.
- **No CI database build:** Deliberate cost trade-off; stale replica can pass all CI checks while being a year behind CSVs (exactly what `verify_corpus.py` was written to catch, locally).
- **Ringer identity resolution:** Name-based, no person ID; co-occurrence matching unvalidated at scale.
- **Query/script drift history:** Multiple incidents where recorded SQL diverged from what scripts actually ran (`extract_ringer_performances.sql` fixed 2026-08-15); pattern guarded by `sqlfile.py` and CI parse step but not result-level regression tests.
- **Scratch directory pollution:** Untracked files in git status (`scratch/`, `data/complib/page_*.json`, `rebuild_output.txt`) suggest work-in-progress not yet integrated.

### Positive signals (debt being actively paid down):
- Decision docs with measured acceptance tests.
- `rebuild_all.py` fails loudly (fixed from silent-success Gemini PR).
- Read-cost indexes and `EXPLAIN` plan assertions.
- Recorded SQL + `findings/` audit trail for every major claim.
- Branch safety CI born from five stale PRs in a row.

---

## 7. Bottom Line

This is a well-documented, offline-first analytical corpus with strong provenance discipline at the schema and page level, but testing remains operational (integrity checker + static CI) rather than unit/integration-test driven. The main risks are replica staleness (caught locally, not in CI), unvalidated inference layers (footnote classifier, ringer identity), and analysis pages whose time windows lag the underlying corpus.
