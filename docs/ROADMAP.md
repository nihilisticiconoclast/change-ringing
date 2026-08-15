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
| 1 | Backfill completeness gate | Vibe | **Done** — PR #5 |
| 2 | Blue Line Atlas (IDEAS option A) | Claude Code | **Done** — `docs/methods.html` |
| 3 | Footnote occasion classification (option D) | Gemini | **Done** — `data/footnote_occasions.csv`, `docs/footnote_occasions.md` |
| 4 | Rhythm of Ringing (option B) | Claude Code | **Next** |
| 8a | Method **invention** timeline (option C, first half) | Claude Code | Ready — full history already held |
| 8b | Method **survival** — adoption over time (option C, second half) | Claude Code | **Unblocked** — full 2012–2024 adoption history now held |
| 5 | Ring-level join semantics | Vibe | **Done** — `docs/decisions/001-ring-vs-tower-joins.md` |
| 6 | CompLib ingestion | Vibe | **Done** — PR #6 (`schema/005_init_complib.sql`) |
| 7 | Corpus integrity checker | Vibe | **Done** — `scripts/verify_corpus.py` |
| 9 | Ringer identity across decades | Gemini | **Done** — 1.97M ringers clustered across 2012–2024 |
| 10 | Run the backfill to completion | Gemini / Vibe | **Done** — 2012–2024 complete (293,471 performances) |

## Held

| # | Item | Why held |
| --- | --- | --- |
| 11 | Acoustic Landscape (option E) | Needs a ringer's review; getting bell acoustics wrong in public would be spotted instantly |
| 12 | Consolidate data-quality caveats | Worth doing once the integrity checker exists, so the doc and the check agree |

---

## Why this order

**The gate first (1).** Implemented via automated `get_expected_count()` against `search.php`.

**Then the visualisations and analytics (2, 3, 4).** Blue Line Atlas, Why People Ring, and Ringer Constellation are live.

**Correctness work (5, 6, 7).** `v_towers_unique`, `v_dove_towers`, `schema/005_init_complib.sql`, and `scripts/verify_corpus.py` are all in place.

**Option C (8a & 8b).** Invention is ready on 1684–2026 first-performance history; survival is now **unblocked** with 13 years of complete adoption history.

**Where the backfill stands.** Complete. The committed files cover **2012–2024** = **293,471 performances**, **1,969,949 ringers**, and **337,946 footnotes**, with 100% verified completeness per year.

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
