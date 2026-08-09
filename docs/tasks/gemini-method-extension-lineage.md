# Task brief: method extension lineage from place notation (Gemini CLI)

A large-context structural task: work out which methods are extensions of
which, across stages, from their place notation. Unusually for this project,
there is a labelled subset to calibrate against, so the output can be scored
rather than merely asserted.

Verified against the live database as of 2026-08-09.

Paste from the horizontal rule onward.

---

> **WORK OFFLINE. THE LIVE DATABASE IS FROZEN (2026-08-09).** Turso breached
> its daily row-read limit, so production is off limits: no loads, no
> exploratory queries, no verification runs. The scripts enforce this -- they
> refuse to open a remote connection unless `CHANGE_RINGING_ALLOW_PRODUCTION=1`
> is set, and you should not set it.
>
> You lose nothing. Build a full local replica in about 90 seconds:
>
> ```
> pip install -r requirements.txt
> python scripts/build_local_db.py --out local_corpus.db
> ```
>
> That reconstructs the corpus from public sources and files committed here --
> Dove's 7,262 towers and 63,894 bells, all 25,055 methods and 30,734
> first-performance events, and the 22,111 adjudicated tower links. Every
> script takes `--local-db local_corpus.db`. BellBoard is left empty unless you
> pass `--bellboard-since YYYY-MM-DD`, because it is the one source that
> throttles.
>
> The replica uses an embedded libSQL connection, not stdlib `sqlite3`, and
> that difference matters: `sqlite3` accepts SQL that libSQL rejects, which is
> how a double-quoted string literal reached production earlier today. Testing
> against this replica is a real check. `EXPLAIN QUERY PLAN` works on it too,
> so read cost can be assessed offline before anything runs for real.
>
> Verify against the replica and say so in the PR. Do not run against
> production.

You are working on `nihilisticiconoclast/change-ringing`. Read `README.md`,
`docs/AGENTS.md` and `docs/CONNECTING.md` first. The `methods` table is loaded
in Turso with 25,055 rows.

## Why this task exists, and why it is yours

Twice now this project has assigned inference work that the source already
answered. BellBoard publishes `dove-tower-id`, so linking performances to
towers is an integer join. The Methods Library states `<classification>` on
every method set, so classifying into Surprise/Delight/Bob needs no model at
all. Both were removed from the plan once checked.

The same check has been run here, so you can trust the framing:

- **Grouping by name is trivial and is not your task.** `methods.name` is a
  first-class column (19,447 distinct values across 25,055 methods), and
  `title` is mechanically `name` + `classification` + stage word -- "Cambridge"
  yields "Cambridge Surprise Minor", "Cambridge Surprise Major" and so on. A
  `GROUP BY name` already gives the naming family. Do not rediscover this.
- **Structural lineage is genuinely open.** `extension_construction` -- which
  encodes how a method extends to a higher stage -- is populated for only
  **1,851 of 25,055** methods (7.4%). `notation` is populated for **all
  25,055**. So the raw structural evidence is complete and the derived
  relationship is almost entirely missing. That gap is the task.

## The task

For each naming family that spans multiple stages, determine from place
notation which methods are genuine extensions of a lower-stage member, and
which merely share a name. "Grandsire" appears at 13 distinct stages, "Kent"
at 11 across 18 methods; some of those are true extensions and some are
independent constructions that reuse a name.

Useful columns on `methods`: `method_id`, `title`, `name`, `stage`,
`classification`, `notation`, `symmetry`, `lead_head`, `lead_head_code`,
`fch_groups`, `length_of_lead`, `number_of_hunts`, `huntbell_path`,
`extension_construction`. Connect as `docs/CONNECTING.md` describes.

Worked example of the signal you are reading -- Cambridge Surprise:

```
Minor    -36-14-12-36-14-56,12
Major    -38-14-1258-36-14-58-16-78,12
Royal    -30-14-1250-36-1470-58-16-70-18-90,12
```

## Calibrate against the labelled subset

The 1,851 methods carrying `extension_construction` (values like `EP1-1`,
`EP1-3`) are your ground truth. **Hold them out, run your method blind, and
report how it scored against them** before applying it to the unlabelled
remainder. This is the part of the brief that matters most: it is the
difference between a result someone can rely on and one they have to re-derive.

If your approach scores poorly on the labelled subset, report that. A negative
result honestly measured is a real contribution here and saves the next person
the attempt.

## Deliverable

`data/method_extension_candidates.csv`, one row per proposed
parent-child (lower stage -> higher stage) relationship:

| column | meaning |
| --- | --- |
| `child_method_id`, `child_title`, `child_stage` | the higher-stage method |
| `parent_method_id`, `parent_title`, `parent_stage` | the proposed source |
| `family_name` | the shared `name` value |
| `relationship` | `extension`, `variant`, or `name_only` |
| `confidence` | `high`, `medium`, or `low` |
| `evidence` | one line: what in the notation supports this |

Plus `docs/method_extension_lineage.md`: your method, the score against the
labelled subset stated plainly, the structural patterns you found, and the
cases you could not resolve.

## Two specific warnings from the last run

The previous location-resolution task produced good data and a write-up that
could not be trusted at face value. Both lessons apply directly.

1. **Verify every identifier you cite in prose.** That write-up gave
   "Claremont, TowerID 1563" (does not exist) and "Lismore, TowerID 10769"
   (actually Burnham on Crouch, Essex). The CSV rows were correct -- the errors
   were confined to the narrative, which made the document read as
   authoritative when parts of it were invented. Query the database for every
   ID and title you put in prose, and do not write an example from memory.
2. **Calibrate confidence honestly, and use the whole scale.** That run emitted
   no `low` band at all, collapsing a four-point scale to three, and two rows
   marked `high` were wrong -- one matched Cheltenham Minster to a different
   parish when an exact match existed. `high` should mean you would be
   surprised to be wrong. Here you can check that claim against the labelled
   subset, so there is no excuse for guessing at it.

## Query cost

This database is metered on rows read, and a task that sweeps 25,055 methods
against each other is exactly the shape that gets expensive.

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

## Boundaries

- **Do not write to the database.** No inserts, updates or schema changes.
  This task produces a candidate file for review.
- **Do not modify anything under `schema/` or `scripts/`**, and do not touch
  `data/method_location_candidates.csv`.
- **Do not take on the Mistral Vibe task in `docs/tasks/`.** The last PR did
  both agents' work in one branch, which defeated the split. Stay in this brief.
- Work on a branch and open a pull request. Claude Code adjudicates and merges.

## Definition of done

The candidate CSV and the write-up, in a PR whose description states the score
against the labelled subset, the confidence distribution, and the families you
think need a human eye.
