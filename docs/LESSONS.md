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

### 16. A table with one row per event will answer a different question from the one you asked

`method_performances` looks like a register of methods. It is a register of
*first-performance events*, and a method can have up to fifteen — first tower-bell
peal, first handbell quarter peal, first inclusion in a keyboard peal, each with its
own date, place and band.

Grouping it by place and summing the counts produced "946 methods were first rung in
Ringing Room", which was published in a draft and is wrong by a factor of eight. The
true figure is 115. Collapsing to one row per method — the record matching that
method's own earliest date — also removed the venue from the top sixteen places
entirely, and every place, society and batch figure on the page moved.

Three things make this worth its own entry:

1. **The wrong number was more interesting than the right one**, which is exactly
   when a check gets skipped. "A virtual tower is the third-biggest source of new
   methods" is a better headline than "115 methods, and mostly the platform was used
   for a different kind of first". The second is true and, once the counting was
   right, turned out to be the better finding anyway — the library grew four new
   event types to describe keyboard ringing, of which 1,137 of 1,138 events postdate
   2020. A schema change legible in the data.
2. **The evidence was already on screen.** The event-type breakdown was in the first
   query ever run against that table. Nothing new had to be measured; it just had to
   be read.
3. **The fix needs a tie-break, and the tie-break needs to be deterministic.** Two
   event types can share a method's earliest date at different towers. Picking
   whichever row the database returns first makes the output depend on storage order.

The general form: before aggregating any table, establish what one row *is*. If the
answer is "one row per (thing, kind-of-thing)" then every `COUNT(*)` over it is a
count of pairs, and the wrong denominator is one join away.

### 17. Publish the bound, not the estimate, when the pipeline could be the cause

Of methods first rung in 1975–99, 13.1% were rung at all in 2021–24; for methods
first rung before 1900 it is 72–82%. A real and surprising result — and one that the
project's own method-linkage layer could have manufactured, because that layer
resolves 72.5% of performances and the rows it refuses are disproportionately
*spliced* peals, which is precisely where rare methods appear.

Rather than caveat it in prose, both bounds were computed and both are drawn: the
strict set the resolver was willing to assert, and a deliberately over-generous set
that also counts every method merely *named* in a row the resolver refused. 13.1%
becomes 16.2%; the pre-1900 figure barely moves; the shape survives.

A postscript that makes the point better than the original: the resolver was later
improved — two bugs fixed, coverage 72.2% → 72.5% — and the bounds moved to
13.1%–16.2% from 13.0%–16.4%. A conclusion drawn from the point estimate would
have needed rechecking; one drawn from the interval did not move at all.

The habit: when a finding depends on a component whose error rate you know, compute
the finding twice at the two extremes of that component's behaviour. If the
conclusion changes, you do not have a finding. If it does not, you have a much
stronger one than a point estimate with a footnote — and the gap between the bars is
itself an honest picture of how much the conclusion rests on your own pipeline.

---

## Keeping the work

### 18. If a brief offers both a measurement and an artefact, the artefact is what you get

A brief asked for a labelled dataset with measured precision and recall, and put
visualising it explicitly out of scope. What came back was a visualisation, and no
dataset. The two things ruled out — a page, and a file under `scripts/` — were the
two things built; the CSV was never created on any branch.

The interesting part is not that it happened. It is that **it took a day to
notice**, because the page was good. Its category counts recomputed exactly, it
respected the privacy constraint, and it looked finished. A missing file makes no
impression in review; an attractive artefact positively argues for itself. Nobody
asks "where is the CSV" while looking at a nice violin plot.

Four things follow, all about how the brief is written rather than how the work
was done:

1. **Do not put a measurement and an artefact in the same brief.** If both are
   wanted, they are two tasks, and the measurement goes first. Otherwise the
   artefact absorbs the effort and the measurement becomes the part that gets cut
   when time runs short — which is the wrong way round, because the artefact is
   worthless if the measurement fails.
2. **Say how many files the pull request should contain.** "Exactly two new files
   and no modifications to anything else" is checkable in one glance at the diff.
   "Out of scope: visualising it" is a sentence that can be read and forgotten.
3. **Make the headline number the first thing the PR description must say.** A
   deliverable you have to go looking for is a deliverable that can be quietly
   omitted; one that has to lead the write-up cannot.
4. **Review the diff against the brief's file list, not against the impression
   the work makes.** This is the whole lesson in one line. The check that would
   have caught it on day one is `git log --diff-filter=A -- data/the_file.csv`,
   and it takes five seconds.

There is a matching failure on the reviewing side, which is mine: I read the page,
verified its numbers, corrected its prose, wrote it a limitations panel, and
marked the task shipped — all without once opening the brief to see what had been
asked for.

### 19. Commit the recipe, not the output

What belongs in the repository is whatever cannot be regenerated: schema,
loaders, and every adjudication decision with its reasoning. Raw sources are
re-downloadable and the assembled database rebuilds in 90 seconds, so neither
needs committing.

A 40 MB database *was* committed here, for the defensible reason that the live
one was frozen. It was removed a few hours later — it was heading for GitHub's
100 MB limit, and a binary that changes wholesale on each rebuild stays in git
history forever. Use a Release asset if a large file genuinely needs sharing.

### 20. Recorded SQL must be the SQL that runs

A `queries/` folder that duplicates the real queries is worse than none: it
looks authoritative while going stale. The build script here reads those files
at build time, so the recorded query and the executed query cannot diverge.

### 21. Write decisions down with the numbers in them

Short decision records — the problem, what was measured, what was chosen, what
the acceptance test is — did more good than any amount of code comments. They
also make delegation possible: a spec with an exact expected row count can be
handed to an agent and verified on return.

### 22. Dual-license data and code separately, explicitly

The code here is MIT; the data is CC BY-SA 4.0, inherited from Dove's Guide.
Putting data into an MIT repository does not relicense it, and share-alike
travels with anything substantially derived. Say so in a file next to the data,
including the attribution and the note that changes were made.

### 23. Check the build product against its source, not against a plausible range

A database can be internally perfect and simply out of date. Every index
present, every foreign key resolving, every join identity holding, every row
count inside its expected range — and a whole year missing.

That is not hypothetical. After a backfill merged, the committed CSVs held
106,756 performances and the replica held 96,067, and so did the README,
because the README had been written from the replica. The gap survived a merge
review and two page rebuilds. Nothing was corrupt; the build had simply not been
re-run, and no self-consistency check can see that, because the database is
perfectly consistent with itself.

The check that finds it is the one comparing the build product against the thing
it is built from. Here that is exact rather than approximate, because the CSVs
are committed: 156,513 must equal 156,513, not "be in a plausible range".

Which is the second half of the lesson. **A range on a value that is exactly
knowable is a weaker check wearing a stronger one's clothes.** The same corpus
checker had `performance_flags: (0, 1000)` and the table held 0 — passing, for
as long as the flags existed, because the loader that should have read those
25,030 committed rows had never been written. Nobody looked, because it was
green. Reserve ranges for quantities that genuinely drift, like a live upstream
snapshot, and assert equality everywhere the true number is derivable.

### 24. A silent step is worse than a missing one

Two failures in one afternoon, same shape.

`build_local_db.py` called `run([sys.executable, resolver, ...])` while `run()`
already prepended `sys.executable`, so Python received its own ELF binary as a
source file. The method-linkage step had therefore *never run inside a build* —
the populated tables came from someone running the resolver by hand. What hid it
for so long was that `run()` echoed `cmd` rather than the argv it actually
executed, so the printed command line was correct and the error pointed at
`/usr/local/bin/python3` rather than at the caller. **Echo the command you run,
not the command you were asked to run.**

An agent's pipeline orchestrator did the more direct version:

```python
res = subprocess.run(['python', script], capture_output=True, text=True)
if res.returncode != 0:
    print(f'Error in {script}: {res.stderr}')
```

— print, continue, exit 0, and the caller then announces `SUCCESS: Entire
Pipeline Completed`. A run in which every page failed to build is
indistinguishable, by exit code, from a clean one. An orchestrator whose exit
code means nothing is worse than no orchestrator, because people trust it.

### 25. A gate you have not tried to break is a decoration

The corpus checker arrived with a negative test, which is rare and right. It
still had a hole, and the hole was found by deleting the one object the checker
most exists to defend — `v_towers_unique`, the whole artefact of decision 001 —
from a copy of the database. The run reported `SKIP` and exited 0, because
missing views were treated as an unapplied optional migration.

The generalisation: **for each thing a check claims to protect, delete it and
confirm the check goes red.** Not "does it pass on good input" — it does, that is
easy — but "does it fail on the specific bad input it names in its own
docstring".

Two related traps, both live in the same file. A dead predicate that always
returned `False` sat next to an inlined version implementing a cruder rule than
the dead one's docstring described; the docstring was right and the running code
was wrong, and the crude rule would have turned a correctness fix into a red
build. And the join-identity check joined a hand-written `SELECT DISTINCT
TowerID FROM towers` rather than the view it was written to verify — an inline
equivalent passes happily while the real object is broken. That is lesson 20
again, from the other direction: a check must exercise the object the codebase
uses, not a lookalike.

### 26. When the window changes, the prose does not

Backfilling three extra years moved every figure on the site, and the figures
updated themselves, because they are generated. The *words around them* did not.
One page's standfirst ended with a literal `(2021–2024)` beside counts that had
just become seven years wide, so the sentence was false while looking freshly
built — the worst combination, because the generated numbers beside it vouch for
it. Elsewhere, "44,280 names" and "113,894 footnotes" sat in the shared
navigation module, one stale figure replicated across nine pages by the very
module written to stop figures being replicated across nine pages.

**Any date range or count stated in prose should be computed by the same query
that produced the numbers next to it.** Where a page genuinely does use a
narrower window than the corpus, say which, and say why in the first sentence of
the caveat — the Rhythm page is still 2021–24 on purpose, because its anomaly
rule compares each day against its own neighbourhood and a longer run changes
which days qualify.

There is a finding hiding in this one. "81.6% of Major methods were never rung"
became **70.6%** once the window went from four years to seven: about a thousand
more methods turned out to be in use. The claim was not wrong, but the window
was doing some of the work the claim attributed to the data.

### 27. `git diff main branch` is not what merging does, and the difference is 2.2 million lines

Four pull request reviews said, in writing, that merging a stale branch "would
delete" `site_chrome.py`, two published pages, three schema files and the shared
completeness gate. The evidence was `git diff --stat main <branch>`, which
reported 2,204,732 deletions for the largest of them.

That figure is real and the conclusion drawn from it was wrong. `git diff A B` is
a **two-dot** diff: it compares two trees and counts everything B lacks as a
deletion, including every file A gained after the branch point. A merge is
**three-way** — it consults the merge base, and a file the branch never touched
survives untouched. Test-merged all three branches into a scratch worktree:

    branch                              deletions  conflicts  rejected files re-added
    feature/gemini-footnote-occasions           0         20                        4
    cleanup/repo-audit-and-consistency          0         26                        4
    feature/data-insights                       0         16                        1

**Zero deletions, every time.** The danger was imaginary. The cost was real but
it was a different cost: sixteen to twenty-six conflicted files, and previously
rejected work arriving as clean additions where it looks like a new contribution.

Two things worth keeping from this. First, the safety check written to prevent
the problem checked for the wrong thing, because it was written from the same
misreading — a guard built on a wrong diagnosis guards nothing. Second, the way
out was thirty seconds of `git merge --no-commit` in a throwaway worktree.
**When a claim is about what an operation will do, run the operation somewhere
safe rather than inferring it from a summary of a different operation.**

### 28. The fourth copy of a fix is where it gets written wrong

`build_rhythm_page.py` carried this comment: *"Comments are stripped before
splitting on ';', not after -- splitting first breaks on any semicolon inside a
'--' comment. That bug has now appeared three times in this project."* Three
copies of the correct fix, each with a note saying how often it had recurred.

The CI step written to catch broken SQL then split on `;` inline, and reported
eight healthy queries as syntax errors: `near "81"`, `near "he"`, `near "these"`
— fragments of English prose out of the comments. A fourth copy, in the check
built to catch that class of problem, written by someone who had read the comment
warning about it an hour earlier.

Counting the recurrences in a comment does not stop the recurrence. Extracting
the function does.

Except that extracting it is not sufficient either, because the fifth appearance
was **inside the module written to end the bug**. `sqlfile.py` v1 stripped only
whole-line comments and asserted in its own docstring that trailing ones were
"harmless". They are not:

    AND p.duration NOT LIKE '%m%'   -- 'Nh MM'; the bare '45m' rows are quarters

A semicolon in a trailing comment, splitting the statement in half. The CI check
caught it — the system working — but only after the fix reintroduced the fault it
was written to prevent.

What finally worked was changing the *kind* of solution. Every version up to the
fifth was a line filter, and no line filter can be correct here, because the
thing being parsed is not lines: it is a stream with quoted regions in it. v2 is
a small scanner that tracks whether it is inside a string literal, which handles
the trailing case, the apostrophe case and `'a--b'` together. It ships with four
self-tests, one per shape that has actually broken this repository, runnable as
`python scripts/sqlfile.py`.

**When a bug recurs, the question is not who forgot. It is whether the shape of
the fix can be right.**

### 29. A page that rebuilds differently every time trains people to ignore its diff

Two published pages produced different bytes from an unchanged database on every
build. `occasions.html` drew an unseeded `random.sample` of 2,000 values;
`ringers.html` passed `list(set(...))` into tie-breaks, and Python randomises
string hashing per process, so set order — and the resulting page — changed run
to run.

The direct harm is that no published version could be reproduced. The larger harm
is what it does to everyone's attention: `git status` showed those two files
modified after every rebuild, whether or not anything had changed, so the only
sane response was to stop looking. A real change would have arrived in exactly
the place nobody was reading.

Fixes were one line each — a seeded `Random(...)`, and `sorted()` for `set()`,
with `(-count, key)` tie-breaks. Verified by building twice under different
`PYTHONHASHSEED` values and comparing SHA-256. **Determinism is not a nicety in a
repository that commits its output; it is what makes the diff mean anything.**

### 30. The best submission was the one engineered to be cheap to check

Almost every lesson here is drawn from something going wrong. This one is not.

Over a dozen agent submissions, one stood out — PR #14, the measurement of the
footnote occasion classifier — and it is worth being precise about *why*, because
the reason is reproducible and none of it is about the author being cleverer.

**It cost hours to produce and about twenty minutes to check.** That asymmetry
was not luck. Four choices created it, and a contributor can make all four
deliberately:

1. **It committed the evidence, not just the conclusion.**
   `data/footnote_occasion_labels.csv` — 400 rows, the raw oracle — is in the
   repository. So the first question a reviewer must ask ("is this ground truth
   independent, or is it the classifier's own output again?") was answerable by
   running one script: 98 of the 400 labels disagree with the classifier, so it
   is independent. The predecessor that failed, PR #7, did not commit its sample.
   Its `scratch/oracle_300_raw.json` was referenced and absent, and **that alone
   made its 100.00% unfalsifiable** regardless of the circular-oracle bug behind
   it. Committing the evidence is what converts a claim into something a reviewer
   can attack.

2. **It reported per-class figures, not an aggregate.** "75.5% accurate" is a
   number you can only believe or disbelieve. Eleven rows of precision, recall
   and support are a number you can *recompute* — I did, and all eleven matched
   to the decimal — and they tell you what to fix. The aggregate says the
   classifier is imperfect; the breakdown says `civic` precision is 38.8% and the
   royal-death patterns are eating memorial and funeral records.

3. **It wrote its predictions down before measuring.** A short section listing
   what the author expected, including "civic will suffer severe precision loss".
   That turns a review from "do I trust this?" into "did the stated prediction
   survive?", which is a much cheaper question.

4. **It led with its own worst number and argued against its own usefulness.**
   The recommendation was that `civic` and `practice` counts should not be
   published. A submission that volunteers where it should not be trusted has
   already done the reviewer's most expensive work.

The spectrum across three submissions in one afternoon makes the point better
than the abstraction does:

| | Verification cost | Outcome |
| --- | --- | --- |
| PR #7 | Impossible — sample not committed, oracle circular | Rejected |
| PR #15 | Expensive — every figure had to be re-derived, and the prose turned out to disagree with its own committed query | Merged after rework |
| PR #14 | Twenty minutes — run the committed CSV against the classifier | Merged nearly as-is |

The analysis quality in #15 was excellent; it found something a reviewer's own
seed measurement had missed. It still took an order of magnitude longer to accept,
purely because of how it was packaged.

**This is lesson 1 applied to a deliverable rather than a project.** Choosing work
where checking is far cheaper than producing is the same instinct as *shaping a
submission* so that checking is far cheaper than producing. The second is
something a contributor controls completely, and it is the single highest-leverage
thing an agent can do to get its work accepted quickly.

The brief should ask for it explicitly: **commit the raw evidence, break the
result down far enough to be recomputed, state predictions before measuring, and
say plainly where the result should not be trusted.**

---

### 31. Unifying the markup and leaving the styling behind is half a fix that reads as a whole one

`site_chrome.py` was written because eleven pages had eleven hand-maintained nav
bars and the footers had silently diverged. It generates the nav markup from one
list, `verify_chrome.py` asserts every page's nav is byte-identical, CI runs it,
and it has passed continuously ever since.

The site still had eleven different nav bars.

Every page emitted the same markup and then styled it with its own `.nav-bar`
rule — mono uppercase on one page, mixed-case sans on the next, one bar with
doubled padding, one positioned over a canvas. Clicking between pages, the header
visibly changed shape. The user reported it; no check had, because the checker
was written to compare the thing that had gone wrong last time.

Three things are worth taking from that:

- **A component is its markup *and* its rules.** Extracting one and leaving the
  other creates a construct that looks centralised, is described as centralised
  in its own docstring, and still has eleven authors. That is worse than eleven
  honest copies, because it stops anyone looking.
- **The check inherits the blind spot of the bug that prompted it.** The nav
  drifted, so the check compared navs. The comparison was `re.findall` over
  `<a href=...>` inside `<div class="nav-links">` — it could not have seen a CSS
  difference if one had been painted across the page in red. Ask what *else*
  could differ while this check passes, and check the second thing too.
- **The verifier must read the sources, not only the output.** Comparing the
  built pages to each other cannot catch a divergence that is uniform: eleven
  pages each styling the nav differently is caught, but eleven pages sharing one
  wrong rule is not. `verify_chrome.py` now fails any template or builder that
  declares a nav selector at all, which is a property of the source and does not
  depend on noticing the symptom.

The generalisation is uncomfortable, because this project has several other
"single source of truth" modules: **a single source of truth that governs only
part of the thing it names is a liability, and the part it does not govern is
exactly where nobody will look.** The palette and page-body CSS are still copied
into every template here — roadmap item 31 — and they have already drifted.

---

## Where the predictions are kept

`docs/HYPOTHESES.md` records every claim this project has tested against what was
expected beforehand. Three of twenty-three held intact. The lessons above are
what those twenty failures had in common; the hypotheses page is the raw tally,
kept separately so the hit rate stays visible rather than being smoothed into
narrative.

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
