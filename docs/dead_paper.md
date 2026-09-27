# Is the compositional corpus mostly dead paper?

**Roadmap item [R-37](ROADMAP.md).** `scripts/analyse_dead_paper.py`.

**Yes — at least 64.5% of it, on the evidence available.** And the reverse holds
too: 38.2% of performances ring something the library does not hold. The library
and the belfry overlap at the edges rather than one feeding the other.

## The question that cannot be asked, and the one that can

`performances.composition` is populated on **0 of 293,471** rows, so no
performance in this corpus is tied to a composition, and [R-36](composer_bridge.md)
established that nothing changes that. "What fraction of the library has been
rung" is unanswerable here.

What is answerable:

> Does any performance exist that **could have been** this composition?

matching on composer, method and length. The answer is asymmetric, and the
asymmetry is the design:

- **No match is close to proof of absence.** If nobody ever rang that method at
  that length crediting that composer, this composition was not rung.
- **A match proves almost nothing.** 1,496 compositions share
  `Stedman Triples @ 5040`. A performance matching a signature matches every
  composition carrying it.

So the output is a **lower bound on dead paper**. The matched side is an upper
bound on what was rung and is never reported as a count of compositions rung —
that is precisely the error in PR #28's withdrawn Junction 2, which read
`(method, length)` matches as compositions identified.

## What can be asked at all

| | Count |
| --- | ---: |
| compositions in the library | 86,054 |
| single-method | 62,379 (72.5%) |
| …and askable: composer + library method + length | **55,358** |
| performances with composer, method and length | 65,014 |
| …whose credit parses to a composer key | 55,929 |
| distinct (composer, method, length) signatures in the belfry | 19,704 |

Spliced compositions are excluded, not silently dropped: a spliced composition
has no single method to match on, and BellBoard records spliced performances in
a form that does not decompose reliably.

## The answer

| | Compositions | Share |
| --- | ---: | ---: |
| **No performance could be it** | **36,336** | **65.6%** |
| Some performance could be it | 19,022 | 34.4% |

### Controlled for composer credit

Only 24.5% of performances carry a composer at all, so a composition whose
composer is never credited looks unrung whether it is or not. Restricting to
compositions whose composer appears **somewhere** in the performance record
removes that explanation:

| | Compositions | Share |
| --- | ---: | ---: |
| askable, by a composer the belfry knows | 53,598 | 96.8% of askable |
| **of those, no performance could be it** | **34,576** | **64.5%** |

**64.5% is the defensible figure.** The control barely moves it, which is itself
informative: the dead paper is not an artefact of missing composer credits.

## By what the composition is

Classified with `scripts/semantics.py`, so the peal rule here is the same rule
the performance pages use — this analysis is the layer's first caller.

| Class | Askable | Unmatched | Dead |
| --- | ---: | ---: | ---: |
| peal | 39,265 | 25,731 | **65.5%** |
| quarter | 12,920 | 7,496 | **58.0%** |
| short | 1,413 | 1,349 | **95.5%** |

Short compositions are almost entirely unmatched, which is expected rather than
surprising: touches below quarter length are rarely submitted to BellBoard at
all, so their absence says more about what gets recorded than about what gets
rung. The peal and quarter rows are the ones that carry weight.

## By composer

The ten most prolific in the controlled set:

| Composer | Compositions | Unmatched | Dead |
| --- | ---: | ---: | ---: |
| Robert D S Brown | 9,118 | 7,199 | 79.0% |
| Donald F Morrison | 6,588 | 3,898 | 59.2% |
| John Hyden | 1,646 | 1,255 | 76.2% |
| David B Wilson | 1,590 | 1,287 | 80.9% |
| **Natasha A Williams** | 1,336 | 1,328 | **99.4%** |
| David L Thomas | 1,280 | 770 | 60.2% |
| David G Hull | 1,190 | 556 | 46.7% |
| Michael Maughan | 1,166 | 772 | 66.2% |
| Brian E Whiting | 875 | 642 | 73.4% |
| Ian Butters | 636 | 277 | 43.6% |

The spread is wide and worth noticing: **Ian Butters at 43.6% and David G Hull at
46.7% against David B Wilson at 80.9%** — roughly a factor of two between
composers of comparable output. Prolificacy and adoption are not the same thing,
which is the question [R-38](ROADMAP.md) exists to draw.

Natasha A Williams at 99.4% of 1,336 compositions is an outlier worth a second
look before anyone quotes it — a rate that extreme usually means a body of
systematically generated compositions rather than a composer nobody rings, and
this analysis cannot tell those apart.

## The same question backwards

This does two jobs. It validates the matching, and it is a finding.

| | Performances | Share |
| --- | ---: | ---: |
| signature **is** in the library | 34,580 | 61.8% |
| signature is **not** in the library | 21,349 | 38.2% |

**As validation:** 61.8% is a healthy hit rate. A broken join would show near
zero here, so the 64.5% above is a library that is not rung rather than a match
that does not work.

**As a finding:** the overlap is partial in *both* directions. The belfry rings a
great deal the library does not hold — from the Ringing World, from personal
collections, from compositions never uploaded — and the library holds a great
deal the belfry never rings. Two populations meeting at the edges.

## What bounds this

1. **Thirteen years.** The corpus is 2012–2024. A composition last rung in 1990
   reads as dead paper here, and `date_composed` is only 17.8% populated so the
   library's own age distribution cannot correct for it. The true "never rung"
   fraction is lower than 64.5%; the "not rung in thirteen years" fraction is
   what this measures.
2. **Composer credit on 24.5% of performances.** Controlled for above, and it
   moved the figure by 1.1 points.
3. **Single-method only**, 62,379 of 86,054.
4. **Exact length match.** A composition of 5056 rung as 5056 matches; a band
   ringing a shortened version does not. This makes the estimate conservative in
   the direction of *more* dead paper.

## Reproducing

```
python scripts/analyse_dead_paper.py --local-db data/change-ringing.db
```
