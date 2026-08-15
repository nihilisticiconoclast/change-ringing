# Quarter ringers and peal ringers are not two populations

**Roadmap item 23.** Measured 2026-08-15 on the 2012–2024 corpus, 293,471
performances and 1,969,949 ringer appearances.
Reproduce with `python scripts/analyse_peal_populations.py`;
the database-only approximation is
[`queries/findings/peal_and_quarter_populations.sql`](../queries/findings/peal_and_quarter_populations.sql).

## The claim being tested

Ringers describe two worlds. There is the Sunday band — the people who turn up
week after week to ring for a service at one tower — and there is the peal
circuit, a smaller, more mobile group who travel to ring long performances. The
received wisdom is that these are largely different people who happen to share
a set of buildings.

It is exactly the kind of thing this corpus should be able to settle, and until
the backfill finished it could not: the question needs a decade of performances
joined to resolved identities.

## First, correcting the question

Of 293,471 performances, **198,715 are between 1,000 and 1,399 changes** and the
single commonest length on a Sunday is 1,260, thirty-three thousand times over.
Those are quarter peals.

**Ordinary Sunday service ringing is not in this corpus at all.** Rounds and call
changes for half an hour before a service are not reported to BellBoard; only a
performance somebody thought worth recording is. So "Sunday ringing" in the data
means "a quarter peal that happened to be on a Sunday", and the original framing
of this item — service band versus peal circuit — asks about a population the
corpus cannot see.

The answerable version is **quarter ringers versus peal ringers**. That is the
same sociological question with an honest name, and everything below is about it.

## The answer: one population, not two

Peal share per canonical ringer, for the 5,874 ringers with at least 50
appearances:

```
   0-9  % peals  3,979  ##############################################
  10-19 % peals    572  ######
  20-29 % peals    306  ###
  30-39 % peals    241  ##
  40-49 % peals    176  ##
  50-59 % peals    149  #
  60-69 % peals    157  #
  70-79 % peals    108  #
  80-89 % peals    113  #
  90-99 % peals     73
```

A single steep decay with a long thin tail. **Two populations would show two
humps.** There is one, and the median active ringer spends 3.0% of their
reported ringing on peals.

Ringers who ring *only* peals essentially do not exist: **0.0–0.1%** at every
activity threshold from 10 appearances upward.

## Nor is it two kinds of tower

The same test over 1,226 towers with 50 or more performances gives the same
shape — 610 in the lowest band, decaying monotonically, median peal share 10.0%.
There is no peal-tower / quarter-tower split either. Towers differ in how much
peal ringing they host, continuously, the way they differ in everything else.

## Nor is it graduation

If peals were what you progress to, peal share would climb with experience. It
does not:

| Years active | Ringers | Mean peal share | Ever rang a peal |
| ---: | ---: | ---: | ---: |
| 1 | 38 | 11.8% | 50.0% |
| 3 | 78 | 12.1% | 59.0% |
| 5 | 118 | 10.8% | 72.9% |
| 7 | 241 | 9.6% | 63.5% |
| 9 | 185 | 8.5% | 66.5% |
| 11 | 571 | 10.4% | 64.6% |

Flat between 8.5% and 12.1% across eleven years. The 12-year bucket is excluded
from that reading: 12 years is the full width of the corpus, so it means
"present throughout" rather than "has rung for twelve years", and it is
confounded by exactly the selection you would expect.

## What survives

The strong folk model is wrong. A weaker and more interesting one holds:

> **Peal ringing is an occasional activity spread thinly across one community,
> not a circuit with its own membership.**

Two things make that more than a deflation. **72% of ringers with 50 or more
appearances have rung at least one peal** — far more inclusive than
"a separate elite" implies. And yet the median such ringer still spends 97% of
their reported ringing on quarters. It is not that a few people ring peals; it
is that most committed ringers ring a few.

## What would change this answer

- **Ordinary service ringing, if it were ever recorded.** The population the
  original question asked about is invisible here, and it is plausibly the one
  that is genuinely separate. Nothing in this document rules that out; it rules
  out a split between the two activities the corpus *can* see.
- **Better identity resolution.** See below.
- **A weighting by effort rather than count.** A peal is roughly three hours and
  a quarter roughly forty-five minutes, so a 3% peal share by count is nearer 11%
  by time. That does not create a second mode, but it changes what "3%" feels
  like and any published version should say so.

## Caveats

**Identity.** Ringers are resolved through
[`data/ringer_identity_candidates.csv`](../data/ringer_identity_candidates.csv),
55,326 canonical entities, **accuracy unmeasured**. This is a candidate dataset
and the same warning applies as to the footnote classifier.

The direction of the bias is worth stating because it is not the obvious one. An
earlier draft of the SQL comment claimed unresolved names could only thicken the
left-hand bar. That is wrong. Comparing the canonical histogram with the same
histogram over raw names:

| Band | Canonical ids | Raw names |
| --- | ---: | ---: |
| 0–9% peals | 3,979 | 4,659 |
| 80–89% peals | 113 | 196 |
| 90–99% peals | 73 | 165 |

Raw names produce a visibly fatter **right** tail. Splitting one person into
variants gives each fragment fewer appearances drawn from a narrower slice of
their ringing, so a fragment can look 100% peal when the person is not. **Poor
identity resolution manufactures apparent specialists at both ends** — which
means the unresolved view is the one that looks more like two populations, and
it is the less trustworthy of the two. Better resolution would strengthen this
finding, not weaken it.

**The 5,000-change threshold** is the conventional peal minimum and is applied
uniformly. At higher stages a peal is longer, so a handful of long quarters and
short peals sit on the wrong side of it. The effect is far too small to move a
distribution this lopsided.

**No names are published**, here or in the query output. The unit throughout is
a count of ringers in a band.
