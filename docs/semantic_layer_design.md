# A semantic layer for the corpus, and an MCP server over it

**Roadmap items [R-52](ROADMAP.md) through [R-56](ROADMAP.md).** Design first,
because the ordering matters and the cheap version of this is worse than nothing.

## Why now

Not tidiness. Two things converged.

**The definitions have already diverged, measurably.** There is no shared
definition of a peal anywhere in this repository. `is_peal` exists as a local
variable inside one function of `analyse_ringing_careers.py`, and **36 scripts
query the database directly**, each carrying its own literal thresholds.
Fourteen places hardcode `5000`. They do not agree:

| Call site | Predicate |
| --- | --- |
| `queries/findings/conductor_speed_signature.sql:65` | `p.changes > 5000` |
| `queries/findings/most_rung_methods.sql:15` | `SUM(changes >= 5000)` |
| `queries/findings/peal_and_quarter_populations.sql:78` | `WHEN p.changes >= 5000` |
| `queries/rhythm/01_daily_profile.sql:18` | `SUM(p.changes >= 5000)` |
| `scripts/analyse_ringing_careers.py:104` | `int(changes) >= 5000` |
| `queries/findings/practice_night_agreement.sql:147` | `p.changes IS NULL OR p.changes < 5000` |

**848 performances have exactly 5000 changes.** They are peals in five of those
places and not peals in the sixth — and the sixth is the query behind R-24's
published claim that between-conductor variation is half within-conductor
variation. **21,788 performances (7.4%) carry no `changes` value at all**, and
the call sites disagree about whether those are excluded, counted as
not-a-peal, or silently dropped from a numerator while remaining in a
denominator.

**An MCP server makes this urgent rather than annoying.** A server that hands an
LLM a SQL prompt hands it the job of defining "peal", and it will invent a
threshold confidently, in prose indistinguishable from the reviewed figures.
Every failure this project has caught in review is that shape: PR #21's oracle
bootstrapped from its own classifier, PR #28's composer column invented beside
an exact one, PR #33's conductor-memory column derived from the wrong mean. The
fix is not to review harder. It is to make the definition unavailable to
invention.

This has already cost a published figure once. PR #19 reported "72.5% conduct a
peal"; the code measured conducting *anything*. The real figure is 19.8%, with a
median wait of 37 performances rather than 11. A definition error, not a code
error.

## What is already in place

The prerequisites are done, which is why this is worth doing now rather than
after more ingestion.

| Layer | State |
| --- | --- |
| Fact grain | `performances`, one row per performance on `perf_id`, 293,471 rows |
| Source completeness | 13 years committed as CSV, each verified against `search.php` as an independent oracle |
| Tower / ring dimension | `decision 001` adopted; `v_towers_unique`, `v_dove_towers`, `v_ringing_towers`; the join identity asserted by `verify_corpus.py` on every run |
| Method dimension | `performance_methods`, 379,176 links on 228,478 performances (77.9%), with confidence and match-kind recorded |
| Ringer dimension | 70,032 raw names → 56,340 canonical clusters. **Accuracy unmeasured** — the open half of R-9 |
| Composer dimension | 57,249 performances bridged to CompLib at 99.80% precision (R-36) |
| Date dimension | `performances.perf_date` only. No date dimension, and two candidate date columns |

So the model's *physical* pieces exist. What does not exist is a **declared**
model with the contentious definitions written down in one place.

## The definitions that are actually contentious

This is the substance. Each of these is a real choice that changes published
numbers, and each is currently made independently at every call site.

### 1. What counts as a peal

Three separate choices, and **measuring them reordered their importance** — the
first draft of this document had them the other way round.

**The boundary, and it is material.** `>= 5000` yields **52,499 peals**;
`> 5000` yields **51,651**. The difference is the **848 performances of exactly
5000 changes — 1.6% of the peal population**, and the `>` spelling is the one
used by `conductor_speed_signature.sql`, the query behind R-24's published
finding. Any per-peal rate computed from that query is on a denominator 1.6%
smaller than everything else on the site.

**Unknown length, and it is bigger.** **21,788 performances (7.4%) have no
`changes` value.** `practice_night_agreement.sql` deliberately counts them as
not-a-peal; `SUM(changes >= 5000)` drops them from the numerator while a
`COUNT(*)` denominator keeps them. That is a 7.4% swing available to whichever
convention a call site happens to use, and it is the largest single ambiguity in
the corpus.

**The stage rule, which turns out to be almost nothing.** The CCCBR framework
sets the minimum by stage — 5000 changes on seven or more bells, but 5040 on
five or six, because a peal at those stages is a whole number of extents. 7,001
performances fall in [5000, 5040), so this looked like the big one. Measured by
stage, it is not: of the 6,166 with a resolved stage, **4 are at Minor and none
at Doubles.** Nearly all are Major and above, where 5000 is correct.

    stage  8: 3,518    stage 10:   892    stage 12:   191
    stage  9:   777    stage 11:   773    stage  6:     4  <- the only ones affected

So the rule should still be encoded correctly — it costs one line and it is the
actual definition — but it is not an argument for this work, and the first draft
of this document implied it was. The arguments are the 848 and the 21,788.

### 2. How a ringer's tally is attributed

- One per performance they appear in, or one per bell rung? Handbell ringers
  ring two bells; `performance_ringers.bell` records which.
- Is the conductor counted as a ringer as well as a conductor?
- A "ringer" here is a **resolved cluster**, not a person, and the resolution's
  accuracy is unmeasured. Any per-ringer measure inherits that, and the
  semantic layer should say so rather than let it be forgotten.

### 3. Method counts and the spliced double-count

379,176 method links sit on 228,478 performances. Any "performances of method X"
that joins through the link table and then counts rows **double-counts spliced
performances**. Whether a spliced performance counts once for each method or
once in total is a definition, and it is currently implicit.

### 4. Which date

`perf_date` is when it was rung; `bb_timestamp` is when it was submitted. "How
many performances in 2020" has two answers. The practice-night work uses the
weekday of `perf_date`, correctly for its question — but nothing records that
the choice was made.

### 5. Tower or ring

Decided in 001, but the semantic layer should record which grain each measure
uses, so `v_towers_unique` versus `dove` is not a per-query decision.

### 6. What counts as a performance at all

`performances` carries `portable`, `dumb_bells` and `ring_type`. Handbell,
dumbbell and keyboard performances are in the corpus. Whether they belong in a
tower-level count is a choice nobody has written down.

### 7. What makes a ringer "active"

The careers work used `MIN_APPEARANCES = 50` and `MIN_SPAN_YEARS = 5`. Defensible
and arbitrary, and buried in one script's constants.

## The shape, and what it is deliberately not

**Not a framework.** No dbt, no Cube, no metrics server. This is a SQLite file
and thirteen static pages; a framework would be more machinery than corpus.

Three pieces, in dependency order:

**(a) `scripts/semantics.py` — one module, the only place a threshold appears.**

```python
PEAL_MIN_CHANGES        = 5000   # seven or more bells
PEAL_MIN_CHANGES_LOW    = 5040   # five or six bells: whole extents
QUARTER_MIN_CHANGES     = 1250

def is_peal(changes, stage) -> bool | None   # None when changes is unknown
SQL_IS_PEAL = "..."                          # the same rule, as a SQL fragment
```

The Python predicate and the SQL fragment must be generated from one source and
**tested against each other on every row of the corpus**, or they are two
definitions again with extra steps. That test is the deliverable, not the module.

`None` rather than `False` for unknown `changes` is deliberate: 21,788
performances cannot be classified, and a boolean would silently call them
quarters.

**(b) SQL views that carry the derived columns**, so a SQL caller gets the
definition without importing anything: `is_peal`, `is_quarter`,
`length_class`, and conformed dimension keys.

**(c) `scripts/verify_semantics.py` — the check that keeps it true.**

This is the piece that makes the layer real, and it has an exact precedent here:
`verify_chrome.py` fails any page that declares its own nav CSS, which is why
there is one nav and not fourteen. `verify_semantics.py` fails any script or
recorded query that hardcodes a peal or quarter threshold outside
`semantics.py`. Negative-tested, as everything here is.

**Without (c), this is worse than nothing** — a definitions module that half the
callers ignore is a second source of truth, and two sources are worse than
fourteen scattered ones because one of them looks authoritative.

## The MCP server, built the right way round

The wrong design is a `run_sql` tool. That is a definition-invention engine.

**Tools are measures, not SQL.** `count_performances(...)`,
`top_methods(...)`, `tower_profile(...)`, `ringer_career(...)` — each one a
function whose definitions come from `semantics.py`, and each returning the
definitions it used alongside the numbers, so a model quoting a figure quotes
its basis with it.

**The recorded findings become tools directly.** `queries/findings/*.sql` have
all been through review. Exposing them by name means an LLM asked about
conductor speed or practice nights can only return a figure that was reviewed.
That is this project's central rule — every figure comes from the committed
query — turned into an interface.

**A raw SQL escape hatch is allowed, and gated.** Read-only connection, forced
`LIMIT`, a statement-interrupt budget, and `EXPLAIN QUERY PLAN` refused if it
`SCAN`s a large table. Results labelled as *ad hoc, not a reviewed finding*.

**Two hazards to design for, both specific to this corpus:**

*Untrusted text.* 337,946 footnotes were written by the public. Any tool
returning footnote or title text puts third-party prose into a model's context,
which is a prompt-injection surface. Tool output is data, never instruction, and
footnote-returning tools should say so in their own description.

*Named individuals.* The corpus names real ringers, and the standing decision is
that those names are public record and stay. But an MCP tool is a new
publication route, and `audit_privacy_and_licences.py` currently checks pages
and documents, not tool schemas. The removal/suppression list from R-39 must be
consulted by the server, or the server reinstates anyone who asked to be removed.

## Ordering, and why this order

1. **R-52 — measure the definitions before choosing them.** How many of the
   7,001 in [5000, 5040) are Doubles or Minor; what the 848 boundary cases and
   21,788 unknowns do to each published figure. Choosing first and measuring
   afterwards is how the flat threshold got there.
2. **R-53 — `semantics.py`, the views, and the Python/SQL agreement test.**
3. **R-54 — `verify_semantics.py`, then migrate all 36 call sites.** The check
   lands with the migration, not after it.
4. **R-55 — the MCP server over the finished layer.**
5. **R-56 — re-derive every published figure** and record which ones moved. Some
   will. That is the point, and the ones that move are the argument that this was
   worth doing.

R-56 is not optional bookkeeping. If no published figure changes, the layer
bought consistency and nothing else, and that should be stated plainly too.
