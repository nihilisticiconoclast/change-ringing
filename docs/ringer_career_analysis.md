# Ringer Career Analysis

**Window:** 2012-01-01 to 2024-12-31, thirteen complete years (BellBoard's
near-complete era). Every figure below was measured on a local replica built
with `scripts/build_local_db.py` on 2026-08-15. A figure stated without a window
is one waiting to change size; the 2021-24 figures this project carried before
the backfill are the same quantities over four years, not different ones.

**Built on resolved identities, not raw names.** A career is the trajectory of
one person, so every metric groups on `canonical_ringer_id` from
`data/ringer_identity_candidates.csv` (Gemini Task 3, 55,326 canonical ringers
resolved across 1,969,949 ringer appearances). Joining the alias "Sue Sawyer"
onto the raw `name` column would split one person into two careers and
undercount everyone who uses initials part of the time.

**Deliverables**
- `scripts/ringer_career_analysis.py` — `--local-db`, loads the identity map
  into a TEMP table, joins `performance_ringers` → `performances` → the map.
- `data/ringer_career_trajectories.csv` — one row per resolved ringer: span,
  appearances, conducting, trajectory, archetype.

**Coverage:** 1,966,913 of 1,969,949 ringer appearances (99.85%) resolve to a
canonical identity. The 3,036 unmapped rows are names present in the database
but absent from the candidates CSV (edge cases, NULLs, and names the resolver
deliberately left as separate clusters — bracketed and parenthetical strings
like `[Christopher C P Woodcock]` that may be editorial annotations, which the
resolver correctly refuses to bridge). The figures are of the resolved 99.85%,
which is the honest scope.

---

## 1. Career span — how long is a ringing career?

| Span (years) | Ringers | Share |
| --- | ---: | ---: |
| 1 (single year) | 24,570 | 44.6% |
| 2-3 | 8,567 | 15.6% |
| 4-5 | 3,310 | 6.0% |
| 6-10 | 8,236 | 14.9% |
| 11-13 (the whole window) | 10,409 | 18.9% |

Median span: **2 years**. Nearly half of all ringers recorded in thirteen years
appear in exactly one calendar year. This is the dominant fact about the
population: ringing, as recorded, has a very long tail of one-off
participants and a much smaller core of sustained ringers.

The 18.9% with an 11-13 year span are not all "thirteen-year careers" — the
window opens in 2012, so a ringer first recorded in 2012 and active through
2024 has a genuine 13-year span, but a ringer recorded in 2012 and 2024 only
(with nothing between) also counts. `active_years` (distinct years with a
performance) is the stricter measure and is in the CSV.

## 2. Productivity trajectory — rising, steady, or declining?

| Trajectory | Ringers | Share |
| --- | ---: | ---: |
| brief (≤ 2 active years) | 32,969 | 59.8% |
| declining | 8,884 | 16.1% |
| rising | 8,230 | 14.9% |
| steady | 5,009 | 9.1% |

Classification compares the mean appearances per year in the first third of a
ringer's active years against the last third, with a ±10% band (matching the
project's existing size-signal threshold; a smaller change is within
year-to-year noise for a single ringer). Careers with ≤ 2 active years are
classified `brief` rather than forced into a trend manufactured from noise.

Rising and declining are nearly balanced (14.9% vs 16.1%), which is the
expected signature of a stable population over a fixed window: for every ringer
whose recorded output is tapering off, another is ramping up. The asymmetry is
small and not worth over-reading.

## 3. Conducting as a career stage

IDEAS.md asked: *"Do a few people conduct disproportionately, and is conducting
a career stage?"* Two separate questions, two separate answers.

### Concentration — yes, moderately

- **8,674** of 55,092 ringers (15.7%) ever conducted.
- The **top 10** conductors hold **6.5%** of all 276,020 conducted performances.
- The **top 1%** of conductors (86 people) hold **25.9%**.

Conducting is concentrated, but not to an extreme degree. A quarter of all
conducting sits with under 0.2% of ringers, yet the top 10 individuals hold
only 6.5% between them — the long tail of conductors is real, not a handful of
people doing all of it.

### Is conducting a late-career stage? — no, not clearly

| Measure | Value |
| --- | ---: |
| median years from first-rung to first-conducted | 1 |
| conducted *later* than first appearance | 4,416 (50.9%) |
| conducted in first active year | 4,258 (49.1%) |

The split is almost exactly even. If conducting were a career stage —
something ringers grow into after years of ringing — the "later" share would
dominate and the median gap would be several years. It does not. The median
ringer who conducts at all begins conducting in their first recorded year.

The reason is structural and worth naming: the most prolific conductors
(Christopher C P Woodcock: 3,554 appearances, 2,854 conducted; Adrian C
Malton: 2,763 conducted) were already established when the 2012 window opens,
so their first *recorded* conducting is also 2012. A window that starts later
in a ringer's life cannot measure when they started conducting. The honest
reading is that **on the evidence available, conducting does not present as a
distinct late-career stage**; it begins early for most who do it, and the data
cannot rule out that it began earlier still.

## 4. Career archetypes — the shape of the population

| Archetype | Ringers | Share | Share of all appearances |
| --- | ---: | ---: | ---: |
| one-appearance | 19,987 | 36.3% | 1.0% |
| short-lived (≤ 3 yr span) | 13,150 | 23.9% | 3.8% |
| steady | 16,522 | 30.0% | 12.9% |
| prolific (top decile, ≥ 61) | 2,131 | 3.9% | 14.6% |
| conductor (≥ 100 app, conducted) | 3,302 | 6.0% | 67.7% |

The last row is the headline. **6.0% of ringers — those who conduct and have
at least 100 appearances — account for 67.7% of all ringer appearances.**
Roughly two-thirds of all recorded ringing is done by the 6% who conduct. The
activity is heavily skewed to a small core, the opposite of the long tail of
one-off participants.

`prolific` is the top decile by appearances (≥ 61), defined as a percentile
rather than a round number so the boundary moves with the corpus the way the
figures do. `conductor` overrides `steady`/`prolific` where a ringer both
conducts and is prolific, because the conducting distinction is the more
informative label for that person.

---

## What this is not

- **Not survival.** A "13-year span" does not mean a thirteen-year career; it
  means first and last recorded appearance are thirteen years apart. A ringer
  active in 2012 and 2024 only has a 13-year span and 2 active years. The CSV
  carries both `span_years` and `active_years` so this is not ambiguous.
- **Not a complete register.** 55,092 resolved ringers is everyone BellBoard
  recorded 2012-2024 with a resolvable name. BellBoard is near-complete for
  this era but is not a census of all ringing.
- **Window-bound.** Everything here is true of 2012-2024. A ringer first
  recorded in 2012 may have rung since 1970; the data begins when recording
  did. Career-span and "first conducted" figures are lower bounds, not
  lifetimes.
- **Identity resolution has edges.** The resolver deliberately leaves
  bracketed and parenthetical name variants as separate clusters
  (`[Christopher C P Woodcock]`, `(3) Yvonne A Woodcock`) because those may
  be editorial annotations rather than the same person. This is conservative
  and correct; it means a small number of genuine duplicates remain split,
  which would very slightly inflate the ringer count and very slightly
  deflate the per-ringer figures. It does not change the shape of any finding
  above.

## How to reproduce

```
python scripts/build_local_db.py --out local_corpus.db
python scripts/ringer_career_analysis.py --local-db local_corpus.db
```

The script loads `data/ringer_identity_candidates.csv` into a TEMP table,
joins `performance_ringers` → `performances` → the map, and writes
`data/ringer_career_trajectories.csv`. The GROUP BY query plan uses the
covering index `idx_ringer_name_perf` and integer primary-key lookups — no
correlated-subquery multiplication, verified with `EXPLAIN QUERY PLAN` per the
project's read-cost standing constraint.
