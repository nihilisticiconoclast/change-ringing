# Roadmap: Gemini CLI

A queue rather than a single task. **One pull request per task**, in order,
stopping at the end of each for review. Later tasks are sketched rather than
specified, because what they should ask depends on what the earlier ones find.

| # | Task | State |
| --- | --- | --- |
| 1 | Method extension lineage from place notation | **Done** — PR #3, merged |
| 2 | A canonical dedication and place-name lexicon | **Done** — PR #4, merged |
| 3 | Ringer identity resolution | **Done** — candidate dataset delivered |
| 4 | Footnote occasion classification | **Done** — candidate dataset delivered |

---

## Standing constraints — read before every task

> **WORK OFFLINE. THE LIVE DATABASE IS FROZEN UNTIL 2026-09-01.** Build a
> replica with `python scripts/build_local_db.py --out local_corpus.db`, or
> query the committed snapshot at `data/change-ringing.db` directly. The
> scripts refuse a remote connection without
> `CHANGE_RINGING_ALLOW_PRODUCTION=1`; do not set it.

**Do not write to the database.** Every task here produces a candidate file
for review. Claude Code adjudicates and merges — see `docs/AGENTS.md`.

**Check whether the source already answers it.** Three times now this project
has assigned inference work that turned out to be unnecessary: BellBoard
publishes `dove-tower-id`, the Methods Library states `<classification>`, and
`methods.name` already groups a naming family. Before starting, confirm the
gap is real, and say so in the PR.

**Two lessons from the location-resolution run.** It produced good data and a
write-up that could not be trusted at face value.

1. **Verify every identifier you cite in prose.** That write-up gave
   "Claremont, TowerID 1563" (does not exist) and "Lismore, TowerID 10769"
   (actually Burnham on Crouch, Essex). The CSV rows were right; the narrative
   was invented. Query for every ID and title you put in prose.
2. **Use the whole confidence scale.** That run emitted no `low` band at all,
   and two `high` rows were wrong. `high` means you would be surprised to be
   wrong. Adjudication samples rather than checking every line, so an
   over-confident row does more damage than an honestly uncertain one.

**Query cost.** Rows read are metered and a task sweeping 25,055 methods
against each other is exactly the expensive shape. `EXPLAIN QUERY PLAN`
anything touching a whole table. Also note `dove.TowerID` is not unique — 13
towers hold two rings — so joining on it alone inflates counts.

---

## Task 1 — Method extension lineage from place notation *(done)*

Work out which methods are genuine extensions of a lower-stage member, and
which merely share a name.

The framing has been checked, so you can trust it:

- **Grouping by name is trivial and is not the task.** `methods.name` is a
  column (19,447 distinct values across 25,055 methods) and `title` is
  mechanically `name` + `classification` + stage word. `GROUP BY name` already
  gives the naming family.
- **Structural lineage is genuinely open.** `extension_construction` is
  populated for only **1,851 of 25,055** methods (7.4%); `notation` is
  populated for **all 25,055**. Complete evidence, almost no derived answer.

Useful columns: `method_id`, `title`, `name`, `stage`, `classification`,
`notation`, `symmetry`, `lead_head`, `lead_head_code`, `fch_groups`,
`length_of_lead`, `number_of_hunts`, `huntbell_path`, `extension_construction`.

Cambridge Surprise, as the signal you are reading:

```
Minor    -36-14-12-36-14-56,12
Major    -38-14-1258-36-14-58-16-78,12
Royal    -30-14-1250-36-1470-58-16-70-18-90,12
```

**Calibrate against the labelled subset.** The 1,851 methods carrying
`extension_construction` are ground truth. Hold them out, run blind, and
**report the score before applying the method to the remainder**. This is the
most important line in the brief: it is the difference between a result
someone can rely on and one they must re-derive. A poor score honestly
reported is a real contribution.

**Deliverable:** `data/method_extension_candidates.csv` — one row per proposed
parent→child relationship, with `child_method_id`, `child_title`,
`child_stage`, `parent_method_id`, `parent_title`, `parent_stage`,
`family_name`, `relationship` (`extension` / `variant` / `name_only`),
`confidence` (`high` / `medium` / `low`), `evidence`. Plus
`docs/method_extension_lineage.md` with the method, the held-out score stated
plainly, the structural patterns found, and what you could not resolve.

---

## Task 2 — A canonical dedication and place-name lexicon *(done)*

Every name-matching problem in this project keeps re-solving the same
vocabulary from scratch. Dove abbreviates dedications hard — `S Paul`,
`SS Peter & Paul`, `S Mary V`, `H Trinity`, `All SS`, `S John Bapt`,
`Cath & Abbey Ch of S Alban` — and other sources write them out. Spelling
varies genuinely (Laurence/Lawrence, Katherine/Catherine, Swithun/Swithin,
and Cornish saints like Wennapa/Weneppa). Place names vary too
(Barrow-on-Soar / Barrow upon Soar, South Mymms / South Mimms).

The deliverable is a reusable mapping — `data/name_lexicon.csv` — derived from
the whole of `dove` and `towers` at once, which is exactly the sweep a large
context is for. It should distinguish an abbreviation expansion from a genuine
spelling variant from a distinct dedication, because conflating those is how
`St Mary, Whitechapel` got matched to Whitechapel S Paul.

Full brief when Task 1 lands, informed by what it finds.

## Task 3 — Ringer identity resolution *(done)*

Matching ringers across performances — the same person appearing as
"J A Boulton", "James Boulton", "James A Boulton". The natural large-context
task, and the basis for any lineage tool.

Candidate dataset delivered at `data/ringer_identity_candidates.csv` and
documented in `docs/ringer_identity_resolution.md`. Full multi-decade extension
waits for the complete BellBoard backfill.

---

## Task 4 — Footnote occasion classification *(done)*

113,895 free-text footnotes record *why* a performance happened. Nothing in the
corpus captures occasion, and no published dataset does either — this is a real
gap, checked before being assigned.

Measured keyword counts, as a floor rather than a target: birthday 7,877,
"memory" 7,345, funeral 3,975, wedding 2,254, "first peal" 2,221. Keyword
matching alone will miss most of it and misread plenty ("in memory of the
bells", "first peal as conductor"), which is why this needs reading rather than
grepping.

**Deliverable:** `data/footnote_occasions.csv` — one row per footnote, with
`perf_id`, `position`, `occasion` (a small closed vocabulary you propose and
justify — memorial, birthday, wedding, funeral, anniversary, first-performance,
civic, seasonal, practice, none), `subject_type` (person / building / bells /
institution / none), `confidence`, `evidence`. Plus a write-up.

**Build your own oracle first, before classifying anything.** There is no
labelled set, so make one: hand-label a random 300 footnotes, hold them out,
run blind, and report precision and recall per occasion class. State the score
before the full run. If a class scores badly, say so rather than quietly
dropping it.

**Two constraints specific to this task.**

1. **These are real people, many recently dead.** 7,345 footnotes are
   memorials. Produce aggregate classifications; do **not** produce a
   searchable index of named individuals, and do not put a named person's
   memorial into a write-up as an illustration. Aggregate patterns are the
   deliverable.
2. **`subject_type` matters more than it looks.** "In memory of" a person and
   "in memory of the old bells" are different things, and conflating them would
   make any downstream count of memorial ringing wrong.

Out of scope: visualising it, and touching any file under `schema/` or
`scripts/`.
