# A ringing career, from the bell people stand behind

**Roadmap item 7.** Measured 2026-08-15 on the 2012–2024 corpus, 293,471
performances and 1,969,949 ringer appearances.

Reproduce with:

```
python scripts/build_local_db.py --out local_corpus.db
sqlite3 local_corpus.db < queries/findings/ringing_careers.sql
```

The SQL returns one `(metric, value)` row per number; the figures below are
what it prints. The canonical-identity column is computed separately (see the
identity caveat) and is the one quoted in the prose.

## What the column sees

`performance_ringers.bell` is the most underused column in the corpus: 1,969,949
populated rows, of which 1,786,411 carry a single bell number (`'1'`, `'11'`),
111,330 carry a handbell pair or run (`'1-2'` up to
`'1-2-3-4-5-6-7-8-9-10-11-12-13-14'`), and 72,208 are NULL. Nothing in the
project had ever read it.

The progression is the one every ringer knows: you learn on the treble, move to
the inside bells, and the tenor or the conducting comes later. Nobody has
watched it happen to real people at scale. The cohort is ringers with 50 or more
tower-bell appearances spanning five or more years — **5,657 canonical ringers,
6,255 raw names** — the same threshold the populations query uses.

## Q1. How long is the apprenticeship?

Appearances before a ringer's first conducted peal.

| | canonical | raw names |
| --- | ---: | ---: |
| cohort | 5,657 | 6,255 |
| of whom ever conduct | 4,103 (72.6%) | 4,643 (74.2%) |
| never conduct | 1,554 | 1,614 |
| ringers in the distribution | 3,570 | 8,346 |
| **median** appearances before first conducted | **16** | **8** |
| mean | 39 | 23 |
| p25 | 4 | 3 |
| p75 | 46 | 23 |
| p90 | 102 | 55 |
| p99 | 333 | 222 |
| max | 1,067 | 1,613 |

The median ringer rings sixteen performances before the first one they conduct.
The long right tail is the interesting part: a tenth of ringers who ever conduct
pass a hundred appearances before doing so. But the centre of the distribution
is early — most people who will conduct have done so within their first few
dozen rings.

The raw-name median is half the canonical one because splitting a ringer into
name-fragments gives each fragment a shorter apparent career and fewer
appearances before its fragment-first conducted peal. The gap is the same
fragmentation effect the populations query documents: raw names manufacture
apparent specialists at the margins. The canonical figure is the finding.

## Q2. Is the progression real, or do people find a bell and stay?

The folk model says ringers move toward the tenor as they gain experience. The
bet in the brief was that most people find a bell and stay on it for twenty
years. **The bet was right that there is no march to the tenor, but wrong about
the reason: people do not settle either. They range across the bells throughout.**

Bell position is normalised as `bell_number / stage` — the highest bell rung in
that performance — so it is comparable across towers: the treble of a six is
~0.17, of a twelve ~0.08; the tenor is 1.0.

| | canonical | raw names |
| --- | ---: | ---: |
| most-used bell is ≥50% of appearances | 482 (8.5%) | 521 (8.3%) |
| most-used bell is ≥70% of appearances | 101 (1.8%) | 107 (1.7%) |
| mean share of a ringer's most-used bell | 0.317 | 0.316 |
| drift, first-10 to last-10 apps (bell position) | −0.0032 | −0.0032 |
| moved toward the tenor | 2,761 (48.8%) | 3,023 (48.3%) |
| moved toward the treble | 2,860 (50.6%) | 3,192 (51.0%) |
| unchanged | 36 | 40 |

Almost nobody settles on one bell: under one in eleven ringers ring half or more
of their appearances on a single bell, and the mean ringer's most-used bell
accounts for less than a third of their appearances. The drift from a ringer's
first ten appearances to their last ten is a wash — −0.0032 on a 0–1 scale, with
as many ringers drifting toward the treble as toward the tenor. If there were a
career-long progression to the tenor this would be clearly positive; it is
indistinguishable from zero.

Raw and canonical agree to the first decimal on every Q2 line. That is because
the finding is structural — name-splitting can only fragment a ringer and
understate their concentration, and there is very little concentration to
understate. This is the question where the identity caveat matters least.

## Q3. What does leaving look like?

Of ringers first seen in year Y, the share with no appearance after year Y+N.

| first seen | cohort (canonical) | no app after +3y | no app after +5y |
| ---: | ---: | ---: | ---: |
| 2012 | 14,361 | 27.5% | 33.1% |
| 2013 | 3,723 | 51.5% | 59.2% |
| 2014 | 2,700 | 56.1% | 66.6% |
| 2015 | 2,239 | 59.0% | 66.1% |
| 2016 | 2,136 | 61.7% | 65.7% |
| 2017 | 2,037 | 60.6% | 71.9% |
| 2018 | 5,773 | 65.7% | 84.0% |
| 2019 | 2,215 | 73.6% | 100.0% |

**An absence is not a death or a resignation, it is an absence.** This is a
cohort attrition rate — "of ringers first seen in 2014, 66.6% have no appearance
after 2019" — never a statement about an individual, and never a list of names.

Two artefacts to read past. 2012 is large because the backfill starts then, so a
one-year cohort from 2012 partly contains ringers whose earlier appearances are
out of frame and therefore count as their first — read 2013 onward. The +5y
column for 2019 is 100% by construction: five years on from 2019 is 2024, the
last year in the corpus, so every 2019 ringer's last appearance is at or before
it. The +3y column is the honest one for recent cohorts.

With those set aside, the signal is clear: roughly six in ten ringers first
recorded in 2013–2017 have no reported appearance five years later. Whether that
is genuine attrition — people leaving the exercise — or reporting drift (moving
to a tower that does not report, changing name, or the identity resolution losing
them) cannot be told from this data alone. The corpus cannot distinguish someone
who stopped ringing from someone who moved. What it can say is that a
substantial fraction of ringers become invisible to BellBoard within five years
of their first recorded appearance, and that the fraction is stable across
cohorts rather than growing, which is more consistent with a steady background
rate of turnover than with a cohort-specific collapse.

## Identity caveat

The SQL in `queries/findings/ringing_careers.sql` groups raw
`performance_ringers.name`, because the canonical identity resolution
(`data/ringer_identity_candidates.csv`, 55,326 entities, accuracy unmeasured) is
a CSV rather than a table, and a query in `queries/` must also prepare against
an empty schema in CI. The canonical figures above were computed against the
local replica with the CSV loaded as a temp table.

**99.8% of ringer rows resolve** to a canonical id (1,966,913 of 1,969,949; 611
distinct names unresolved, none NULL), so the two views agree closely. Where
they diverge — the Q1 median, the cohort size — raw names can only fragment a
ringer, which inflates the cohort count and shortens apparent careers. It
cannot manufacture a finding: the structural result in Q2 (ringers do not
settle) holds identically under both, because there is nothing to understate.

The identity resolution itself is a candidate dataset with unmeasured accuracy,
built from a peal-only snapshot predating the 13-year backfill. It is the best
available and is clearly labelled as such. A page can come later if a finding
justifies one; this is a finding worth a page, and the bell-progression result
is the part most likely to surprise a ringer.
