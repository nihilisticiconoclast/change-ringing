# Which agent does what, and why

Three agentic coding tools are in use on this project: Claude Code, Gemini
CLI, and Mistral Vibe. All three are terminal-native -- they can run shell
commands, edit files, and (in Vibe's case) open pull requests directly -- so
none of them is boxed out of any task mechanically. The division below is
about where each one's actual strengths line up with a real bottleneck in
this project, not an arbitrary split.

## Claude Code -- schema, orchestration, judgement calls

Use for: schema design and migrations, the entity-resolution *adjudication*
step (deciding whether "J. Smith, Painswick, 1994" and "J. Smith, Bisley,
2019" are the same ringer once candidate matches are surfaced), reviewing
and merging what the other two produce, and maintaining `docs/` as the
project's source of truth.

Why: this is the sustained, multi-session, judgement-heavy work -- exactly
what long-running agentic sessions with persistent memory are suited for,
and where a wrong call (merging two different ringers, or splitting one
ringer into two) is expensive to unwind later. Treat Claude Code as the
project's editor, not just a contributor: it's the right tool for holding
the whole schema and provenance trail in view at once and catching
inconsistencies between what Gemini and Vibe produce.

## Gemini CLI -- large-context ingestion and cross-referencing

Use for: any task that benefits from holding a large volume of source text
in context at once without chunking -- cross-referencing a large batch of
candidate ringer-name matches against each other in a single sweep, or
resolving the CCCBR Methods Library's free-text first-performance locations
against Dove's tower register (4,445 distinct town/county pairs against
7,262 towers -- see `docs/tasks/gemini-location-resolution.md`).

Two caveats learned since this document was first written, both pointing the
same way: check whether the source already carries the identifier before
assigning inference work. Linking BellBoard performances to Dove towers
looked like a large entity-resolution problem and is not one -- BellBoard
publishes `dove-tower-id` on each performance. Classifying methods into
families likewise needs no inference: the CCCBR Methods Library states
`<classification>` explicitly on every method set. Route to Gemini the cases
where the identifier genuinely is absent, which is a smaller set than the
original plan assumed.

Why: Gemini's context window is the largest of the three by a wide margin.
Entity resolution and corpus-linking tasks are exactly the case where
context size is the binding constraint -- the more of the corpus you can
see at once, the fewer false negatives you get from comparing candidates
pairwise instead of against the whole field. Route the *bulk* cross-
referencing work here; route the final adjudication back to Claude Code.

## Mistral Vibe -- bounded coding tasks via pull request

Use for: well-specified, self-contained coding tasks -- writing or fixing
an ingestion script, adding a new index, patching a bug in the migration
script -- dispatched as a PR against this repo rather than a direct push.

Why: Vibe's remote Code Mode is built around exactly this workflow --
isolated cloud sandboxes that open pull requests and integrate with GitHub
natively. That makes it the natural choice for anything that should be
*reviewed* before it lands, which most schema and ingestion-script changes
should be. Don't route open-ended judgement calls here; route them tasks
with a clear definition of done.

## Task briefs

Ready-to-dispatch briefs live in `docs/tasks/`, one file per task. Each states
its deliverables, its boundaries against the other agents' work, and the
known traps in this codebase. Write a new one before dispatching rather than
briefing an agent ad hoc -- the boundaries section is what stops two agents
editing the same files.

Each agent has a **roadmap** rather than a single brief, so work continues
without waiting for a new one to be written each time:

- `mistral-vibe-roadmap.md` -- CompLib ingestion, then an integrity checker
- `gemini-roadmap.md` -- extension lineage, then a name lexicon

Each holds a numbered queue: one task fully specified and active, the rest
sketched. The sketches are deliberately thin, because what a later task should
ask depends on what the earlier one finds -- three times now a task has been
rewritten or dropped after the source turned out to answer it already. Expand
the next task when the current one lands, and keep the standing-constraints
section at the top of each file, since that is the part agents actually reread.

One task per pull request, in order. A single agent once did both briefs in one
branch: the work was sound, but it defeated the split, so both roadmaps now say
explicitly not to take on the other's.

## Claude Code's own queue

Adjudication and merges, as below, plus the work that is neither a bounded
coding task nor a large-context sweep -- schema semantics, and any decision
where being wrong is worse than being slow.

1. **Widen the Rhythm page beyond 2021-24** *(next)*. It is the one page still
   restricted to a window narrower than the corpus, and widening it is analysis
   rather than a rebuild: the anomaly rule compares each day against its own
   neighbourhood, so thirteen years changes which days qualify, and 2020 enters
   as a year of almost no ringing. Expect the answer to move -- the same widening
   took "81.6% of Major methods are never rung" down to 53.9%.
2. **Consolidate the data-quality caveats.** They are currently spread across
   `CONNECTING.md`, `SOURCES.md`, `method_location_resolution.md`, the schema
   headers and several commit messages. Anyone querying the corpus needs them
   in one place.
3. **Method survival, option C's second half.** Unblocked by the completed
   backfill: currency is published on `invention.html`, and survival needs the
   adoption history that thirteen years now provides.
4. **Production load**, once the Turso freeze lifts on **2026-09-01**. Nothing
   in this list touches the live database before then.

Completed: the CCCBR Methods Library loader and location resolution (PR #1),
the location adjudication, the read-cost fixes, the Founder Atlas, method
extension lineage (PR #3), the dedication and place lexicon (PR #4), the
backfill completeness gate (PR #5), CompLib ingestion (PR #6), footnote
occasions as an explicitly unvalidated candidate (PR #7), the corpus integrity
checker (PR #10), ring-level join semantics (decision 001, adopted), and the
**BellBoard historical backfill in full** -- 2012-2024, 293,471 performances,
across PRs #8, #9 and a direct push for 2012-2017.

## What a good submission looks like

Distilled from the one that took twenty minutes to accept when comparable work
took hours — PR #14, the classifier measurement. Full reasoning is lesson 30 in
`docs/LESSONS.md`; the operative version is in both agent briefs.

**Make it cheap to check.** Commit the raw evidence rather than only the
conclusion; break the result down far enough that a reviewer can recompute it;
write predictions before measuring; lead with your worst number; and make every
figure in the prose come from the committed query.

The asymmetry is the point. Producing 400 hand-checked labels takes hours;
verifying them took one script, because the labels were in the repository. The
submission that skipped that step was rejected outright despite reporting a
better-looking result.

## In practice

A typical BellBoard ingestion pass looks like: Vibe opens a PR with the
ingestion script for a new batch -> Claude Code reviews and merges it ->
Gemini runs the actual cross-referencing pass over the resulting data in
one large-context sweep -> Claude Code adjudicates the ambiguous matches
and commits the resolution decisions with a note on reasoning (see
`schema/` migration comments for the expected style: state *why*, not just
*what*).
