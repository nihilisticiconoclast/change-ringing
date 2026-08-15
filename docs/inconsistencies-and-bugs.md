# Inconsistencies and Bugs

## Gaps and Inconsistencies in Documentation

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

## Bottom Line

This is a well-documented, verification-first data corpus project with a clear three-agent split, a frozen production database, and a mature offline rebuild pipeline. The **BellBoard backfill is complete in committed CSVs**; the main open work is **measuring classifier accuracy**, **loading CompLib in full**, **widening the Rhythm analysis**, and **consolidating data-quality caveats** before reloading Turso after September 2026. The biggest doc hygiene issue is **stale README and gemini-roadmap header content** that still describes an incomplete backfill and blocked tasks that have landed.
