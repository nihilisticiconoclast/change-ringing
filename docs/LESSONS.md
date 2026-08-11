# Lessons learnt

Written after the first day of building this corpus with three agents — Claude
Code, Mistral Vibe and Gemini CLI — working in parallel on a shared repository.
Kept for the next project rather than this one, so the specifics are here only
as evidence.

Everything below cost something. Where a lesson has a number attached, the
number was measured, not estimated.

---

## Choosing the work

### 1. Pick projects where checking an answer is far cheaper than producing one

This is the single best predictor of whether a project like this will go well,
and it is not the same as "is it a data project".

Over one day I was wrong about: NaN handling, a performance "fix" that saved no
money, a row count (11 vs 19), a join specification that would have made things
seventy times worse, and whether a colleague's dataset was usable. Every one was
disproved in seconds by running a query.

The project never required anyone to be right. It required them to be
**checkable**, which is a far weaker demand. Domains where verification costs
about the same as production — strategy, design, most prose — do not get this
and feel like wading by comparison.

### 2. Well-curated source data is worth more than clever processing

Dove's Guide, the CCCBR Methods Library and BellBoard have been maintained by
people who cared, for decades. That is why `dove-tower-id` exists at all.

**Three separate times a task was planned around inference the source already
answered:**

| Planned as hard | Actually |
| --- | --- |
| Match BellBoard performances to towers by name | BellBoard publishes `dove-tower-id`; ~94% carry it, 99.5% resolve |
| Classify methods into families | The library states `<classification>` on every method set |
| Group methods into naming families | `methods.name` is already a column |

Each was caught by looking at the data before writing the brief. The habit is
now a standing instruction to every agent: **confirm the gap is real before
filling it, and say so.**

---

## Working with multiple agents

### 3. Give an agent an oracle, not just a warning

The clearest result of the day. Two agents, comparable capability, opposite
outcomes:

- **Gemini** was given 1,851 labelled rows and told to score against them before
  trusting itself. Its work held up.
- **Mistral** was given a written warning that the source truncates silently,
  and no way to measure whether it had been truncated. Its backfill captured
  **55,000 rows of a 336,654-row corpus — 16% — and reported success.**

The instrument that would have caught it existed the whole time: BellBoard's
`search.php` reports a result count for any window, in one request. Nobody found
it until the failure had to be adjudicated.

**A brief that names a hazard without supplying the measurement is close to
useless.** If you cannot describe how the agent will know it succeeded, the task
is not ready to hand over.

### 4. Resolve disagreements by measuring, not by arbitrating

When two agents reported counts differing by seven times, the temptation was to
reason about which was more credible. Three HTTP requests settled it instead:
2023 held 25,859 performances, 2024 held 25,267, the full period 336,654.

Cost: about a minute. **When two agents disagree about a quantity, go and
measure the quantity.**

### 5. Boundaries exist so agents can run at once — say them explicitly

The first PR did both agents' briefs in one branch. The work was fine, but it
defeated the point of splitting them. Every brief now carries an explicit "do
not take on the other agent's task", plus a list of files not to touch.

### 6. Give each agent a queue, not a task

Single tasks mean an agent stalls waiting for a new brief. A numbered roadmap —
one task fully specified, the rest deliberately sketched — keeps work flowing.
Sketch the later ones thinly: three tasks here were rewritten or dropped once
the earlier work revealed the source already answered them.

### 7. An agent's data can be right while its prose is invented

A resolution write-up cited "Claremont, TowerID 1563" (does not exist) and
"Lismore, TowerID 10769" (actually Burnham on Crouch, Essex). **The CSV rows
were correct throughout** — only the narrative was wrong, which made the
document read as authoritative while being partly fabricated.

Treat generated prose and generated data as separately trustworthy. Verify every
identifier that appears in a sentence.

### 8. Insist on the whole confidence scale

That same run emitted no `low` band at all, collapsing four levels to three, and
two rows marked `high` were wrong. Since adjudication samples rather than
checking every row, an over-confident row does more damage than an honestly
uncertain one. Ask for calibration explicitly, and check the distribution.

---

## Working with data

### 9. Local testing is weaker than production testing — find out how

Three bugs here were invisible locally and appeared only against the hosted
database:

| Bug | Why local missed it |
| --- | --- |
| NaN never converted to NULL | SQLite silently stores NaN as NULL; the server rejects it |
| Double-quoted SQL string literal | stdlib `sqlite3` accepts it as a string; libSQL rejects it as an identifier |
| `executemany()` at 4.1 rows/s, then stalling | It is a network round-trip problem; there is no network locally |

Two of the three vanished by using **the same client library locally as in
production** — an embedded libSQL connection rather than stdlib `sqlite3`. That
one change turned local testing from an approximation into a real check.

Where a gap remains, write it down rather than claiming coverage you do not
have.

### 10. Latency and cost are different problems, and only one is visible

A batch update took 18 minutes. Batching it into a single statement brought it
to 19 seconds, and it was reported as fixed.

**It read exactly the same 139 million rows.** The metered cost — the thing that
actually mattered — was unchanged. A day's usage hit 591 million row reads
against a database holding 130,000 rows, from two statements that both looked
ordinary.

On any metered system, check the plan (`EXPLAIN QUERY PLAN`) and not the
stopwatch. A `SCAN` inside a correlated subquery means you are paying the
product of two tables.

### 11. A wrong identifier is worse than a missing one

Adjudicating 5,728 tower matches, the operating rule was that a NULL is visibly
unresolved and invites another pass, while a plausible-but-wrong ID silently
corrupts every downstream query and is very hard to notice later.

That justified rejecting 240 matches where the resolver had picked a tower in a
multi-tower town with **no building name to go on** — a guess dressed as a
match. Rejected rows keep their candidates on file, so "rejected" means "not
asserted", not "discarded".

### 12. Check the obvious fix before recommending it

`dove.TowerID` is not unique, so joins fan out. The obvious remedy — "join the
superset table instead" — turned out to inflate results by **1,439 rows against
the 19 it was meant to fix**, because that table is not unique either.

The same investigation found the join was also silently *dropping* 160 records,
which mattered more than the duplication and would never have surfaced from
de-duplication alone. Verify the fix on real data before writing it into a spec.

### 13. Third-party APIs lie in ways that look like success

BellBoard answers sustained querying by truncating the response body and
returning HTTP 200. A run that stops at 16% is byte-for-byte indistinguishable
from one that finished.

Assume any undocumented API throttles. Rate-limit from the start, cache to disk,
and build a completeness check — an expected count from an independent
endpoint — rather than trusting the absence of an error.

Also: the docs are often wrong about themselves. BellBoard's `export.php`
honours `from`/`to`; the plausible-looking `date_from`/`date_to` silently return
zero rather than erroring.

### 14. An aggregate is a hypothesis, and the ranking is the weakest part of it

`docs/IDEAS.md` recorded, as a finding: *"September is the busiest ringing month
(12,067 performances) and nobody knows why."* The count was correct. Everything
else about the sentence was wrong.

**49% of September's performances fall in eleven days of 2022**, between the
death of Elizabeth II and her state funeral. Across the four-year corpus, **24
days carry 21.0% of all ringing**. Remove them and September goes from 1st of
twelve months to 7th; the weekly trough moves from Wednesday to Monday, because
four of the 24 fell on a Monday.

Three transferable points, in increasing order of usefulness:

1. **A total is robust; an ordering is not.** 12,067 was right. "Busiest" was a
   claim about twelve numbers whose gaps were smaller than the contamination.
   Before publishing a rank, check what happens to it when the top few
   contributing days, rows or customers are removed. If the rank changes, report
   the magnitude and not the position.
2. **"Nobody knows why" is a statement about the analysis.** The answer was
   already in the corpus, as free text, in a column nobody had grouped by: the
   most repeated footnote on 9 September 2022 is "In memoriam HM Queen Elizabeth
   II", written independently by hundreds of bands. One `GROUP BY` found it.
   Treat an unexplained pattern as an unfinished query, not as a finding.
3. **Detect outliers by rule, then let the data name them.** The 24 days were
   found by comparing each day with the median of the *same weekday* within six
   weeks either side — same weekday because Sunday is 2.5x Monday, so a plain
   rolling mean flags every Sunday, and median because the thing being detected
   would otherwise inflate its own baseline. Nothing about which days count as
   events was hand-entered; the labels came from the footnotes. That separation
   is what makes the list arguable instead of anecdotal, and the build prints the
   days that fell just below the threshold so the boundary can be inspected.

### 15. The under-normalised column is often the one carrying the information

Two free-text fields did all the work on the Rhythm page, and neither would exist
in a well-designed schema.

**The method field.** "99 Tolling" is ninety-nine strokes of one bell — one per
year of the life being marked. 99 peaks the day after a 99-year-old died, 96 the
day after a 96-year-old, 365 exactly one year after the first lockdown. **No
table in any of the four corpora has an age or date-of-birth column.** A schema
with a `method` foreign key would have rejected "99 Tolling" at load, and the
only place a person's age exists in this data would have been validated away.

**The footnote.** Whether the bells were half-muffled is not a column either. It
is a phrase ringers happen to write. It gives a rate of 73%, 74%, 72%, 74% on
four consecutive Remembrance Sundays against a 5.7% baseline — nobody
coordinates this, there is no return to file, and the practice is reproducible to
within two points. It also distinguishes a funeral from a celebration from a
remembrance without any labelling.

Before normalising a messy text field into codes, check what the mess encodes.
Prefer keeping the raw column alongside a derived one. The corollary for
ingestion work: a loader that rejects rows failing a foreign key is discarding
exactly the records that carry information the schema did not anticipate.

---

## Keeping the work

### 16. Commit the recipe, not the output

What belongs in the repository is whatever cannot be regenerated: schema,
loaders, and every adjudication decision with its reasoning. Raw sources are
re-downloadable and the assembled database rebuilds in 90 seconds, so neither
needs committing.

A 40 MB database *was* committed here, for the defensible reason that the live
one was frozen. It was removed a few hours later — it was heading for GitHub's
100 MB limit, and a binary that changes wholesale on each rebuild stays in git
history forever. Use a Release asset if a large file genuinely needs sharing.

### 17. Recorded SQL must be the SQL that runs

A `queries/` folder that duplicates the real queries is worse than none: it
looks authoritative while going stale. The build script here reads those files
at build time, so the recorded query and the executed query cannot diverge.

### 18. Write decisions down with the numbers in them

Short decision records — the problem, what was measured, what was chosen, what
the acceptance test is — did more good than any amount of code comments. They
also make delegation possible: a spec with an exact expected row count can be
handed to an agent and verified on return.

### 19. Dual-license data and code separately, explicitly

The code here is MIT; the data is CC BY-SA 4.0, inherited from Dove's Guide.
Putting data into an MIT repository does not relicense it, and share-alike
travels with anything substantially derived. Say so in a file next to the data,
including the attribution and the note that changes were made.

---

## The honest summary

None of this made the work error-free. There were three production-only bugs, a
591-million-read day, a failed backfill, a decision spec that had to be
corrected before anyone implemented it, two rounds of rework on the agent split,
and a published finding — the September one — that was wrong for four days before
the analysis that was supposed to illustrate it took it apart instead.

What the setup did was make every one of those **visible and recoverable within
minutes**. That is the property worth reproducing — not the absence of mistakes,
but the speed at which they surface.
