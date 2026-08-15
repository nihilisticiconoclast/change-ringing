# Roadmap: Gemini CLI

A queue rather than a single task. **One pull request per task**, in order,
stopping at the end of each for review. Later tasks are sketched rather than
specified, because what they should ask depends on what the earlier ones find.

| # | Task | State |
| --- | --- | --- |
| 1 | Method extension lineage from place notation | **Done** — PR #3, merged |
| 2 | A canonical dedication and place-name lexicon | **Done** — PR #4, merged |
| 3 | Ringer identity resolution | **Done** — candidate dataset delivered |
| 4 | Footnote occasion classification | **Partly done** — a page shipped, the dataset was never built. See below |
| 5 | Measure the occasion classifier | **Active** — the missing half of Task 4, brief below |

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

## Task 1 — Method extension lineage from place notation *(active)*

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

## Task 2 — A canonical dedication and place-name lexicon *(queued)*

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

## Task 3 — Ringer identity resolution *(blocked)*

Matching ringers across performances — the same person appearing as
"J A Boulton", "James Boulton", "James A Boulton". The natural large-context
task, and the basis for any lineage tool.

Blocked deliberately: `performance_ringers` holds ~10,000 rows from a single
recent window, which is far too thin for the pairwise sweep to beat a simple
`GROUP BY name`. It needs the BellBoard historical backfill to have actually
been run. Do not start it until this row says otherwise.

---

## Task 4 — Footnote occasion classification *(partly done)*

> **Reviewed 2026-08-15.** `docs/occasions.html` shipped and it is a good page —
> the violin plot of length-by-occasion is a genuinely nice idea, its eight
> category counts recompute exactly, and the privacy constraint was respected:
> only aggregate arrays are embedded, no footnote text and no names. I corrected
> its prose (it said "hundreds of thousands of footnotes" for 113,894, and
> labelled footnote counts as performances) and added a limitations panel.
>
> **But the deliverable was not built, and the two things the brief put out of
> scope are the two things that were.** Checked against the git history rather
> than from impression:
>
> | Asked for | Delivered |
> | --- | --- |
> | `data/footnote_occasions.csv`, one row per footnote | **Never created** — no commit on any branch adds it |
> | A hand-labelled 300-footnote oracle, scored before the full run | **Not built**, no precision or recall reported |
> | `subject_type` — person vs building vs bells | **Absent**, so "in memory of" a person and "in memory of the old bells" are still conflated |
> | `confidence` and `evidence` per row | Absent |
> | *Out of scope: visualising it* | A visualisation |
> | *Out of scope: touching `scripts/`* | `scripts/build_occasions_page.py` |
>
> This is worth stating plainly because it is an easy failure to repeat and it
> was not caught for a day: **a good-looking page passes review in a way a
> missing CSV does not.** Given an unglamorous measurable deliverable and an
> implicit opportunity to build something visual, the visual thing got built, and
> it was attractive enough that nobody asked where the dataset was. That is a
> lesson about the brief as much as about the run — see `docs/LESSONS.md`.
>
> The page stays. Task 5 below is the half that is missing, and it is now the
> only thing asked for.

### Original Task 4 brief, retained

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

---

## Task 5 — Measure the occasion classifier *(active)*

**One deliverable, and it is a number, not a page.**

`docs/occasions.html` currently asserts that 113,894 footnotes divide into eight
occasions. Nobody knows whether that is true, and the page says so in its own
footer:

> *"A keyword is not an intent. 'First' catches a ringer's personal milestone and
> the word 'first' in any other sentence alike; no sample has been hand-checked to
> estimate that error rate, and until one has, treat the ordering of the smaller
> categories as unproven."*

Your job is to remove that sentence by making it false.

### The deliverable

**`data/footnote_occasion_labels.csv`** — a hand-labelled random sample, and the
measurement it supports.

1. **Sample 400 footnotes at random from all 113,894**, with a fixed, stated seed
   so the sample is reproducible. Not a convenience sample, not the interesting
   ones, not a stratified sample weighted toward the categories you expect — a
   plain random draw. If you want a stratified supplement for the rare classes,
   add it as a clearly separate second sample and score it separately.
2. **Label each one by reading it**, before looking at what the classifier said.
   Columns: `perf_id`, `position`, `label` (one of the eight categories, or
   `none`, or `multiple` with the categories listed), `subject_type`
   (person / building / bells / institution / none), `notes`.
3. **Then** run the classifier over the same 400 and compute, per category:
   **precision, recall, F1, and support**. Report the confusion pairs — which
   categories get mistaken for which — because that is the actionable part.

### What the answer is likely to be, so you can tell if you have got it wrong

Two categories are worth predicting in advance, and writing your prediction down
before you measure:

- **Firsts / Milestones** is the largest category at 31,833 and is built on
  `\b(first|1st|circled|milestone)\b`. If that keyword is catching "the first
  time we have rung since the pandemic" and "first quarter as conductor" and
  "rung first at the Abbey" alike, its precision will be poor and its rank
  meaningless. This is the single most consequential number in the task.
- **Church Service / Festival** is inflated by a known 988 footnotes reading
  "thanksgiving for the life of", which the Memorial pattern also claims. That
  is measured already; your sample should reproduce it or explain why not.

If your measured precision comes out above 0.95 for every category, **be
suspicious of your own labelling** rather than pleased. Keyword classifiers on
free text do not usually score that well, and the most likely explanation is that
you labelled with the classifier's output visible.

### The write-up

`docs/footnote_occasion_accuracy.md`. It must say, in this order: the sample
method and seed; your predictions, written before measuring; the per-category
table; the confusion pairs; and **which categories you would now stop reporting**.

That last one is the point of the whole task. A category with precision below
about 0.7 should not be on a published page as a count, and saying so is a
success, not a failure. The Blue Line Atlas excludes 662 methods it cannot verify
and is better for it.

### Constraints

- **The privacy rule is unchanged and applies to your sample.** The labelled CSV
  may contain footnote text, because it is a working file that a human needs to
  check. But **no named individual may appear in the write-up**, no memorial may
  be quoted as an illustration, and the sample must not be published as a
  browsable index. 7,345 of these footnotes are memorials written by people who
  did not anticipate republication.
- **Out of scope, and this time it means it:** do not modify
  `docs/occasions.html`, `scripts/build_occasions_page.py`, or anything under
  `schema/`. If the measurement says the page should change, say so in the
  write-up and stop — the change is a separate task, and deciding it is not
  yours.
- Offline. The corpus is at `data/change-ringing.db`; the freeze on the live
  database holds until 2026-09-01.

### Definition of done

A pull request containing exactly two new files —
`data/footnote_occasion_labels.csv` and `docs/footnote_occasion_accuracy.md` —
and no modifications to anything else. The PR description states the precision
and recall of the largest category in its first paragraph.

If the honest answer is "the classifier is fine", that is a good outcome and a
short PR. If the honest answer is "Firsts / Milestones is 40% precise and should
come off the page", that is a better one.
