# Roadmap

One list, in the order the work should happen. Per-agent briefs live in
`docs/tasks/`; this is the shape of the whole thing.

Ordering principle: **things that make the corpus trustworthy come before
things that make it interesting**, because an analysis built on a corpus with a
silent gap has to be redone. Two of the items below exist only because a silent
gap was found.

## Now

| # | Item | Owner | State |
| --- | --- | --- | --- |
| 3 | Footnote occasion classification (option D) | **Gemini** | **Dataset landed, measurement still missing** — `data/footnote_occasions.csv`, 337,946 rows, 11 classes with `subject_type`. Merged as an explicitly unvalidated candidate |

| 19 | Measure the occasion classifier | **Gemini** | **Still active, and now the only thing blocking the dataset's use.** PR #7 delivered the classifier and the 337,946-row CSV but its accuracy check was circular — it scored itself against its own output and reported 100.00% |

| 7 | Corpus integrity checker | Vibe | **Merged** 86a00c3 — PR #10, four changes on merge. 49 checks, exits non-zero, negative-tested. Found two live defects on its first run: 25,030 committed flag rows never loaded, and the replica a year behind the CSVs |
| 20 | Load CompLib in full | Vibe | **Next for Vibe** — 86,040 compositions at 25/page is ~3,442 requests; the loader caches, so it is a long job not a risky one |
| 16 | Spliced ellipsis expansion | Claude Code | **Done as far as it honestly goes** — 69.7%, two bugs fixed; the remainder needs a tuned threshold. See Held |
| 21 | Practice night: Dove's claim vs BellBoard's record | **Gemini** | **Next for Gemini** — the cheapest cross-source check in the repo and never done. Measured seed: 31.3% of 897 towers ring most on their stated night against 16.7% by chance. Brief is Gemini Task 6 |
| 22 | A ringing career, from `performance_ringers.bell` | **Vibe** | Queued behind item 20; brief is Vibe Task 7. 1,897,741 rows in a column nothing has ever read; 6,563 ringers with 50+ appearances over 5+ years. Apprenticeship length, whether the treble→inside→tenor progression is real, and the shape of attrition |
| 23 | Quarter ringers vs peal ringers — are they two populations? | **Claude Code** | **Done** — `docs/two_populations.md`. **No.** A single steep decay, median peal share 3.0%, no second mode; same for towers; no growth with experience. 72% of active ringers have rung a peal. The framing had to change first: ordinary service ringing is not in the corpus at all |
| 24 | Conductor speed, controlled for bell weight | **Claude Code** | Landed as `queries/findings/conductor_speed_signature.sql` from Gemini's `feature/data-insights`, bug fixed. Between-conductor variation is **half** within-conductor variation. Open half: separate band, tower and method from the conductor |
| 25 | Normalise the free-text `method` column for regional traditions | **Gemini** | After item 21. `regional_traditions.sql` finds Devon Call Changes at 85% in Devon, but on raw strings, so every count is a lower bound |

### Done

| # | Item | Owner | Where |
| --- | --- | --- | --- |
| 1 | Backfill completeness gate | Vibe | **Merged** 25e2677 — PR #5, three fixes applied on merge |
| 5 | Ring-level join semantics | Gemini (was Vibe's) | **Merged** — `schema/007_init_tower_views.sql`. Verified against the decisions/001 acceptance test |
| 6 | CompLib ingestion | Vibe | **Merged** 4d84c62 — PR #6, no amendments needed. 86,040 compositions available; the `m + methodid` join verified 8/8 |
| 10 | BellBoard historical backfill | Gemini | **Complete** — PRs #8, #9 and the 2012–2017 push. Thirteen years, 2012–2024, **293,471 performances**. Twelve years match `search.php` to the record; 2022 is one short of a count taken today, which is retrospective upstream growth, not a gate failure |
| 2 | Blue Line Atlas (option A) | Claude Code | `docs/methods.html` |

| 4 | Rhythm of Ringing (option B) | Claude Code | `docs/rhythm.html` — corrected two IDEAS figures |
| 8a | Method invention timeline (option C, first half) | Claude Code | `docs/invention.html` |
| 13 | Performance → method linkage | Claude Code | `schema/005` — 77.9% of performances linked, 379,176 links (2012–24 corpus) |
| 16 | Spliced ellipsis expansion | Claude Code | Two resolver bugs fixed; oracle 68.0% → 69.7% |
| 14 | Vendor the CDN libraries | Claude Code | `docs/vendor/` — fixed two live bugs it was hiding |
| 17 | Provenance and caveats on every page | Claude Code | `scripts/site_chrome.py`, checked by `scripts/verify_chrome.py` |
| 18 | Document the orphan `dove_tower_id` values | Claude Code | `decisions/001` |

## Blocked, and on what

| # | Item | Owner | Blocked on |
| --- | --- | --- | --- |
| 10 | Run the backfill to completion | Gemini | **Done** — 2012–2024 committed and verified. Only *production* loading remains, and that waits for the freeze on **2026-09-01** |
| 8b | Method survival — adoption over time (option C, second half) | Claude Code | Item 10. Currency is published on `invention.html`; survival needs adoption history |
| 9 | Ringer identity across decades | Gemini | **Unblocked.** Item 10 is done, so resolution now has thirteen years to work with rather than four — which is what makes co-occurrence matching worth doing at all |
| 15 | Felstead — 360,000 peals back to the 1800s | Claude Code | **A reply from the CCCBR.** Enquiry sent 2026-08-15; `docs/felstead-enquiry.md`. The join is verified and the job is ~5,600 requests, so this starts the day there is an answer |
| 12 | Consolidate data-quality caveats | Claude Code | Item 7, so the doc and the check agree |

## Held

| # | Item | Why held |
| --- | --- | --- |
| 11 | Acoustic Landscape (option E) | Needs a ringer's review; getting bell acoustics wrong in public would be spotted instantly. The r/bellringing post may produce one |
| 16 | Spliced ellipsis expansion *(was "abbreviation expansion")* | **Worked on 2026-08-15 and stopped again, one rung further along.** The name was wrong: measuring the leftovers rather than guessing showed abbreviations are 2% of the shortfall. The two real causes were a bug (nine Little Bob methods absent from the index) and an *ellipsis* — "St Clement's" for "St Clement's College", 471 rows. The bug is fixed; the ellipsis needs prefix matching with a threshold, which is tuning, which is the line. 1,487 rows remain one method short, recorded with their counts |

## Item 19 — not a new task, the missing half of an old one

Full brief: `docs/tasks/gemini-roadmap.md` Task 5.

`docs/occasions.html` shipped and is good. But the Task 4 brief asked for
`data/footnote_occasions.csv` with a hand-labelled 300-footnote oracle, precision
and recall per class, and a `subject_type` distinguishing "in memory of" a person
from "in memory of the old bells" — and it put **visualising it out of scope**,
along with touching `scripts/`.

Checked against the git history: the CSV was never created on any branch, no
sample was labelled, no accuracy was reported, and the only files touched were
`docs/occasions.html` and `scripts/build_occasions_page.py` — the two things
ruled out.

**Why this is a lesson and not a telling-off.** Given an unglamorous measurable
deliverable and an implicit chance to build something visual, the visual thing
got built — and it was good enough that nobody asked where the dataset was for a
day. A missing CSV is invisible in review; an attractive page is not. The fix is
in how the next brief is written, which is why Task 5 asks for exactly two files
and says the PR description must lead with the precision of the largest category.

---

## What 8a found, and the counting trap it nearly published

`docs/invention.html`. 23,874 methods with a first-rung date, 1684–2026.

Three findings worth keeping: **1940–45 is a hard zero** (bells silenced, three
years with no new methods at all, which happens in no other year after 1889);
**methods arrive in batches** (562 in one peal at Stow Bardolph in 1993 — 14% of
the whole collection debuted on a day that introduced 60 or more, so an "invention
rate" is close to meaningless); and **the pandemic produced a new category of
first rather than new methods** (Ringing Room: 1,142 events, 115 debuts, and four
new event types in the library of which 1,137 of 1,138 events are 2020 or later).

**The trap.** The first version of the page claimed a virtual tower was the
third-largest source of new methods, at 946. It was counting first-performance
*events*, and `method_performances` holds up to fifteen per method — first
tower-bell peal, first handbell quarter, first inclusion in a keyboard peal, each
with its own date and place. Collapsing to one row per method took the figure to
115 and removed Ringing Room from the top sixteen places entirely. Every place,
society and batch number was inflated by the same bug.

Worth generalising: **a table with one row per event type per entity will silently
answer a different question from the one asked.** The clue was available before the
page was written — the event-type breakdown was in the very first query run against
that table — and it was not looked at.

**The finding that needed a guard.** Of the 7,645 methods first rung in 1975–99,
only 13.1% were rung at all in 2021–24; for pre-1900 methods it is 72–82%. That
could have been an artefact of the schema/005 linkage, whose 77.9% coverage skews
against exactly the spliced peals where rare methods appear. So both bounds are
published — 13.1% strict, 16.2% counting every method merely *named* in a refused
row — and the shape survives both. It is labelled **currency**, not survival: four
years is a short window, and the real question needs the backfill.

---

## What linkage 13 changed about what can be asked

`performances.method` was free text with no link to the method library, so the
two largest corpora could not be joined at all. 228,478 of 293,471 performances
(77.9%) now carry at least one method link.

The interesting part was the 15,497 performances that name several methods at
once. "Spliced Surprise Major (8m)" is eight methods, listed in `details` as
prose — and the string states how many to find, so **every row checks itself**.
Same shape as the notation parser's `lead_head` oracle, and the same conclusion:
ship what the oracle proves (69.7%), record the rest with the numbers that made
them fail, and do not chase the remainder.

First finding out of it, and it reframes item 8b: **81.6% of the 10,838 Major
methods in the library were not rung once in 2021–24.** At Minor it is 77.2%, at
Triples 85.1%. *(Re-measured as the corpus grew: 70.6% at seven years, **53.9%
at thirteen**. The direction holds and the size does not — three thousand Major
methods moved from "never rung" to "rung" on nothing but a wider window. Quote
the window with the number.)* That is a stronger version of what `IDEAS.md` had as "70% of the
9,169 methods rung in four years were rung exactly once" — the library is mostly
a register of things nobody rings. Whether they are dead or merely dormant is
exactly the survival question, and it still needs the backfill.

---

## Why this order

**The gate first (1).** Everything downstream of BellBoard is currently built
on a corpus that presents as complete and is not. *(Resolved: the gate landed
in PR #5, and every year since has been accepted only on an exact match with
`search.php`. The committed files now cover 2012–2024 — 293,471 performances —
against a true 336,689 for 2012 onward.)* Until a run can prove its own
completeness, loading more data just makes the gap bigger and harder to see.

**Then the two analyses that are already honest (2, 3, 4).** The Blue Line
Atlas and the Rhythm of Ringing both draw only on data that is complete in
itself: place notation for every method, and dates for every performance in the
window. Neither claim depends on the backfill. The footnote work is the same —
337,946 footnotes are all there is, and classifying them does not require more.

**What item 4 turned up, and why it changes how the rest should be read.** The
Rhythm page was queued as the cheap one — "the findings are already in hand".
Two of the three were wrong. September was not the busiest ringing month for any
reason to do with September: 49% of its performances fall in the eleven days
between the death of Elizabeth II and her funeral, and the corpus said so itself
in the footnote text. Wednesday was not the weekly trough either. **24 days
carry 21.0% of four years of ringing**, and any monthly or weekday aggregate
computed without excluding them is measuring the news.

Two consequences for the work still queued:

- Every aggregate over `perf_date` in this project should now say whether those
  24 days are in or out. `queries/rhythm/01_daily_profile.sql` returns them;
  `scripts/build_rhythm_page.py` finds them by rule at 3.5x the same-weekday
  median. Item 7, the corpus integrity checker, is the natural place to make
  that a standing check rather than a habit.
- The general lesson is not "watch for outliers". It is that the explanation was
  already in the corpus as free text and no derived table would have held it.
  Two under-normalised columns — the method field and the footnote — carried
  everything worth reading on that page, including a person's age, which has no
  column anywhere in four corpora. Worth remembering before normalising
  anything away in item 6.

**Correctness work in parallel (5, 6, 7).** Independent of the analyses and
safe to run alongside.

**Option C splits, and only half of it waits.** Checked rather than assumed:

- **Invention (8a) is ready now.** `method_performances` spans **1684–2026**
  with 30,746 first-performance records — 16,442 of them since 2000, 8,961 in
  1975–99. When methods were invented, by whom and where, is complete history.
  No backfill required.
- **Survival (8b) is not.** "Rung once, therefore a dead end" cannot be
  supported on 2021–24: a method rung once in that window may have been rung
  fifty times in 2015. That needs adoption history, which is what the backfill
  supplies.

**Ringer identity across decades (9) also waits**, for the same reason —
matching is far more powerful across thirty years than within four.

**Where the backfill actually stands. Finished.** The corpus holds 2012–2024 =
**293,471 performances**, against 293,472 that `search.php` reports for the same
range — one record, added upstream after 2022 was fetched. That is the whole of
BellBoard's near-complete era, from an original single window of 1,401.

The thing to carry forward is what the width bought. "81.6% of Major methods
were never rung" became 70.6% at seven years and **53.9% at thirteen**. A window
is a parameter of a finding, not a detail of its provenance, and this corpus is
now wide enough that the parameter stops doing most of the work.

---

## The four visualisation options, and where they went

From `docs/IDEAS.md`, with what actually happened:

- **A · Blue Line Atlas** — built. 20,679 methods drawn at Minor through
  Maximus, from notation verified against the library's own `lead_head`.
  Required a place-notation parser (`scripts/notation.py`), which turned out to
  be the reusable part.
- **B · Rhythm of Ringing** — built, and it was not the cheapest in the end.
  Sunday 23,648 / Saturday 19,378 hold up; the September and Wednesday figures
  did not survive contact with the data, and the page is built around the
  correction. The pandemic recovery, 16,729 → 28,212, stands. The result worth
  keeping is that what was rung — tolling, half-muffled — separates national
  occasions into celebration, remembrance and death without being told to.
- **C · Invention and Survival** — splits. Invention is ready now on complete
  1684–2026 first-performance history; survival waits for adoption history from
  the backfill. Deferring the whole of C would have been wrong.
- **D · Why People Ring** — with Gemini now. "With care" is a scoping
  constraint, not a delay: 7,345 footnotes are memorials and 3,975 mention
  funerals, written as tributes by people who did not anticipate republication,
  and birthday footnotes name living individuals and imply their ages (1,843
  mention "80th"). Aggregate classifications are the deliverable; no named
  individuals in the output, and no named person's memorial quoted as an
  illustration. The analysis itself is unaffected.
- **E · Acoustic Landscape** — held pending review by someone who rings.

## Standing note on the parser

`scripts/notation.py` was written for the atlas and is more broadly useful:
place notation in, rows out, verified on 24,404 of 25,066 methods (97.4%). The
662 failures concentrate at odd stages — 168 at Cinques, 129 at Doubles, 108 at
Caters — and at Minor and Major, the stages most ringing happens at, it agrees
with the library on over 99.7%. It was **not** pushed to 100%: the remaining
failures are characterised by stage rather than chased, because a parser that
tells you precisely which cases it cannot handle is more useful than one that
claims everything.

This removed a queued task from Vibe's roadmap rather than duplicating it.
