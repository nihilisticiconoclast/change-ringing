# Does a tower ring on the night Dove says it does?

**Roadmap item 21 / Gemini Task 6.** Cross-source check of Dove's stated practice
night against 293,471 BellBoard performances, 2012–2024.

Every figure below comes from
[`queries/findings/practice_night_agreement.sql`](../queries/findings/practice_night_agreement.sql),
which holds two statements — the Mon–Sat comparison and the Mon–Fri one. Re-run
either and you get these numbers.

## The finding

Dove records a practice night for 3,513 towers. BellBoard records when ringing
actually happened. Neither corpus can be checked against itself.

| | Towers | Stated night is busiest | Chance | Mean share on stated night |
| --- | ---: | ---: | ---: | ---: |
| **Mon–Sat** | 1,569 | **27.3%** | 16.7% | 22.0% |
| **Mon–Fri** | 1,054 | **43.9%** | 20.0% | 31.0% |

**Excluding Saturday is what makes the signal visible.** On weekdays alone, a
tower's stated practice night is its busiest ringing night more than twice as
often as chance would give, and nearly a third of all weekday ringing lands on
that one evening. Saturday is outing and peal-attempt day, and it competes with a
weekday practice in a way the other days do not.

So Dove's practice night is genuinely informative — considerably more so than the
Mon–Sat figure alone suggests, which is why the split matters.

## Two confounds, both load-bearing

**Sunday.** Reported short performances are dominated by Sunday service quarters
at nearly every tower, so comparing the outright busiest day of the week returns
Sunday almost everywhere. A first cut that did not exclude Sunday scored **15.9%**
and read as a scandal about Dove's data quality. It was not a finding; it was a
confound.

**Reporting.** BellBoard records *reported* performances — overwhelmingly quarter
peals. **Ordinary practice-night ringing is almost never reported.** This measures
where reported quarters cluster, which is a proxy for practice night and not the
thing itself.

> The 27.3% and 43.9% figures are **lower bounds on agreement**, not estimates of
> how many Dove entries are stale. A tower that practises on Tuesday and rings its
> quarters on Saturday scores zero here while its Dove entry is perfectly correct.
> Any summary that turns these into "half of Dove's practice nights are wrong" is
> misreading them.

## Activity makes the agreement stronger

The brief asked whether a busy tower's entry is more reliable than a quiet one's.
It is, and the effect is large at the top end.

| Activity (non-Sunday short perfs) | Towers | Stated night busiest | Mean share |
| --- | ---: | ---: | ---: |
| 20–49 | 1,072 | 25.7% | 20.8% |
| 50–99 | 355 | 30.4% | 24.4% |
| 100–199 | 108 | 27.8% | 22.3% |
| 200+ | 34 | **44.1%** | **35.3%** |

The middle two tiers sit within noise of each other on 108 and 355 towers, so the
shape is "the very busiest towers are clearly different" rather than a clean
gradient — and 34 towers is a thin top tier. Worth stating that way rather than
drawing a line through four points.

## Parsing the `Practice` column

Of 3,513 towers carrying a non-empty `Practice` value, the query accepts those
beginning with a weekday abbreviation and containing neither `alt` nor
`arrangement`. That admits `Tue 19:00` and `Thu (exc Bank Hols)` while rejecting
`Thu (alt)`, `Tue (1st, 3rd, 5th)` and `PN: by arrangement`.

The matching cohort is smaller again because a tower also needs 20 or more
reported non-Sunday short performances to be testable at all: **1,569 towers**
Mon–Sat, and 1,054 once Saturday is excluded and Saturday-practice towers drop
out.

## Towers at the extremes

Named because a tower is a building, not a person.

Taken from the query's own output, towers with 150 or more non-Sunday short
performances.

**Highly aligned** — nearly all non-Sunday ringing on the stated evening:

- **Frodsham, Cheshire** (S Lawrence) — stated `Fri`, 444 of 458 (96.9%)
- **Pettistree, Suffolk** (S Peter & S Paul) — stated `Wed`, 553 of 594 (93.1%)
- **Barnes, Greater London** (S Mary) — stated `Fri`, 337 of 375 (89.9%)

**Poorly aligned** — busy towers whose quarters almost never fall on the stated
night:

- **Cambridge, Cambridgeshire** (S Edward K&M) — stated `Tue`, 1 of 229 (0.4%)
- **Amersham, Buckinghamshire** (S Mary V) — stated `Wed`, 1 of 185 (0.5%)
- **High Ercall, Shropshire** (S Michael & All Angels) — stated `Thu`, 2 of 242 (0.8%)

The second group is the caveat made concrete. S Edward's at 0.4% is not evidence
that Dove is wrong about it; it is a tower whose *reported* ringing is something
other than practice-night quarters, with the practice itself invisible to
BellBoard.

## Provenance

This landed as PR #15 and was merged with the numbers re-derived. As submitted,
the write-up reported 1,404 towers at 27.7% and 1,288 at 44.0%, which the
committed query does not produce — it returns 1,569 at 27.3% and 1,054 at 43.9%.
Every tier in the activity table was out by the same kind of margin, and three of
the six case studies named the wrong practice night: Frodsham as `Thu` when the
data says `Fri`, Barnes as `Tue 20:00` when it says `Fri`, Escrick as `Mon` when
it says `Tue`. A sixth, Perth, does not appear in the query's output at all.

The percentages were right in every case, which is the tell: the figures had been
computed by a different code path and then paired with tower metadata from
another, so the rates survived and the labels attached to them did not. The
conclusion is unaffected and the analysis is good — but a document that cannot be
reproduced from its own recorded query is not yet finished. Both statements are
now in the query file and every figure above comes from running it.
