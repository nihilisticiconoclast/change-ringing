# Ideas: visualisations and insight seams

Options, not commitments. Every figure below was measured against
`data/change-ringing.db` on 2026-08-10, and each option says what would have to
be built and where it could go wrong — so a choice can be made on evidence
rather than on how good the idea sounds.

**What the corpus now holds.** 293,471 BellBoard performances (2012–2024,
thirteen complete years — the whole of BellBoard's near-complete era),
1,969,949 ringer appearances across 70,351 distinct names, 337,946 footnotes,
28,066 performance flags, 25,066 methods with complete place notation, 63,966
bells, 7,262 rings, and 86,040 CompLib compositions.

Figures below that predate the backfill are marked with the window they were
measured over. **A finding stated without a window is a finding waiting to
change size.** The clearest case in this project, measured three times on the
same query as the corpus grew:

| Window | Major methods never rung |
| --- | ---: |
| 2021–24 | 81.6% |
| 2018–24 | 70.6% |
| 2012–24 | **53.9%** |

Nothing about the method or the library changed. Three thousand Major methods
moved from "dead" to "in use" on nothing but a wider view.


---

## Seams worth mining now the corpus is whole — 2026-08-15

Thirteen years, four corpora, and a method linkage joining the two largest.
Nearly every idea below is only possible *because* of a join nobody had made,
and each is stated with what was measured to check it is worth doing, so none
of them is a hunch.

The theme is deliberate: **things every ringer knows and nobody has measured**,
and **things sitting in two datasets that have never been put side by side**.

### A. Does a tower ring on the night Dove says it does? — *measured, and the answer is "sort of"*

Dove records a practice night for 3,515 towers. BellBoard records when ringing
actually happened. **The two have never been compared**, and it is the cheapest
cross-source check in the repository.

Measured, 897 towers with an unambiguous non-Sunday practice night and at least
20 reported non-Sunday short performances:

| | |
| --- | ---: |
| Towers whose busiest non-Sunday night is the one Dove states | **31.3%** |
| Expected if the stated night carried no information | 16.7% |
| Mean share of a tower's non-Sunday ringing on its stated night | **23.8%** |
| A flat week would give | 16.7% |

So Dove's practice night is real but weak: about twice chance, and **two towers
in three do not ring most on the night their own Dove entry names.**

The first cut of this got 15.9% agreement and looked like a scandal. It was
confounded: Sunday service ringing dominates reported short performances at
almost every tower, so the "busiest day" was Sunday nearly everywhere. Excluding
Sunday is what turns a mistake into a measurement.

**The caveat is as important as the number.** BellBoard records *reported*
performances — quarter peals, mostly — and ordinary practice-night ringing is
almost never reported. So this measures where reported short performances
cluster, which is a proxy for practice night and not the thing itself. 31.3% is
a lower bound on agreement, not an estimate of how many Dove entries are stale.
Anyone publishing this must say so in the same breath.

### B. A ringing career, from the bell people stand behind

`performance_ringers.bell` is populated on **1,897,741 rows** and, as far as I
can tell, nothing in this project has ever read it. It is the single most
underused column in the corpus.

Every ringer knows the progression — you learn on the treble, graduate to the
inside bells, and the tenor or the conducting comes later. Nobody has watched it
happen to real people at scale. **6,563 ringers have 50 or more appearances
spanning five or more years**, which is enough to trace an individual arc:
first appearance, the bells they ring over time, the peal at which they first
conduct, and whether they stop.

Three questions it answers that cannot be answered any other way:

- **How long is the apprenticeship?** Appearances before a first conducted peal.
- **Does the progression actually exist?** Or do most people find a bell and
  stay on it for twenty years — which is what I would bet on.
- **What does leaving look like?** A ringer's last appearance is in the data.
  Attrition is a real concern in the exercise and nobody has measured its shape.

Careful with the last one: an absence is not a death or a resignation, it is an
absence. Published as a cohort rate, never as an individual.

### C. Two populations, one exercise — *measured, and the answer is no*

**Done: `docs/two_populations.md`.** The folk model is wrong. Peal share per
ringer is a single steep decay — median 3.0%, no second mode — and the same
shape holds for towers. Peal-only ringers are 0.1%. Peal involvement does not
rise with years ringing. 72% of ringers with 50+ appearances have rung at least
one peal, and the median one still spends 97% of their ringing on quarters:
**peal ringing is an occasional activity spread across one community, not a
circuit with its own membership.**

The framing below had to be corrected before it could be answered — ordinary
Sunday service ringing is not reported to BellBoard and is absent from the
corpus entirely, so the question the data can answer is quarter ringers versus
peal ringers. The original text is kept:

#### Original framing

Measured on the full corpus:

| | Peals (5,000+ changes) | Shorter |
| --- | ---: | ---: |
| Sunday | 6,995 | 67,812 |
| Saturday | 13,634 | 35,653 |
| Weekday | 31,870 | 115,719 |

**Sunday is 91% short performances; Saturday is the peal day.** Ringers know
these are largely different activities and substantially different people. The
corpus can now test the second half: with 55,326 canonical identities, do the
Sunday population and the peal population overlap, or is the exercise two
communities sharing a set of buildings? That is a structural claim about a
hobby that nobody has been able to check.

### D. Heavy bells as a separate circuit — the Dove-to-BellBoard join nobody uses

Dove carries every ring's tenor weight; BellBoard carries who rang. Joining them
asks whether the heavy towers — 25cwt and up — draw a distinct and smaller
population, which is the received wisdom and has never been shown. The same join
gives the honest version of Gemini's conductor question below: speed controlled
for weight rather than confounded by it.

### E. What is regional is not what anyone thinks — *measured, and it is a negative*

Exactly **one** library method out of 25,066 is more than 50% concentrated in a
single county, against a baseline where the busiest county holds 6.6% of all
ringing. The named repertoire is effectively uniform across England.

Regional distinctiveness is real and lives entirely in what the Methods Library
does not index: Devon Call Changes at 85% in Devon, Quick Tolling at 99% in
Lincolnshire, a Cornish doubles call-change form found essentially nowhere else.
See `queries/findings/method_regionalism.sql` and `regional_traditions.sql`.

The follow-up is normalisation: those are free-text strings, so each tradition's
count is a lower bound and one recorded under several spellings is invisible.

### Dropped after checking

- **Composition reuse.** `performances.composition` is populated on **0** of
  293,471 rows, so "do bands ring published compositions or the same handful?"
  cannot be asked of this corpus. `composer` is there on 24.5%, which supports a
  much weaker version and not the interesting question. CompLib's 86,040
  compositions cannot be joined to performances without the composition text.

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

> **Built — `docs/rhythm.html`. And it corrected two of the figures below,
> including the headline one.** What is struck through was measured correctly
> and interpreted wrongly. It is left in place rather than quietly edited,
> because the mistake is the most useful thing on this page.

**The idea.** Ringing has a pulse, and the data shows it plainly:

| Day | Performances | |
| --- | ---: | --- |
| Sunday | 23,648 | service ringing |
| Saturday | 19,378 | the peal day |
| ~~Wednesday~~ | ~~8,377~~ | ~~the trough~~ |

~~And a seasonal shape nobody expected: **September is the busiest month at
12,067**, ahead of May (10,803) and June (10,170), with January lowest at
5,417. I do not know why September peaks. That is the point — it is a real,
visible, unexplained pattern in a national dataset.~~

The four years also contain the pandemic recovery in the open: **2021: 16,729 →
2022: 28,212**, a 69% jump, then a settling to 25,859 and 25,267. That one
stands.

**What was actually wrong, and why it matters more than the finding.**

- **September is not the busiest month.** 5,937 of its 12,067 performances —
  49% — fall in the eleven days between the death of Elizabeth II and her state
  funeral. Removing 24 nationally anomalous days, found by rule rather than from
  memory, takes September to 6,130 and **7th of twelve**. The busiest months are
  November and December. `queries/findings/september_is_one_funeral.sql`.
- **Nobody knew why because nobody had asked the data.** The explanation was
  sitting in the corpus as free text the whole time: the most repeated footnote
  on 9 September 2022 is “In memoriam HM Queen Elizabeth II”, written
  independently by hundreds of bands. It took one `GROUP BY` to find. "Nobody
  knows why" was a claim about the analysis, not about the world.
- **Wednesday is not the trough either.** Once the same 24 days are removed,
  Monday is lowest — four of them fell on a Monday, including the funeral. And
  the Monday/Wednesday gap is 5.7%, so naming any single day was over-reading.
- **24 days carry 21.0% of four years of ringing.** That is the real finding,
  and it is a much better one than a month name.

**What the page ended up being about.** Not the calendar. Two extra columns —
whether the performance was *tolling*, and whether the footnote says the bells
were *half-muffled* — separate those 24 days into celebration, remembrance, a
death, and the funerals that are both. Remembrance Sunday's muffled rate is
73%, 74%, 72%, 74% across four years against a 5.7% baseline, the steadiest
number this project has found in any corpus. And "99 Tolling" turns out to
record the age of the person who died, in a field reserved for method names, in
a corpus with no age column anywhere.

**Risk, as assessed beforehand.** "Calendar heatmaps are a well-worn form; the
novelty is entirely in the findings, so the design has to be unusually good."
That was right, and the answer turned out not to be better design: it was
finding something other than a calendar to put on the page.

---

### C. Invention and Survival — the long tail of methods

> **Invention half built — `docs/invention.html`. Survival still waits.** The
> premise below contains a factual error, corrected underneath rather than
> deleted, because it is the kind of error that shapes a whole plan.

**The idea.** 9,169 distinct methods were rung across four years. **6,389 of
them — 70% — were rung exactly once.** Meanwhile Plain Bob Doubles was rung
5,719 times.

Set that against Gemini's extension-lineage data and the question becomes
interesting: of the methods rung once, which spawned descendants at higher
stages, and which are evolutionary dead ends? Method invention is unusually
well documented — ~~every method has a named inventor and~~ a first-peal date — so
this is a rare chance to watch a creative tradition's hit rate.

**Risk.** Four years is a short window for a survival claim. A method rung once
in 2021–24 may be a century-old standard that simply had a quiet spell. This
needs the historical backfill to be honest, or it must be framed strictly as
"in this window".

**Corrections from building it.**

- **No method has a named inventor in this data.** No column in any of the four
  corpora records who devised a method — not the Methods Library, not BellBoard,
  not Dove, not CompLib. What exists is the first *performance*: date, place and
  society. In change ringing that is close to the same event, since a method
  enters the collection by being rung and named, so the page says "first rung"
  throughout. But "watch a creative tradition's hit rate" cannot be done by
  inventor, and planning around that sentence would have wasted a day.
- **The risk paragraph was right, and is the reason C split.** Invention needed
  no backfill at all; survival still does. `docs/invention.html` publishes
  *currency* — what share of each vintage was rung in the window — with strict
  and generous bounds rather than one number, and says plainly that it is not
  survival.
- **Plain Bob Doubles at 5,719 was an undercount.** That figure came from exact
  matches on the method string. With the `schema/005` linkage, which also
  attributes the constituents of spliced performances, it is **8,046**. Any
  method-frequency figure computed before that linkage existed is low, and by
  an amount that varies with how often the method appears in spliced peals.

**Also worth knowing:** "Tolling" appears as the third most common *method* at
4,168 performances, and is not a method at all. Any method-frequency chart must
exclude it or it will be visibly wrong to a ringer.

---

### D. Why People Ring — the footnote corpus

**The idea.** 337,946 footnotes are free text, and they are where the human
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

**Why it suits Gemini.** Classifying 337,946 free-text footnotes into occasion
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
- ~~**The September question.** Association AGMs? Harvest? The end of the
  holiday season?~~ **Resolved: a state funeral.** See option B above. The
  guesses were all about seasonality and the answer was not seasonal at all,
  which is worth remembering the next time a monthly total looks meaningful.

---

## What I would pick

*Written before any of this was built. Left unedited; the outcomes are noted.*

**B first** — cheapest, the findings are already in hand, and the pandemic
recovery plus the September anomaly are publishable now.
→ *Built. "The findings are already in hand" was the wrong reason: two of the
three were wrong, and the work was in checking them rather than in drawing
them. The cheap option was cheap to draw and not cheap to verify, and it is the
verification that produced everything worth reading.*

**A next**, because it is the one that could not be done anywhere else and the
parser has a perfect oracle. The parser is reusable well beyond the picture.
→ *Built — `docs/methods.html`. "Could not be done anywhere else" was
overstated: blue lines are standard in ringing software. What is new is the
comparative view at full scale. The parser was indeed the reusable part.*

**D with care.** The most affecting material in the corpus, and the only option
with an ethical dimension worth pausing over.

**C after the backfill**, not before — the survival claim is not honest on a
four-year window.
→ *Split. Invention (roadmap 8a) needs no backfill —`method_performances` spans
1684–2026 — and only survival (8b) waits. Deferring all of C would have been
wrong.*
