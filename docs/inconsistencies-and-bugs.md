# Inconsistencies and Bugs

## 1. Gaps and Inconsistencies in Documentation

### Stale or contradictory content

1. **`README.md` BellBoard section (lines 345–347)** still says *"The corpus currently holds only a small recent window"* — contradicts the Status section above it (293,471 performances, 2012–2024 complete).

2. **`docs\tasks\gemini-roadmap.md` header table** says Task 6 backfill is *"Next: 2017 backwards to 2012"* — backfill is finished per `ROADMAP.md`, `SOURCES.md`, and `README` Status.

3. **Same file, Task 3 section** still marked *"blocked"* on thin data, but the summary table says **Done** and `ROADMAP.md` item 9 says ringer identity is **unblocked**.

4. **Same file, Task 1 section** still titled *"active"* though the table marks it Done.

5. **`README.md` Status checkboxes** still open for CompLib linkage and ringer identity resolution, while roadmaps mark related work done (ingestion merged; identity candidates delivered).

6. **`scripts/build_local_db.py` docstring** says BellBoard replica is *"a single window rather than the full history"* — committed CSVs now cover 2012–2024.

7. **Rhythm page window:** README says page is restricted to 2021–24 while also noting corpus runs 2018–24; widening is Claude's explicit next task.

### Missing or ambiguous references

8. **`docs\tasks\gemini-location-resolution.md`** referenced in three places but **file absent** — location work is done (`method_location_adjudication.csv`), so the brief may have been removed without updating references.

9. **`data/change-ringing.db`** is **gitignored** (removed after hitting size limits) but `queries\README.md`, both agent roadmaps, and `rebuild_all.py` still describe it as a *"committed snapshot"* you can query directly — you must build it locally instead.

10. **Generated datasets** (`data/footnote_occasions.csv`, `data/ringer_identity_candidates.csv`) are produced by `rebuild_all.py` but not present in the committed `data/` tree — docs refer to them as if they exist after a rebuild.

### Minor count / wording drift

11. Footnote counts oscillate between **113,895** (four-year window / occasions page) and **337,946** (full corpus) across docs — intentional but easy to misread.

12. **`mistral-vibe-roadmap.md` Task 4** still listed *"unblocked"* though schema/007 and decision 001 are merged.

13. **Untracked working files** in git status (`data/complib/page_*.json`, scratch scripts) suggest an in-progress partial CompLib fetch not yet integrated.

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

## 5. Bottom Line

This is a well-documented, verification-first data corpus project with a clear three-agent split, a frozen production database, and a mature offline rebuild pipeline. The **BellBoard backfill is complete in committed CSVs**; the main open work is **measuring classifier accuracy**, **loading CompLib in full**, **widening the Rhythm analysis**, and **consolidating data-quality caveats** before reloading Turso after September 2026. The biggest doc hygiene issue is **stale README and gemini-roadmap header content** that still describes an incomplete backfill and blocked tasks that have landed.
