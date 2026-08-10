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
| 3 | Footnote occasion classification (option D) | Gemini | **Active** |
| 4 | Rhythm of Ringing (option B) | Claude Code | **Next** |
| 5 | Ring-level join semantics | Vibe | Unblocked — spec in `decisions/001` |
| 6 | CompLib ingestion | Vibe | Queued |
| 7 | Corpus integrity checker | Vibe | Queued |

## After the backfill succeeds

| # | Item | Owner | Why it waits |
| --- | --- | --- | --- |
| 8 | Invention and Survival (option C) | Claude Code | A survival claim on four years is not honest |
| 9 | Ringer identity across decades | Gemini | Present resolution covers 2021–24 only |
| 10 | Run the backfill to completion | Claude Code | Needs the gate, and the freeze lifts 2026-09-01 |

## Held

| # | Item | Why held |
| --- | --- | --- |
| 11 | Acoustic Landscape (option E) | Needs a ringer's review; getting bell acoustics wrong in public would be spotted instantly |
| 12 | Consolidate data-quality caveats | Worth doing once the integrity checker exists, so the doc and the check agree |

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

**Correctness work in parallel (5, 6, 7).** Independent of the analyses and
safe to run alongside.

**Survival claims last (8, 9).** Both need history. A method rung once in
2021–24 may be a century-old standard having a quiet spell, and ringer identity
matching is far more powerful across decades than within four years. Doing
these early would produce plausible, publishable, wrong answers.

---

## The four visualisation options, and where they went

From `docs/IDEAS.md`, with what actually happened:

- **A · Blue Line Atlas** — built. 20,679 methods drawn at Minor through
  Maximus, from notation verified against the library's own `lead_head`.
  Required a place-notation parser (`scripts/notation.py`), which turned out to
  be the reusable part.
- **B · Rhythm of Ringing** — next, and the cheapest. Sunday 23,648 /
  Saturday 19,378 / Wednesday 8,377; September the busiest month at 12,067 with
  no explanation yet; and the pandemic recovery visible as 16,729 → 28,212.
- **C · Invention and Survival** — deferred behind the backfill, on honesty
  grounds rather than difficulty.
- **D · Why People Ring** — with Gemini, with an explicit constraint that the
  output is aggregate: 7,345 of those footnotes are memorials for real people.
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
