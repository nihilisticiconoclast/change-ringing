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
| 1 | Backfill completeness gate | Vibe | **Urgent** — the run captured 16% and reported success |
| 2 | Blue Line Atlas (IDEAS option A) | Claude Code | **Done** — `docs/methods.html` |
| 3 | Footnote occasion classification (option D) | Gemini | **Shipped** — `docs/occasions.html`; not yet reviewed against the aggregate-only constraint |
| 4 | Rhythm of Ringing (option B) | Claude Code | **Done** — `docs/rhythm.html`; corrected two IDEAS figures |
| 13 | Performance → method linkage | Claude Code | **Done** — `schema/005`; 72.2% of performances linked |
| 14 | Vendor the CDN libraries | Claude Code | **Done** — fixed two live bugs it was hiding |
| 8a | Method **invention** timeline (option C, first half) | Claude Code | **Next** — full history already held |
| 5 | Ring-level join semantics | Vibe | Unblocked — spec in `decisions/001` |
| 6 | CompLib ingestion | Vibe | Queued |
| 7 | Corpus integrity checker | Vibe | Queued |

## After the backfill succeeds

| # | Item | Owner | Why it waits |
| --- | --- | --- | --- |
| 8b | Method **survival** — adoption over time (option C, second half) | Claude Code | Needs adoption history; see below |
| 9 | Ringer identity across decades | Gemini | Present resolution covers 2021–24 only |
| 10 | Run the backfill to completion | Claude Code | Needs the gate, and the freeze lifts 2026-09-01 |

## Held

| # | Item | Why held |
| --- | --- | --- |
| 11 | Acoustic Landscape (option E) | Needs a ringer's review; getting bell acoustics wrong in public would be spotted instantly |
| 15 | Felstead ingestion — 360,000 peals back to the 1800s | **Waiting on permission**, not on code. See `docs/felstead-enquiry.md`: no stated licence, no API, no robots.txt, and several thousand hours of volunteer transcription behind it. The join is verified (`towerbase-id`, 12/12 sampled) and the whole job is ~5,600 requests, so this is ready to start the day there is a reply |
| 16 | Spliced abbreviation expansion | The method resolver leaves 4,348 performances unresolved, 1,711 of them exactly one method short, almost all abbreviations — "Rev Court", "Cambridge SM". Held rather than queued: two rounds took the oracle from 63.6% to 68.0% and the next round is a third tuning parameter. The rows are recorded with their counts, so it can be picked up on evidence |
| 12 | Consolidate data-quality caveats | Worth doing once the integrity checker exists, so the doc and the check agree |

---

## What linkage 13 changed about what can be asked

`performances.method` was free text with no link to the method library, so the
two largest corpora could not be joined at all. 69,368 of 96,067 performances
(72.2%) now carry at least one method link.

The interesting part was the 15,497 performances that name several methods at
once. "Spliced Surprise Major (8m)" is eight methods, listed in `details` as
prose — and the string states how many to find, so **every row checks itself**.
Same shape as the notation parser's `lead_head` oracle, and the same conclusion:
ship what the oracle proves (68.0%), record the rest with the numbers that made
them fail, and do not chase the remainder.

First finding out of it, and it reframes item 8b: **81.6% of the 10,838 Major
methods in the library were not rung once in 2021–24.** At Minor it is 77.2%, at
Triples 85.1%. That is a stronger version of what `IDEAS.md` had as "70% of the
9,169 methods rung in four years were rung exactly once" — the library is mostly
a register of things nobody rings. Whether they are dead or merely dormant is
exactly the survival question, and it still needs the backfill.

---

## Why this order

**The gate first (1).** Everything downstream of BellBoard is currently built
on a corpus that presents as complete and is not. The committed files cover
2021–2024 — 96,067 performances — against a true 336,654 for 2012 onward. Until
a run can prove its own completeness, loading more data just makes the gap
bigger and harder to see.

**Then the two analyses that are already honest (2, 3, 4).** The Blue Line
Atlas and the Rhythm of Ringing both draw only on data that is complete in
itself: place notation for every method, and dates for every performance in the
window. Neither claim depends on the backfill. The footnote work is the same —
113,895 footnotes are all there is, and classifying them does not require more.

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

**Where the backfill actually stands.** Not finished. The corpus holds
2021–2024 = **96,067 performances**, which is **29%** of the 336,654 BellBoard
reports for 2012 onward; all of 2012–2020 is missing, 240,587 performances.
Genuine progress from the original single window of 1,401, but not the archive.

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
