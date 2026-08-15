# Ideas: visualisations and insight seams

Options, not commitments. Every figure below was measured against
`data/change-ringing.db` on 2026-08-10, and each option says what would have to
be built and where it could go wrong — so a choice can be made on evidence
rather than on how good the idea sounds.

**What the corpus now holds.** 293,471 BellBoard performances (2012–2024),
1,969,949 ringer appearances across 70,032 distinct names, 337,946 footnotes,
25,066 methods with complete place notation, 63,966 bells, 7,262 towers (15,722 rings).

---

## Visualisation options

### A. The Blue Line Atlas — a periodic table of method shapes

**The idea.** Change ringing already has a native visual language: the path a
bell traces through a method, drawn as a line. Ringers learn methods by that
shape. Nobody has ever drawn all of them at once.

`notation` is populated for **all 25,066 methods**, so every shape in the
collection is derivable. Render each as a small multiple, arranged so
structurally similar methods sit together — a wall of curves where Cambridge,
Yorkshire and Superlative are visibly cousins and a Jump method is visibly
alien.

**Why this is the strongest option.** It is domain-native rather than a generic
chart type imposed on the data, it is genuinely beautiful, and it has a
**complete built-in oracle**: parse the notation, apply it from rounds, and the
row reached must equal the `lead_head` column — populated for all 25,066
methods. A parser is either right on 25,066 cases or it is not. No labelling,
no judgement.

**Prerequisite.** A place-notation parser. That is real work but exactly
specified, and the oracle makes it safe to delegate.

**Risk.** 25,066 small multiples will not fit one page; needs a defensible
selection or a zoomable canvas. Blue lines for stage 2–4 methods (1,714 of
them) are trivial and visually dull.

---

### B. The Rhythm of Ringing — the week and the year

**The idea.** Ringing has a pulse, and the data shows it plainly:

| Day | Performances | |
| --- | ---: | --- |
| Sunday | 23,648 | service ringing |
| Saturday | 19,378 | the peal day |
| Wednesday | 8,377 | the trough |

And a seasonal shape nobody expected: **September is the busiest month at
12,067**, ahead of May (10,803) and June (10,170), with January lowest at
5,417. I do not know why September peaks. That is the point — it is a real,
visible, unexplained pattern in a national dataset.

The four years also contain the pandemic recovery in the open: **2021: 16,729 →
2022: 28,212**, a 69% jump, then a settling to 25,859 and 25,267.

**Why it is worth doing.** Cheapest option by far — the data needs no
derivation. A polar year-clock with the weekly cycle layered on it, split by
tower versus handbell, tells three stories at once.

**Risk.** Calendar heatmaps are a well-worn form; the novelty is entirely in
the findings, so the design has to be unusually good to avoid looking generic.
The September spike needs an explanation before it is published, or it should
be presented explicitly as an open question.

---

### C. Invention and Survival — the long tail of methods

**The idea.** 9,169 distinct methods were rung across four years. **6,389 of
them — 70% — were rung exactly once.** Meanwhile Plain Bob Doubles was rung
5,719 times.

Set that against Gemini's extension-lineage data and the question becomes
interesting: of the methods rung once, which spawned descendants at higher
stages, and which are evolutionary dead ends? Method invention is unusually
well documented — every method has a named inventor and a first-peal date — so
this is a rare chance to watch a creative tradition's hit rate.

**Risk.** Four years is a short window for a survival claim. A method rung once
in 2021–24 may be a century-old standard that simply had a quiet spell. This
needs the historical backfill to be honest, or it must be framed strictly as
"in this window".

**Also worth knowing:** "Tolling" appears as the third most common *method* at
4,168 performances, and is not a method at all. Any method-frequency chart must
exclude it or it will be visibly wrong to a ringer.

---

### D. Why People Ring — the footnote corpus

**The idea.** 113,895 footnotes are free text, and they are where the human
occasion lives:

| Mentions | Count |
| --- | ---: |
| birthday | 7,877 |
| "memory" (memorials) | 7,345 |
| funeral | 3,975 |
| wedding | 2,254 |
| "first peal" | 2,221 |

Ringing marks things. 7,345 performances rung in someone's memory is a
different kind of dataset from a tower register, and no visualisation of
ringing has ever shown *why* it happened.

**The pairing with "Tolling":** 4,168 single-bell performances, overwhelmingly
memorial. Band size confirms it — 4,576 performances have exactly one ringer.

**Why it suits Gemini.** Classifying 113,895 free-text footnotes into occasion
types is a large-context task with no published answer.

**Risk, and it is real.** This is data about identifiable people, much of it
about deaths. Aggregate patterns are fine; a searchable index of named
memorials is not something to publish without thought. Recommend aggregate-only
and no named individuals in the visualisation.

---

### E. The Acoustic Landscape — pitch and weight across the country

**The idea.** Dove records what each bell *sounds* like: `Nominal__Hz` on
46,629 bells, `Note` on 54,936, `Weight__lbs` on 54,366, and a tenor weight for
7,259 of 7,262 rings. The country has an acoustic geography — heavy, low rings
in city churches, light rings in villages — and it has never been mapped.

With Web Audio, a ring could be *heard*: click a tower, hear its actual
nominal frequencies. That is a genuinely new thing for this data.

**Risk.** Nominal frequency is not the perceived note in a simple way, and
getting the acoustics wrong in public would be noticed immediately by the
audience most likely to look. Needs a ringer's review before publishing.
Synthesised bell tone is also hard to make un-awful.

---

## Insight seams worth a look

Things the data can answer that nobody has asked. Each is a query, not a project.

- **Ringing is far less concentrated than expected.** The ten busiest towers
  account for just **3.4%** of all performances, spread across **5,623 active
  towers** — 77% of all rings in the country saw a recorded performance in four
  years. I expected heavy concentration and was wrong; the negative result is
  the interesting one.
- **Band size is bimodal**: 36,271 performances on six bells, 23,040 on eight.
  The six/eight split is the real structure of the activity, not a smooth
  distribution.
- **557 distinct associations** appear. Which are growing, which shrinking, and
  do their territories overlap or tile?
- **Conductor concentration.** `performance_ringers.conductor` is flagged. Do a
  few people conduct disproportionately, and is conducting a career stage?
- **Tenor weight versus method difficulty.** Are harder methods rung on lighter
  bells? Plausible and testable, joining `dove.Wt` to method classification.
- **The September question.** Association AGMs? Harvest? The end of the holiday
  season? Worth resolving before it is published as a finding.

---

## What I would pick

**B first** — cheapest, the findings are already in hand, and the pandemic
recovery plus the September anomaly are publishable now.

**A next**, because it is the one that could not be done anywhere else and the
parser has a perfect oracle. The parser is reusable well beyond the picture.

**D with care.** The most affecting material in the corpus, and the only option
with an ethical dimension worth pausing over.

**C after the backfill**, not before — the survival claim is not honest on a
four-year window.
