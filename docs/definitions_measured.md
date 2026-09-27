# The contentious definitions, measured

**Roadmap item [R-52](ROADMAP.md).** Produced by
`scripts/measure_definitions.py`; design in `semantic_layer_design.md`.

**This document does not choose anything.** It reports how many records each
choice moves, so that [R-53](ROADMAP.md) picks with the cost in front of it and
every published figure can be checked against the convention it actually used.

Choosing first and measuring afterwards is how the current flat threshold got
there, and it is how PR #19 came to publish "72.5% conduct a peal" when the code
measured conducting *anything* — the real figure being 19.8%, with a median wait
of 37 performances rather than 11. A definition error, not a code error, and
invisible to every check in the repository.

## Summary: the size of each choice

Ordered by how much it moves, which is **not** the order anybody would have
guessed. The first draft of the design document led on the stage rule, which
turns out to be the smallest thing here by three orders of magnitude.

| # | Choice | Records it moves | Live or latent? |
| --- | --- | ---: | --- |
| 4 | Spliced method double-count | **150,701** (+66.0%) | **Live** |
| 6 | `bb_timestamp` is not a submission date | **57,295** (19.5%) | Latent |
| 5 | Handbells in a tower count | **30,054** (10.2%) | **Live** |
| 2 | Unknown `changes` | **21,788** (7.4%) | **Live** — 1.43 points on peal share |
| 8 | "Active ringer" threshold | 6,902 → 18,764 | **Live** |
| 1 | Peal boundary `>` vs `>=` | **848** (1.62% of peals) | **Live** |
| 7 | Ringer counted per row or per performance | 3,414 | **Live** |
| 3 | Stage-dependent peal minimum | **4** | Latent |

## 1. The peal boundary — 848 performances

```
changes >= 5000 :   52,499 peals
changes >  5000 :   51,651 peals
exactly 5000    :      848   = 1.62% of the peal population
```

Five call sites use `>=`: `most_rung_methods.sql`,
`peal_and_quarter_populations.sql`, `rhythm/01_daily_profile.sql`,
`analyse_ringing_careers.py`. One uses `>`:
`queries/findings/conductor_speed_signature.sql` — and that is the query behind
R-24's published finding that between-conductor variation is half
within-conductor variation. **That result sits on a denominator 1.6% smaller
than every other published figure on the site.**

## 2. Unknown length — 21,788 performances, and 1.43 points

**21,788 performances (7.4%) carry no `changes` value.** Three conventions are
in use and they are not equivalent:

| Call site | Predicate | Effect on the 21,788 |
| --- | --- | --- |
| `practice_night_agreement.sql` | `changes IS NULL OR changes < 5000` | counted as not-a-peal, deliberately and explicitly |
| `most_rung_methods.sql`, `rhythm/01_daily_profile.sql` | `SUM(changes >= 5000)` | **silently dropped from the numerator** — SQLite skips NULL in `SUM` — while a `COUNT(*)` denominator keeps them |
| `analyse_ringing_careers.py` | `changes not in (None, "")` else `False` | counted as not-a-peal |

The middle one is the hazard, because nothing about it looks wrong:

```
peal share, denominator = all performances   : 17.89%
peal share, denominator = known length only  : 19.32%
                                               -----
the choice moves the headline peal share by    1.43 points
```

This is why `semantics.py` must return `None` for unknown length rather than
`False`. A boolean silently calls 21,788 performances quarters.

## 3. The stage-dependent minimum — 4 performances

The CCCBR framework sets the peal minimum by stage: 5000 changes on seven or
more bells, but **5040 on five or six**, a peal at those stages being a whole
number of extents. 7,001 performances fall in [5000, 5040), so this looked like
the largest problem in the set.

It is the smallest. Of the 6,166 with a resolved stage:

```
stage  8: 3,518    stage 10:   892    stage 12:   191
stage  9:   777    stage 11:   773    stage  6:     4   <- the only ones affected
```

**Four performances, all at Minor, none at Doubles.** Encode the rule anyway —
it is the actual rule and costs one line — but it is not an argument for this
work, and the first draft of the design document presented the 7,001 as though
it were. Corrected there.

## 4. The spliced double-count — 150,701 rows, and the largest by far

```
method links        : 379,180
performances linked : 228,479
linked to >1 method :  25,134  (11.0% of linked performances)
inflation if you COUNT(*) after joining: 150,701 extra rows, +66.0%
```

Eleven per cent of linked performances carry more than one method, but they
carry about six extra each — spliced peals, where one performance is eight or
more methods. So **"performances of method X" summed across all methods exceeds
the number of performances by 66%.**

Whether a spliced performance counts once per method or once in total is a
definition, and it is currently implicit at every call site. The most-linked
methods, with spliced appearances included:

| Method | Links |
| --- | ---: |
| Plain Bob Doubles | 25,203 |
| Grandsire Doubles | 18,273 |
| Plain Bob Minor | 18,187 |

## 5. What counts as a performance at all — 30,054 handbell performances

| | Count | Share |
| --- | ---: | ---: |
| `ring_type = 'tower'` | 263,417 | 89.8% |
| `ring_type = 'hand'` | 30,054 | 10.2% |
| `portable` set | 1,318 | 0.4% |
| `dumb_bells` set | 72 | 0.0% |

**A tower-level count that does not exclude handbells is 10.2% too high**, and
nothing in the repository records whether any given published tower figure
excluded them.

## 6. Which date — and `bb_timestamp` is not what its name says

This started as "`perf_date` or `bb_timestamp`?" and became a data-quality
finding.

```
rung year <> bb_timestamp year : 77,243 (26.3%)
bb_timestamp over a year later : 69,856 (23.8%)
```

Far too much for submission lag. The daily counts say why:

| `bb_timestamp` date | Performances |
| --- | ---: |
| 2017-01-06 | 11,532 |
| 2017-01-07 | 11,213 |
| 2017-01-08 | 10,993 |
| 2017-01-09 | 9,462 |
| 2017-01-05 | 7,355 |
| 2015-02-15 | 4,420 |

**57,295 rows (19.5%) sit on a date carrying more than 2,000 performances.** A
real submission day carries a few hundred.

Those dates are **not our ingest runs** — ours were 2026-08-09 and 2026-08-15,
recorded correctly in `ingested_at` (96,067 and 197,404 rows). Early January
2017 and mid-February 2015 are **BellBoard's own historical bulk imports.**

So `bb_timestamp` is BellBoard's record-creation time, not the band's submission
time. Anyone treating it as a submission date is wrong for about a fifth of the
corpus, and anyone ordering by it for recency gets those two spikes instead.
`perf_date` is the only date that means what it says; `ingested_at` is the only
honest provenance column.

**Currently latent, not live:** no published query reads `bb_timestamp`. But
`schema/002` builds `idx_perf_timestamp` on it — **11.1 MB of index on a column
no query touches**, which is worth dropping on the same pass.

## 7. How a ringer's tally is attributed

```
ringer rows                           : 1,969,949
distinct performances covered         :   292,138
(performance, name) pairs with >1 row :     3,414
rows flagged conductor                :   276,150
```

Three separate choices:

- **Per row or per performance?** 3,414 (performance, name) pairs have more than
  one row — one person on two bells, mostly handbells. "Appearances" counted per
  row is that much higher.
- **Is the conductor a ringer too?** 276,150 rows carry the flag, and every call
  site decides independently.
- **1,333 performances have no ringers at all** (292,138 covered of 293,471).

And the caveat that outlives all three: a "ringer" here is a **resolved
cluster, not a person.** 70,032 raw names resolve to 56,340 canonical entities,
and **that resolution's accuracy is unmeasured** — the open half of R-9. Every
per-ringer figure inherits it, and `semantics.py` should carry that statement
next to the definition rather than let it be forgotten.

## 8. What makes a ringer "active"

`analyse_ringing_careers.py` uses `MIN_APPEARANCES = 50` and
`MIN_SPAN_YEARS = 5`. Defensible, arbitrary, and buried in one script's
constants.

| Minimum appearances | Ringers qualifying |
| ---: | ---: |
| 10 | 18,764 |
| 25 | 10,835 |
| **50** | **6,902** ← the published choice |
| 100 | 4,194 |
| 200 | 2,200 |

The cohort roughly halves with each doubling, so the threshold is load-bearing
rather than incidental. These are raw names rather than resolved clusters, so
they are upper bounds on the number of people; the shape is the point.

## What R-53 has to decide

One recommendation per choice, with the reason, for R-53 to accept or overrule:

| Choice | Recommendation | Why |
| --- | --- | --- |
| Peal boundary | `>= 5000` | Five call sites already; `>` is the outlier, and 5000 changes is a peal |
| Unknown length | `is_peal` returns `None` | 21,788 rows cannot be classified; a boolean lies about them |
| Stage minimum | Encode 5040 for stages 5–6 | It is the real rule, costs one line, moves 4 rows |
| Spliced methods | Two named measures, not one | `performances_of_method` (distinct perf_id) and `method_appearances` (links). Ambiguity is the bug; either count is fine if named |
| Handbells | Tower measures exclude them by default | Excluding is the conservative reading of "tower" |
| Date | `perf_date` for everything; `bb_timestamp` documented as unreliable and its index dropped | It is not a submission date |
| Ringer tally | Per performance, conductor included, both stated | Per-row double-counts handbell ringers |
| Active ringer | Keep 50/5, but as a named, cited constant | Changing it now would move a published figure for no reason; naming it makes the sensitivity visible |

## Reproducing

```
python scripts/measure_definitions.py --local-db data/change-ringing.db
```

Every figure above is printed by that command.
