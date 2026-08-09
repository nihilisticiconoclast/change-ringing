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

- `mistral-vibe-bellboard-backfill.md` -- resumable historical backfill runner
- `gemini-method-extension-lineage.md` -- derive extension lineage from notation

Completed and removed: the CCCBR Methods Library loader and the
first-performance location resolution, both landed in PR #1.

One process note from that PR: a single agent did both briefs in one branch.
The work was sound, but it defeated the split -- the boundaries sections exist
so two agents can run concurrently without editing the same files. Both current
briefs say explicitly not to take on the other's task.

## In practice

A typical BellBoard ingestion pass looks like: Vibe opens a PR with the
ingestion script for a new batch -> Claude Code reviews and merges it ->
Gemini runs the actual cross-referencing pass over the resulting data in
one large-context sweep -> Claude Code adjudicates the ambiguous matches
and commits the resolution decisions with a note on reasoning (see
`schema/` migration comments for the expected style: state *why*, not just
*what*).
