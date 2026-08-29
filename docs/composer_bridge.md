# Bridging the composition library to the performance record

**Roadmap item [R-36](ROADMAP.md).** Built by `scripts/resolve_composer_bridge.py`;
candidates in `data/composer_bridge_candidates.csv`, hand labels in
`data/composer_bridge_adjudication.csv`.

CompLib holds 86,054 compositions. BellBoard holds 293,471 performances. Until
now the two corpora sat side by side with nothing joining them. This is the join
that turned out to be available, what it costs, and how far it can be trusted.

## The join everybody looks for first does not exist

`performances.composition` is populated on **0 of 293,471** rows. Not sparsely —
not at all. BellBoard's schema has the field and its contributors never fill it,
so no performance in this corpus can ever be tied to a specific composition.

That is worth stating flatly because it is the obvious thing to attempt and it
cannot be made to work by trying harder. It is also the fault behind the
withdrawn Junction 2 in `complib_insights_and_linkages.md`: a
`(method, length)` pair looks like it identifies a composition and does not —
40,437 such signatures cover 86,054 compositions, and `Stedman Triples @ 5040`
alone covers 1,496 of them. [R-37](ROADMAP.md) writes that dead end up in full.

What is left is the composer.

| | Populated | Of |
| --- | --- | --- |
| `performances.composition` | 0 | 293,471 |
| `performances.composer` | 71,959 (24.5%) | 293,471 |
| CompLib attribution (inside `derived_title`) | 79,056 (91.9%) | 86,054 |

## Parsing the two sides

**CompLib** puts the composer in `derived_title`, after the last `" by "`.
Splitting on the *last* occurrence rather than the first matters for seven
titles: `240 Death by Chocolate Bob Minor by Ryan J Faulkner-Hatt`, and an Op.
field reading `... shortened by Brian E Whiting by Ian M Holland`, where Holland
is the composer and Whiting wrote the thing that was shortened. Splitting on the
first `" by "` gets all seven wrong.

**BellBoard** is free text typed by whoever submitted the performance, and it
contains everything you would expect:

| Shape | Performances | Example |
| --- | --- | --- |
| carries a parenthetical | 10,617 | `J J Parker (12 part, 7th obs)` |
| a single token | 7,215 | `BEW`, `Elf`, `Monument`, `Traditional` |
| carries a composition number | 5,219 | `D F Morrison No. 108` |
| traditional / anonymous | 3,416 | `trad`, `Trad.`, `Anon` |
| mentions arrangement | 2,564 | `D F Morrison arr W J Couperthwaite` |
| names more than one person | 2,023 | `Charles Middleton and Henry Johnson` |
| a possessive reference | 581 | `Johnson's variation of Middleton's` |

Order matters twice here. Parentheticals come off **before** the string is split
on `and`, or `J S Warboys (SU0308 and SU0403)` becomes two men. Leading verbs
come off **before** trailing qualifiers, or `Arranged by John Pladdys` is deleted
entirely.

**Initialisms are deliberately not resolved.** `BEW` is almost certainly Brian E
Whiting and `MBD` almost certainly Mark B Davies, and this repository does not
guess. 2,249 performances credit a composer by initials alone; they are reported
unresolved with the reason attached, because a guess that happens to be right is
indistinguishable from one that is wrong, and only one of them is safe to build
on.

## The key, and what it costs before anything is matched

The key is **first initial plus surname**, lowercased: `a-cox`. It is crude on
purpose — [R-41](ROADMAP.md) is the brief to do it properly — and its cost can
be measured inside CompLib alone, before a single performance is looked at.

Of 1,223 keys, **24 cover more than one real person**, accounting for 2,277
credits — **2.9%**. That is the ceiling on precision, and it is a property of
the library rather than of this matcher.

| Key | Covers |
| --- | --- |
| `a-tyler` | Andrew N Tyler (824) · Albert M Tyler (46) |
| `c-nicholson` | Claire C Nicholson (332) · Colin F E Nicholson (1) |
| `j-parker` | Joseph W Parker (146) · Joseph J Parker (81) · James Parker (7) · Julian C Parker (3) |
| `d-smith` | Dylan M Smith (65) · David I Smith (4) · Daniel J Smith (3) · Damien S Smith (2) · David D Smith (1) |

Counting *distinct strings* rather than distinct people would have made this
figure three times larger and meaningless: 80 keys cover more than one string,
but `A J Cox` and `Anthony J Cox` are one man. Joint credits are split into
their individual people first, for the same reason — before splitting,
`David G Hull and Donald F Morrison` counts as a second `D Morrison` and the
apparent ambiguity is 48.3% instead of 2.9%.

## What the bridge resolves

| Outcome | Performances | Share |
| --- | --- | --- |
| **resolved** | 57,249 | 79.6% |
| not a person (`Traditional`, series names, empty parse) | 7,521 | 10.5% |
| ambiguous key (covers more than one person) | 2,528 | 3.5% |
| initialism, not guessed | 2,249 | 3.1% |
| no key match (CompLib holds no such composer) | 2,303 | 3.2% |
| incompatible (initials rule the person out) | 109 | 0.2% |

Of the 62,189 performances whose credit parses to a keyable personal name,
**92.1% resolve** — which reconciles with the 92.0% recorded on R-36 from a
looser earlier parse.

## Is it right? Two measurements, neither of them the matcher grading itself

### 1. The held-out subset, where truth is already available

When the credit spells the forename out — `Anthony J Cox`, not `A J Cox` — and
the CompLib name it reached also spells one out, the two forenames either agree
or they do not. Neither side comes from the matcher, so this is a genuine
held-out test. It covers **26,917 performances**.

180 of them disagree. A disagreement is *not* yet an error, and assuming
otherwise is what produced a first draft claiming 89.4% precision. All 69
distinct strings were read by hand and committed to
`data/composer_bridge_adjudication.csv`:

| | Performances | Strings |
| --- | --- | --- |
| the same person | 127 | 37 |
| genuinely a different person | 53 | 32 |

The same-person cases are diminutives (`Mike`/`Michael`, `Jim`/`James`,
`Lucy`/`Lucinda`), archaic written abbreviations (`Wm`/`William`, `Thos`/`Thomas`,
`Chas`/`Charles`, `Jas`/`James`), spelling variants (`Stephen`/`Steven`,
`Lesley`/`Leslie`) and one transposition typo (`Dainel`/`Daniel`). The genuine
errors are ordinary distinct forenames sharing an initial: `George Hayward`
matched to Graham R Hayward, `Selwyn Jones` to Stephen M Jones, `Roy Williams`
to Robert Williams.

**Precision on the checkable subset: 99.80%** (26,864 of 26,917).

Two of the errors are worth noting because they show the key doing exactly what
it was warned it would: `Raymond A Hutchings` → Richard A Hutchings and
`Peter J Flavell` → Paul J Flavell both have an agreeing *middle* initial, which
is what made them look strong.

Five parser bugs were found this way — three by reading the residual list, two
more by writing the unit tests for the fixes:

| Bug | Effect |
| --- | --- |
| `A.J. Cox` not recognised as initials | 226 performances of false errors |
| leading `Composed by` becomes the forename | credit keys as `b-middleton`, reaches nobody |
| `/` missing from the separator list | `John S. Warboys / Julian Morgan` reached only Morgan |
| `Arranged by John Pladdys` | **the whole credit deleted** — the trailing-qualifier rule strips from `arranged` to the end, which is right for `D F Morrison arr W J Couperthwaite` and wrong when the word opens the credit |
| `n/a Williams` | after `/` became a separator, split into `n` and `a Williams`, and `a Williams` keys as a real person |

The last two are the interesting pair: fixing the third bug caused the fifth, and
only the test written for the third caught it.

### 2. Corroboration, using evidence with no name in it

CompLib records each composition's stage and length. So for a resolved match,
ask a question the name plays no part in: **has this composer ever published at
the stage and length actually rung?**

| | Rate |
| --- | --- |
| matched composer publishes that shape | **94.3%** (48,876 of 51,852) |
| a randomly drawn composer does | 43.1% |
| lift over the null | **2.19×** |

The null draws a composer weighted by how much they have published, which is the
harder null — a prolific composer corroborates almost anything.

**But a rate is worth nothing until you know it discriminates.** PR #21's oracle
reported F1 = 1.00 while measuring nothing, because it had been bootstrapped from
the classifier it was testing. So the same test was run against the 68
hand-adjudicated strings, where the answer is already known:

| Bucket | Corroborates |
| --- | --- |
| known right | 94.5% (23,212 / 24,556) |
| **known wrong** | **11.6%** (5 / 43) |
| initial-only, unmeasurable by test 1 | 94.2% (25,659 / 27,253) |

It separates right from wrong by a factor of eight. That is what makes the last
row usable.

### The half neither test reaches directly

30,332 performances give an initial only, so test 1 is blind to them. Test 2 is
not, and because it discriminates, its rate can be inverted:

```
observed 0.942 = p x 0.945 + (1 - p) x 0.116     ->  p = 99.5%
```

So roughly **124 of those 27,253 are wrong**. The wrong-match rate rests on only
43 performances, but the estimate barely moves with it: the observed rate sits so
close to the right-match rate that `p` stays above 99% for any wrong-match rate
below 0.5.

## What this is, and what it is not

It is **57,249 performances** — 19.5% of the corpus, 79.6% of those carrying a
composer — attached to a named composer in CompLib, at a measured 99.8%
precision where checkable and an estimated 99.5% where not.

It is **not** a link to a composition, and no future work will make it one.
It is **not** applied to the corpus: `data/composer_bridge_candidates.csv` is a
candidate file with its status and evidence per row, in the same shape as
`data/method_location_candidates.csv`, and the ambiguous rows stay marked.

The 2,303 `no_key_match` performances are the interesting leftovers — composers
who appear in the belfry and not in the library. They are a starting point for
[R-38](ROADMAP.md), and they are also the mechanism behind every one of the 53
adjudicated errors: a composer CompLib does not hold, sharing a key with one it
does.

## Reproducing

```
python scripts/resolve_composer_bridge.py --local-db data/change-ringing.db
```

Every figure above is printed by that command. It exits non-zero if the
adjudicated labels no longer cover the disagreements the parser produces, so a
change to the parser cannot quietly leave the published precision measured
against stale labels.
