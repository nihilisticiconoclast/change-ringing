# Hypotheses and observations

Every claim this project has tested, what was expected before the measurement,
what the measurement said, and whether the expectation survived.

**The wrong ones are the point.** A record that only lists confirmed hypotheses
is a marketing document: it tells you nothing about how often the guessing works,
which is the only thing that calibrates the next guess. **Twenty-two of the
twenty-six entries below are wrong or wrong in size**, which is worth knowing
before trusting the twenty-fourth.

The first version of this page's own tally was also wrong — it claimed 4 / 5 / 14
against an actual 3 / 4 / 16, because the counts were written by hand rather than
counted. Fixed by counting. That is entry H24 in spirit and it is left here
rather than tidied away.

Retro-filled on 2026-08-15 from `docs/LESSONS.md`, `docs/decisions/`,
`docs/ROADMAP.md`, `docs/IDEAS.md` and the commit history. Entries added going
forward should be written **before** the measurement wherever possible; the ones
below were necessarily reconstructed, and that is marked.

| Verdict | Meaning |
| --- | --- |
| ✅ **Held** | The prediction survived measurement |
| ❌ **Wrong** | The measurement contradicted it |
| 🟡 **Wrong in size** | Direction right, magnitude wrong enough to change what you would do |
| 🔵 **Unresolved** | Measured and still open, or not yet measurable |

---

## About the data

### H1. Linking BellBoard performances to Dove towers will be a hard name-matching problem
**Expected:** fuzzy matching of free-text place names, with adjudication.
**Observed:** BellBoard publishes `dove-tower-id` on every performance. It is an
integer join. ~94% carry it and 99.5% of those resolve.
**❌ Wrong** — and wrong in the useful direction. The Methods Library *is* the
hard case; BellBoard is not. Reconstructed.

### H2. `dove.TowerID` is a tower identifier
**Expected:** one row per tower.
**Observed:** 7,262 rows, 7,249 distinct IDs — 13 towers hold two rings. `towers`
is worse: 15,722 rows, 15,402 IDs, 307 repeating. Neither is a tower register;
both are installation registers.
**❌ Wrong.** Became `docs/decisions/001`. Reconstructed.

### H3. Joining `dove` on TowerID inflates counts by about 11 rows
**Expected:** 11, from an early note in the README.
**Observed:** 19 for `method_performances`, and **227** for `performances`.
**🟡 Wrong in size.** The first figure came from a different query shape and was
carried forward unchecked.

### H4. The orphaned tower references are corruption to be cleaned
**Expected:** bad data.
**Observed:** 124 records citing TowerIDs absent from `dove` — mostly chimes and
tubular bells outside Dove's full-circle scope, plus rings that have left the
ringable list. Legitimate, and a hard foreign key would reject them.
**❌ Wrong.** The fix was a soft reference, not a clean-up.

### H5. Switching `v_first_tower_peals` to the deduplicated projection will recover 179 rows and remove 19
**Expected:** those figures, written into decision 001 as an acceptance test.
**Observed:** **−11 rows, and +38 rows that gained a tower they already
referenced.** Neither predicted number was close: 179 and 19 describe
`method_performances` as a table, while the view is a `LEFT JOIN` over it
filtered to one event type.
**❌ Wrong.** Measure the object you are changing, not the table underneath it.

### H6. A 5% tolerance is needed on the backfill completeness gate
**Expected:** export and search endpoints would differ slightly.
**Observed:** across six week-long windows and 2,588 performances, they agree
**exactly**, every window, difference of zero.
**❌ Wrong.** Tolerance set to 0. A 5% allowance on a 30-day window would have
silently forgiven around a hundred records.

### H7. The replica is a faithful copy of the committed CSVs
**Expected:** yes, it is built from them.
**Observed:** 25,030 committed flag rows had **never been loaded** — the loader
had loops for performances, ringers and footnotes and none for flags. Separately,
the replica sat a full year behind the CSVs after a merge, and the README quoted
the replica.
**❌ Wrong, twice.** Now asserted by `check_csv_agreement`.

---

## About the ringing

### H8. September is the busiest month for ringing
**Expected:** a real seasonal pattern.
**Observed:** 54% of September's excess is one fortnight of 2022 — the mourning
period for Elizabeth II. With national event days removed, September comes 7th.
**❌ Wrong.** Published before it was checked, and corrected on the page.

### H9. Wednesday is the quiet day of the ringing week
**Expected:** from the same early draft.
**Observed:** the trough is Monday once event days are removed.
**❌ Wrong.** Same root cause as H8.

### H10. A handful of national days carry a disproportionate share of ringing
**Expected:** a noticeable effect.
**Observed:** **24 days carry 21.0%** of the 2021–24 corpus.
**✅ Held**, and larger than expected.

### H11. Method invention is a steady trickle of individual ideas
**Expected:** a smooth accumulation.
**Observed:** it arrives in batches. The largest single day is 562 methods first
rung in one peal at Stow Bardolph in 1993; the second is 496 at Cambridge in 1983.
**❌ Wrong.**

### H12. The war years show a gap in the records
**Expected:** patchy reporting.
**Observed:** a hard zero. 1939: 17 methods. Then 0, 3, 0, 0, 4, 0. Church bells
were reserved as an invasion warning and the ringing genuinely stopped.
**✅ Held** — but it is a gap in the ringing, not in the records, which is a
different claim from the one first written.

### H13. Most of the method library is never rung
**Expected:** 81.6% of Major methods never rung — measured over 2021–24.
**Observed:** 70.6% over seven years, **53.9% over thirteen**. Around three
thousand Major methods moved from "never rung" to "rung" on nothing but a wider
window.
**🟡 Wrong in size**, and the most instructive entry here. The claim was never
false; the window was doing half the work. A finding stated without its window
is a finding waiting to change size.

### H14. Some methods are strongly regional
**Expected:** regional repertoires, findable by county concentration.
**Observed:** **one** library method out of 25,066 exceeds 50% concentration in a
single county, against a baseline where the busiest county holds 6.6% of all
ringing. The named repertoire is nationally uniform.
**❌ Wrong** — and the negative is the finding.

### H15. Regional distinctiveness does not exist, then
**Expected:** follows from H14.
**Observed:** it exists and lives entirely outside the Methods Library. Devon
Call Changes is 85% in Devon; Quick Tolling 99% in Lincolnshire; a Cornish
doubles call-change form appears essentially nowhere else.
**✅ Held** once the question stopped requiring the answer to be a method.

### H16. Some conductors ring markedly faster than others
**Expected:** a real and visible "fast ship / slow ship" effect.
**Observed:** controlling for tenor weight, the spread across conductors is 3.62
changes per minute, 12% of the mean — but the **standard deviation between
conductors (0.58) is half the standard deviation within a single conductor's own
peals (1.16)**.
**🟡 Wrong in size.** The effect is real and swamped by noise. Knowing who is
conducting tells you less than the folk belief implies.

### H17. The Sunday band and the peal circuit are two different populations
**Expected:** a bimodal distribution of peal share per ringer.
**Observed:** a single steep decay — median 3.0%, no second mode. Same shape for
towers. Peal involvement does not rise with years ringing. 72% of ringers with
50+ appearances have rung at least one peal.
**❌ Wrong.** See `docs/two_populations.md` and the
[Two Populations](populations.html) page. The question also had to be corrected
first: ordinary service ringing is not in the corpus at all.

### H18. Dove's stated practice night tells you when a tower rings
**Expected:** broad agreement.
**Observed:** the stated night is the busiest non-Sunday night for **31.3%** of
897 testable towers, against 16.7% by chance.
**🟡 Wrong in size** — real signal, about twice chance and no better. Assigned as
Gemini Task 6. A first cut got 15.9% and looked far worse; that was Sunday
service ringing swamping the comparison, which is a confound and not a finding.

---

## About the tooling

### H19. The occasion classifier is 100.00% accurate
**Expected:** per the submitted evaluation, 100% on every one of eleven classes.
**Observed:** the oracle called the classifier under test to build its own ground
truth. Demonstrated by substitution: a classifier returning "birthday" for every
input scores **100.00%** on the same oracle. A read-through of 25 footnotes
suggested roughly 70%.
**❌ Wrong**, and unmeasurable as submitted. Real accuracy is still unknown.

### H20. Missing schema indexes are a cosmetic problem
**Expected:** slower queries.
**Observed:** 591 million rows read in a day, and a single
`SELECT COUNT(*)` costing 396 million.
**❌ Wrong.** Now a hard failure in the integrity checker.

### H21. Merging a stale branch would delete the work main has gained
**Expected:** `git diff --stat main <branch>` showed 2,204,732 deletions.
**Observed:** test-merged three stale branches into a scratch worktree — **zero
deletions, every time.** A two-dot diff is not what a merge does; a three-way
merge keeps what the branch never touched. The real cost is 16–26 conflicted
files and previously rejected work returning as clean additions.
**❌ Wrong**, and asserted in four pull request reviews before being checked.

### H22. Extracting the SQL splitter into one module ends the splitting bug
**Expected:** four copies become one correct copy.
**Observed:** the fifth occurrence was **inside that module**, which stripped only
whole-line comments and declared trailing ones harmless. A semicolon in a
trailing comment split a statement in half.
**❌ Wrong.** No line filter can be correct; the input is a stream with quoted
regions. Fixed by changing the kind of solution, not the number of copies.

### H23. Committed pages are reproducible from the committed data
**Expected:** yes — the whole point of committing the recipe.
**Observed:** two pages produced different bytes on every build from an unchanged
database, via an unseeded `random.sample` and set-iteration order feeding
tie-breaks.
**❌ Wrong.** Fixed and verified byte-identical across two `PYTHONHASHSEED`
values.

### H24. Dove's practice night, refined: does excluding Saturday sharpen it?
**Expected:** the seed measurement gave 31.3% against 16.7% chance over Mon–Sat,
and I recorded it as "real but weak, about twice chance and no better".
**Observed:** excluding Saturday, **43.9% of 1,054 towers** ring most on their
stated night against a 20.0% baseline, with 31.0% of weekday ringing on that one
evening. Saturday is outing and peal-attempt day and was masking the signal.
**🟡 Wrong in size**, in Dove's favour. My seed under-sold the register.
Gemini's PR #15.

### H25. The occasion classifier is around 70% accurate
**Expected:** ~70%, from a 25-footnote read-through, with `civic` the worst class.
**Observed:** **75.5%** overall against a 400-footnote independent oracle, and
`civic` precision **38.8%** — the worst by a distance, with royal-death patterns
swallowing 12 memorial and 5 funeral records.
**✅ Held.** Both the figure and the named failure mode. PR #14.

### H26. The 400-footnote oracle is ground truth
**Expected:** treat the labels as correct and report accuracy against them.
**Observed:** reading 16 of the 98 disagreements, roughly 4 favour the
*classifier*, so the oracle is itself around 93% accurate. It systematically
labels terse milestone forms — `1st blows in Method: 5`, `First on the Treble
for 1` — as `none`.
**❌ Wrong.** 75.5% is measured against an imperfect ruler and should not be
quoted to a tenth of a per cent.

### H27. Ringers find a bell and stay on it for twenty years
**Expected:** the folk model says you progress treble to inside to tenor; the
brief's own bet was the weaker form -- that most ringers settle on one bell
rather than graduate up the ring.
**Observed:** neither. Mean normalised bell position (bell / ring size) is
0.550 in the first tenth of a career and 0.546 in the last -- no upward drift,
no settling. The up / down / stayed split is roughly even (32% / 35% / 33%),
and the median ringer rings across nearly the whole ring over a career
(within-ringer range 0.889). Ringers move around without moving up. Measured
on 5,641 canonical ringers with 50+ tower appearances spanning 5+ years.
**❌ Wrong.** Both the strong model (progression to the tenor) and the weaker
bet (settle on one bell) fail. The replacement -- a band that rings everywhere
and conducts early -- is the sharper finding.

---

## The tally

| | Count |
| --- | ---: |
| ✅ Held | 4 |
| 🟡 Wrong in size | 5 |
| ❌ Wrong | 18 |
| **Total** | **27** |

**Four predictions out of twenty-seven survived intact — 15%.** That is not a comment on
whoever made them — several are mine, several came from experienced ringers'
received wisdom, and several were reasonable readings of a smaller corpus. It is
a comment on how weak intuition is about a dataset nobody has looked at this way
before, and it is the argument for the working rule this project already follows:
**measure it before you write it down, and write down what you expected.**

Two patterns are worth extracting.

**The window is part of the claim.** H13 and H8 are the same failure at different
scales: a real effect measured over too narrow a slice, stated as though the
slice were the world. H13 halved when the corpus tripled.

**The negative result is usually the interesting one.** H14, H16 and H17 all
overturned received wisdom, and in each case the thing that replaced it was
sharper than the thing it displaced — the repertoire is national, conductors
barely differ, and ringing is one community rather than two.
