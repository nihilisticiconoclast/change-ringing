# A ringing career, from the bell people stand behind

**Mistral Vibe Task 7.** Measured on the 2012–2024 corpus, 293,471 performances
and 1,969,949 ringer appearances, against canonical identities from
`data/ringer_identity_candidates.csv` (55,326 entities, a candidate dataset with
unmeasured accuracy — see `docs/ringer_identity_resolution.md`).
Reproduce with `python scripts/analyse_ringing_careers.py --local-db <replica>`;
the database-only approximation, which groups raw names, is
[`queries/findings/ringing_careers.sql`](../queries/findings/ringing_careers.sql).

`performance_ringers.bell` is populated on **1,897,741 rows** and nothing else in
this project reads it. It is the most underused column in the corpus. Every
ringer knows the supposed arc: you learn on the treble, move to the inside
bells, and the tenor or the conducting comes later. This traces that arc across
real people.

## The cohort

**5,641 canonical ringers** have 50 or more single-bell tower appearances,
spanning five or more years — enough to trace an individual arc. (The brief's
6,563 was measured on a slightly earlier snapshot; the corpus and the identity
CSV are both moving targets, and this figure is what the committed replica
reproduces. The standing-constraints note that a local run is a weaker check
than production applies here too.)

`bell` holds single bells (`'1'`, `'11'`) and handbell pairs (`'1-2'`, up to
`'1-2-3-4-5-6-7-8-9-10-11-12-13-14'`). The pairs are handbell performances, a
different activity, and are excluded throughout. Bell number alone is not
comparable across towers — the tenor of a six is the 6, of a twelve the 12 — so
every appearance's position is normalised by the number of bells rung in that
performance (the count of single-bell rows for the perf is the ring size).
Normalised position is `bell / ring_size`: the treble is small, the tenor is
1.0.

## 1. How long is the apprenticeship?

Appearances before a first conducted performance, using
`performance_ringers.conductor`. Two versions, because the corpus is mostly
quarter peals and they answer different questions:

| Conducting… | Ever do it | Median wait | Mean | p25 | p75 |
| --- | ---: | ---: | ---: | ---: | ---: |
| any performance | **72.5%** | **11** appearances | 34 | 2 | 40 |
| a **peal** (≥5,000 changes) | **20.0%** | **37** appearances | 87 | 7 | 113 |

Conducting *something* is common and happens early — most who ever conduct do so
within their first dozen appearances. Conducting a **peal** is a different and
much smaller thing: a fifth of the cohort, reached three times later in a career.

This distinction matters enough to say plainly that the first draft of this
document got it wrong. It measured the first row and described it as the second
— "72.5% of the cohort ever conduct a peal" — which overstates peal conducting
by a factor of 3.6 and understates the apprenticeship by a factor of 3.4. The
error was not in the code, which never mentioned peals; it was in the prose
written over it. It sits alongside the two-populations finding, where 72% of
active ringers have *rung* a peal: about a fifth of those go on to call one.

## 2. Is the progression real?

The folk model says treble → inside → tenor. The data says no, and it says no
in both directions.

Mean normalised bell position, first tenth of a career against the last:

| | Mean position |
| --- | ---: |
| Early career (first 10%) | 0.550 |
| Late career (last 10%) | 0.546 |
| **Drift** | **−0.004** |

No upward drift — essentially zero, if anything slightly down. Split three ways
by whether a ringer's late position is more than 0.05 above, below, or within
their early position:

| Direction | Ringers | Share |
| --- | ---: | ---: |
| Moved up | 1,801 | 31.9% |
| Moved down | 1,979 | 35.1% |
| Stayed (±0.05) | 1,861 | 33.0% |

Roughly even, with no bias toward the tenor. **Ringers do not graduate up the
bells.** But neither do they find a bell and stay on it for twenty years: the
median within-ringer range of bell position is **0.889** — over a career the
median ringer rings across nearly the whole ring — and only **0.9%** end on a
single bell. They move around without moving up.

The intuition behind the folk model is real — ringers do rotate through the
bells — but the *direction* is not. There is no settled tenor that a ringer
ages into; there is a band that rings everywhere and conducts early.

## 3. What does leaving look like?

A ringer's last appearance is in the data. **An absence is not a death or a
resignation, it is an absence.** The corpus cannot distinguish someone who
stopped ringing from someone who moved, changed name, or rings at a tower that
does not report to BellBoard. So this is published as a cohort rate, never as a
statement about an individual, and never as a list of names.

Of ringers first seen in year Y, the share with no appearance after 2020:

| First seen | Ringers | None after 2020 | % gone |
| ---: | ---: | ---: | ---: |
| 2012 | 14,447 | 5,747 | 39.8% |
| 2013 | 3,750 | 2,232 | 59.5% |
| 2014 | 2,720 | 1,711 | 62.9% |
| 2015 | 2,270 | 1,383 | 60.9% |
| 2016 | 2,152 | 1,251 | 58.1% |
| 2017 | 2,059 | 1,139 | 55.3% |
| 2018 | 5,878 | 3,169 | 53.9% |
| 2019 | 2,233 | 1,201 | 53.8% |
| 2020 | 1,527 | 860 | 56.3% |

For the active cohort (50+ appearances) attrition is far lower:

| First seen | Ringers (50+) | None after 2020 | % gone |
| ---: | ---: | ---: | ---: |
| 2012 | 4,985 | 439 | 8.8% |
| 2013 | 291 | 26 | 8.9% |
| 2014 | 175 | 9 | 5.1% |
| 2015 | 151 | 7 | 4.6% |
| 2016 | 129 | 2 | 1.6% |
| 2017 | 127 | 2 | 1.6% |

The 2020 line is the example the brief asked for, and it crosses the COVID
discontinuity: ringing stopped almost entirely for a year from March 2020, so
the 2013–2020 cohorts are partly a pandemic effect rather than a steady
attrition. Cohorts first seen after 2020 cannot by construction have left
before 2020, so they are omitted. The honest reading is that roughly half of
everyone who starts ringing and is recorded here is not recorded five to eight
years later — but committed ringers (the 50+ cohort) attrite at under 10%,
which is what makes the rest of this document possible at all.

## What would change this answer

- **Ordinary service ringing, if it were ever recorded.** Like the
  two-populations finding, the population the folk model is really about — the
  Sunday service band — is invisible here, and it is plausibly the place where
  bell progression is real. This rules the model out for *reported* ringing,
  not for ringing as a whole.
- **Better identity resolution.** The candidate dataset's accuracy is
  unmeasured. Splitting one ringer into variants shortens each fragment's
  apparent career and narrows its slice of the ring, which would manufacture
  both more "specialists" and more "early leavers". The raw-name SQL cohort is
  6,234 against the canonical 5,641 — fatter, as fragmentation would predict.
- **A longer corpus.** Thirteen years is enough to see no progression; it is not
  enough to see a full lifetime arc. The 2024 edge is still open: ringers last
  seen in 2024 have not left, they are just at the end of the window.
