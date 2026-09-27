# Roadmap

One list, in the order the work should happen. Per-agent briefs live in
`docs/tasks/`; this is the shape of the whole thing.

Ordering principle: **things that make the corpus trustworthy come before
things that make it interesting**, because an analysis built on a corpus with a
silent gap has to be redone. Two of the items below exist only because a silent
gap was found.

## How items are referenced

Every item has an ID that is unique across all three roadmaps:

| Prefix | Register | Holds |
| --- | --- | --- |
| `R-nn` | `docs/ROADMAP.md` | the central register of work — what the project is doing |
| `G-nn` | `docs/tasks/gemini-roadmap.md` | Gemini's briefs |
| `V-nn` | `docs/tasks/mistral-vibe-roadmap.md` | Mistral Vibe's briefs |

All three registers used to number from 1, so "item 9" named three different
pieces of work and a report that "item 9 was committed to main" could not be
checked without first asking which document was meant. It also hid a real defect:
Gemini's summary table had numbered the backfill as its task 6, which pushed
every task below it one out of step with its own briefs — so the table said task
7 was practice night while the brief said task 7 was the method column.

**Always write the prefix.** An agent brief states which `R-` item it delivers;
`scripts/verify_docs.py` asserts that IDs are unique, that no ID names two
different items, that every reference resolves, and that a row under "Now" is
still work to do rather than a finished one nobody moved down.

Numbers were kept as they were rather than renumbered, so every existing
reference in a commit message or pull request still points at the same work.


## Now

| # | Item | Owner | State |
| --- | --- | --- | --- |
| R-37 | **SEARCH** — is the compositional corpus mostly dead paper? | **Claude Code** | After R-36. 86,054 compositions exist; the method page already showed ~54% of Major methods go thirteen years unrung. The composition-level question is sharper but needs care: with no composition ID on performances, the answerable form is *by composer and by method and by length*, not "was this exact composition rung". State that limit in the question, not in a footnote |
| R-38 | **VISUALISATION** — the composers | **Claude Code** | After R-37. A new population: **2,542 composers**, and the distribution is extraordinary — Robert D S Brown has **11,195 compositions, 13% of the entire library**, Donald F Morrison 8,146. Does prolificacy predict adoption? Follow the house idiom, and note that `date_composed` is only **17.8%** populated, which rules out the obvious historical-trend view before anyone builds it |
| R-39 | **FIX** — the removal / anonymisation route | **Claude Code** | Was R-35, restated. GitHub Pages is static and cannot accept a form post, so a `mailto:` page is the fit — private, no third party, no external request. **The link is the easy half:** honouring a request needs a committed suppression list every builder consults, or the next `rebuild_all.py` reinstates the person, and nothing here can remove them from BellBoard. Say that on the page rather than implying more |
| R-41 | **JOIN** — normalise composer names properly | **Gemini** | After R-40, and **re-scoped now that R-36 has measured the crude key rather than guessed at it**. First-initial-plus-surname resolves 57,249 performances at 99.80% precision where checkable — so the job is no longer "find out how bad it is" but "beat a known number". Two concrete targets, both from `docs/composer_bridge.md`: the **2,303 no_key_match** performances, composers who appear in the belfry and not in the library, and the **2,249 initialisms** (`BEW`, `MBD`) which R-36 deliberately refused to guess — an evidenced expansion using composer repertoire is a real contribution, a plausible guess is not. The 24 keys covering more than one person are the hard core, and `data/composer_bridge_adjudication.csv` is 69 rows of labelled ground truth to test against. Report where you are wrong, as before |
| R-49 | **FIX** — the published occasions page uses a second, unmeasured classifier | **Gemini** | Found while reviewing PR #30. `docs/occasions.html` is built by `build_occasions_page.py`, which carries its **own** `CATEGORIES` regex dict and never calls `classify_footnote_occasions.py`. Its `Royal / National` bucket is still `\b(jubilee\|coronation\|queen\|king\|royal\|majesty\|accession\|platinum\|remembrance\|armistice)\b` — bare `royal`, bare `queen`, bare `remembrance`, the exact over-broad pattern R-43 just fixed in the other classifier. So **the only occasion classifier that has ever been measured is the one the site does not use**, and the published page gets no benefit from R-43. Point the page at the measured classifier and rebuild, or measure the page's own dict — but not two of them |
| R-50 | **TEST** — nothing catches a page whose figures are stale | **Claude Code** | The half R-42 does not reach, and the reason the 2026-08-29 health check found 11 of 13 pages publishing figures the pipeline no longer produced. R-42's snapshots mask numbers on purpose, so a page with perfect structure and last month's counts passes everything. Needs a freshness check: rebuild and compare, or assert published figures against the database at build time. Cheap version first — a single derived count per page, checked |
| R-51 | **FIX** — decide whether the hosted database returns at all | **Claude Code** | The freeze was dated 2026-09-01. That date is now removed rather than left to expire, because the question changed: measured on 2026-08-29, **nothing reads Turso**. The site is static and makes zero external requests, both sync workflows are dispatch-only with their crons commented out, the auth token is revoked, and every corpus is committed so the replica rebuilds from the repository. The productive phase of this project — CompLib, the composer bridge, careers, regional traditions, all 14 pages — happened entirely without it. **What it would buy** is the one thing static files cannot: letting someone query the corpus without cloning ~200 MB. That is in the project's own framing and is the honest argument for keeping it. **Two consequences if it goes:** the libsql driver loses its stated rationale (`db.py` keeps it locally because it rejects SQL `sqlite3` accepts — verified, real, but a check *for production*), and **R-45 inverts** — consolidate onto stdlib `sqlite3` rather than `db.py`, which is also the smaller change at 28 scripts against 11. Deferred deliberately; the constraint now reads "dormant, no date" everywhere so it cannot go stale on its own |
| R-54 | **TEST** — make the definitions layer binding, and migrate the callers | **Gemini** | After R-53, and it lands **with** the migration rather than after it. `scripts/verify_semantics.py` fails any script or recorded query that hardcodes a peal or quarter threshold outside `semantics.py` — exactly the shape of `verify_chrome.py`, which fails any page declaring its own nav CSS and is why there is one nav and not fourteen. Then move all 36 call sites onto it. **Without the check this is worse than nothing:** a definitions module half the callers ignore is a second source of truth, and two are worse than fourteen scattered ones because one of them looks authoritative. Negative-test it, as everything here is |
| R-55 | **JOIN** — an MCP server over the semantic layer | **Claude Code** | After R-54, and **not before** — a server built on scattered definitions hands an LLM the job of defining "peal", and it will invent one confidently in prose indistinguishable from the reviewed figures. Tools are **measures, not SQL**: each returns the definitions it used alongside the numbers. The recorded `queries/findings/*.sql` become named tools directly, so a model asked about conductor speed can only return a figure that went through review — this project's central rule turned into an interface. A raw SQL escape hatch is allowed but gated: read-only, forced `LIMIT`, statement-interrupt budget, `EXPLAIN QUERY PLAN` refused on a large-table `SCAN`, results labelled ad hoc. **Two corpus-specific hazards:** 337,946 footnotes were written by the public, so any tool returning that text is a prompt-injection surface and must say so in its own description; and an MCP tool is a new publication route for named individuals, so it must consult R-39's suppression list or it reinstates anyone who asked to be removed |
| R-56 | **INTERPRETATION** — re-derive every published figure against the layer | **Claude Code** | After R-55. Rebuild every page and document through `semantics.py` and record which figures moved and why. Some will: the 848 boundary cases are 1.6% of the peal population and R-24's query is on the minority side of them. **This is not bookkeeping.** If nothing moves, the layer bought consistency and nothing else, and that should be published as plainly as a correction would be. If figures do move, the list of them is the argument that the work was worth doing |
| R-44 | **TEST** — negative tests for `verify_corpus.py` | **Vibe** | Next for Vibe, and it follows directly from PR #26. Your CSV-agreement check reported SKIP when a CSV was absent without looking at the table, so 86,054 uncommitted rows passed silently; I fixed that one. **The other 50 checks have never been tried against a database that should fail them.** Break each deliberately, confirm it fails, and record which ones could not be broken — those are the decorations |
| R-45 | **FIX** — one database access path (was R-28) | **Vibe** | After R-44. `classify_footnote_occasions.py` and `fetch_and_export_bellboard.py` use stdlib `sqlite3` while ingestion uses `db.py`/libsql, and sqlite3 accepts SQL that libSQL rejects — so a script tested one way is not tested for the other. Two of the three production-only bugs in `docs/LESSONS.md` were exactly this. `db.py`'s docstring explains why. **Blocked on R-51:** this item's rationale is that libSQL rejects SQL `sqlite3` accepts, which matters because production is libSQL. If the hosted database is retired the right direction reverses, so do not start until R-51 is settled |
| R-46 | **JOIN** — method adoption over time (was R-8b) | **Vibe** | Unblocked: R-10 is done, so there are thirteen years of adoption history rather than four. `invention.html` publishes when a method was *first rung*; this is the second half — what happens **after**. Does a method get taken up, spike and vanish, or never spread? The window matters enormously here, as the 81.6% → 53.9% correction showed |
| R-47 | **INTERPRETATION** — the specialisation measures #18 got right | **Vibe** | The open half of R-22, both taken from your own PR #18 which did them better than #19: a **most-used-bell share** as a direct specialisation measure (`≥50% of appearances: 8.5%`), and attrition at a **fixed horizon from each ringer's own first appearance** rather than against one calendar line. The second is the better construction — a fixed 2020 line gives a 2013 cohort seven years to disappear and a 2019 cohort one |
| R-48 | **FIX** — the replica is not reproducible from committed inputs, and it has now broken something | **Vibe** | After V-9, and **widened**: this is no longer only about methods. `build_local_db.py` fetches **two** upstreams live with nothing committed — `ingest_methods.py` downloads the CCCBR XML, and `fetch_dove_csvs.py` downloads Dove. Neither is pinned, so two clones a week apart get different corpora with nothing in the history to explain it: the library held 25,055 methods when the pages were built and 25,066 a fortnight later, which is why `methods.html` moved from 20,668 blue lines drawn to 20,679. **The Dove half has now caused a real failure.** A fresh rebuild on 2026-09-27 fails `verify_corpus.py`: 9 adjudicated links cite TowerID **25219**, which `data/method_location_adjudication.csv` resolved against Dove when it was adjudicated and which Dove has since removed. The adjudication was correct when made and is orphaned by a deletion nobody here controls. So the fix is the R-20 pattern applied twice: commit both sources the way `data/complib/*.csv` is committed, record each one's fetch date and SHA-256 in `data/SOURCES.md`, make the committed copy the default and the live download an explicit flag, and have `verify_corpus.py` check the database against them — **failing when a source is missing but its table is populated**, which is the exact hole I fixed in your PR #26 version. An adjudication must stay resolvable against the snapshot it was made on |
| R-24 | Conductor speed, controlled for bell weight | **Claude Code** | Open half: separate band, tower and method from the conductor. The first half landed as `queries/findings/conductor_speed_signature.sql` (from Gemini's `feature/data-insights`, bug fixed) and found between-conductor variation is **half** within-conductor variation — but a conductor who rings mostly with one band at one tower is not distinguishable from that band and that tower, so the figure is not yet a conductor effect |
| R-27 | Make CI able to catch a stale replica | **Claude Code** | Mine. `check_csv_agreement` is the check that found a year-old replica, and CI cannot run it because building the database needs network and ~15 minutes. A small committed fixture database, or a CSV-only row-count assertion, would close the gap without the build |
| R-34 | Three large artefacts committed at the repository root | **Claude Code** | Mine, pending a decision. `temp.js` (1.2 MB) and `data/search_results.json` (1.2 MB) are near-duplicates of each other, and `docs/invention.html` embeds the same payload a third time; `test.py` is empty; `screenshot.png` and `screenshot2.png` sit at the root. `.git` is now 149 MB. Nothing has been deleted — see lesson 19, commit the recipe not the output, and `export_compositions.py` is the recipe |
### Done

Finished work stays here in full, with what it found and what was corrected on
merge. "Now" holds only what is still to do — a row that has been delivered
moves down, so the length of the top table is the size of the queue.

| # | Item | Owner | Where it landed, and what it found |
| --- | --- | --- | --- |
| R-1 | Backfill completeness gate | Vibe | **Merged** 25e2677 — PR #5, three fixes applied on merge |
| R-5 | Ring-level join semantics | Gemini (was Vibe's) | **Merged** — `schema/007_init_tower_views.sql`. Verified against the decisions/001 acceptance test |
| R-6 | CompLib ingestion | Vibe | **Merged** 4d84c62 — PR #6, no amendments needed. 86,040 compositions available; the `m + methodid` join verified 8/8 |
| R-2 | Blue Line Atlas (option A) | Claude Code | `docs/methods.html` |
| R-4 | Rhythm of Ringing (option B) | Claude Code | `docs/rhythm.html` — corrected two IDEAS figures |
| R-8a | Method invention timeline (option C, first half) | Claude Code | `docs/invention.html` |
| R-13 | Performance → method linkage | Claude Code | `schema/005` — 77.9% of performances linked, 379,176 links (2012–24 corpus) |
| R-14 | Vendor the CDN libraries | Claude Code | `docs/vendor/` — fixed two live bugs it was hiding |
| R-17 | Provenance and caveats on every page | Claude Code | `scripts/site_chrome.py`, checked by `scripts/verify_chrome.py` |
| R-18 | Document the orphan `dove_tower_id` values | Claude Code | `decisions/001` |
| R-3 | Footnote occasion classification (option D) | **Gemini** | **Dataset landed and now measured at 75.5% (item 19)** — `data/footnote_occasions.csv`, 337,946 rows, 11 classes with `subject_type`. Merged as an explicitly unvalidated candidate |
| R-19 | Measure the occasion classifier | **Gemini** | **Done** — PR #14, `docs/footnote_occasion_accuracy.md`. A genuinely independent 400-footnote oracle: **overall accuracy 75.5%**, and every per-class figure reproduced exactly on merge. `civic` precision is 38.8%, confirming the royal-death patterns swallow memorial and funeral. Open: the oracle itself is ~93% accurate and systematically mislabels terse milestone forms |
| R-7 | Corpus integrity checker | Vibe | **Merged** 86a00c3 — PR #10, four changes on merge. 49 checks, exits non-zero, negative-tested. Found two live defects on its first run: 25,030 committed flag rows never loaded, and the replica a year behind the CSVs |
| R-20 | Load CompLib in full | **Vibe** | **Done and reproducible** — PR #26. 86,054 compositions and 186,464 method-definition rows, the full walk of all 3,443 pages of `/composition/search`, matching the API's `count` to the record. Committed as `data/complib/*.csv` (49 MB) and replayed by `build_local_db.py`, so a fresh clone builds them — **verified by rebuilding the replica from scratch**, not by reading the diff. `verify_corpus.py` gained CSV-agreement checks, so a stale or partial load now fails the build. The `/rows` enrichment pass was deliberately scoped out: one request per composition, ~86k requests |
| R-21 | Practice night: Dove's claim vs BellBoard's record | **Gemini** | **Done** — PR #15, `docs/practice_night.md` and `docs/practice.html`. 43.9% of 1,054 towers ring most on their stated night Mon–Fri, against 20.0% by chance; 27.3% Mon–Sat. Excluding Saturday is what makes the signal visible. Merged with every figure re-derived from the recorded query |
| R-22 | A ringing career, from `performance_ringers.bell` | **Vibe** | **Done** — PR #19, `docs/careers.html` and `docs/ringing_careers.md`. **The folk progression is not there.** Mean normalised bell position 0.551 early career, 0.547 late: no upward drift — and no settling either, the median ringer's range across a career is 0.889 of the ring. Every figure reproduced exactly on merge. One correction: "72.5% conduct a peal" was 72.5% conducting *anything*; peals are 19.8% and a median wait of 37 rather than 11. The result is unchanged by PR #22 resplitting 1,898 identity clusters, which is now stated on the page. Three near-identical PRs were submitted (#17, #18, #19). **Open half, both taken from #18, which did them better:** a most-used-bell share as a direct specialisation measure, and attrition at a fixed horizon from each ringer's own first appearance rather than against one calendar line — a fixed 2020 line gives a 2013 cohort seven years to disappear and a 2019 cohort one, so part of the trend down that column is the construction |
| R-23 | Quarter ringers vs peal ringers — are they two populations? | **Claude Code** | **Done** — `docs/two_populations.md`. **No.** A single steep decay, median peal share 3.0%, no second mode; same for towers; no growth with experience. 72% of active ringers have rung a peal. The framing had to change first: ordinary service ringing is not in the corpus at all |
| R-25 | Normalise the free-text `method` column for regional traditions | **Gemini** | **Done** — PR #21, `docs/regional_traditions.md`. **The practice is Cornwall's; only the name is Devon's.** A quarter of everything Cornwall reports — 25.45% — is call changes, 3.3× the next county; Devon is fourth at 5.37%. Merged with three corrections: the 400-row "hand-labelled" oracle was bootstrapped from the classifier and disagreed with it on **1 row in 400**, so its F1 = 1.00 measured nothing (replaced with 200 genuinely independent labels, 98.5%); the denominator divided by the national total, which ranks counties by how much they report rather than by tradition, and correcting it *reversed* the tolling result — Northamptonshire, not Lincolnshire; and the recorded SQL joined a table that existed nowhere, so it could not be run at all |
| R-26 | A real test suite | **Gemini** | **Done** — PR #27. 36 unit and oracle tests in `tests/` (39 now), run by `scripts/run_tests.py`, in CI and in `rebuild_all.py`. **Negative-tested on merge:** inverting one expansion rule in `notation.py` fails 26 of the 36, so the suite can actually fail — which is the only thing that makes a passing suite mean anything. Tests are cwd-independent (each file sets its own path; verified by running from `/tmp`). Assigned to Vibe, delivered by Gemini. Open: no golden-file test for the page builders, so a builder that silently changes a page still passes |
| R-28 | One database access path | **Vibe** | **Superseded by R-45**, which carries the same work. Restated there rather than renumbered, so the reason it matters — two of the three production-only bugs in `docs/LESSONS.md` were this exact fault — is not lost |
| R-30 | Landing page, and one nav for the whole site | **Claude Code** | **Done.** From Gemini's PR #20. The nav bar is now styled in `site_chrome.py` and nowhere else, and `verify_chrome.py` fails any template or builder that declares a nav rule — see the note below on why the first version of that module was only half a fix. The landing page is rebuilt in the site's own idiom, with a hero drawn from the corpus |
| R-31 | The rest of the page CSS is still copied eleven times | **Gemini** | **Done.** Base design tokens, typography, `.wrap` (1200px), `.eyebrow`, `header`, `h1`, `.figures` and `section` rules consolidated into `site_chrome.py` (`BASE_CSS`), enforced across all 13 pages by `verify_chrome.py` (`SHARED_SELECTORS`), and removed from all templates/builders |
| R-9 | Ringer identity across decades | Gemini | **Done — moved out of Blocked.** Delivered as PR #22 and merged in `ff1b67d`: 70,032 raw names over the full 2012–24 corpus resolved to **56,340** canonical entities, with a middle-initial anti-conflation guard that resplit 1,898 clusters and dropped the largest from 9 names to 7. Accuracy is still **not measured** — that remains the open half — but the resplit doubles as a robustness test, and the careers finding is unchanged by it to three decimals, which is on `docs/careers.html` |
| R-32 | `invention.html` is the only page that phones out | **Gemini** | **Done** — PR #25. `vis-network` 10.1.1 vendored to `docs/vendor/` alongside the four libraries already there, licence and SHA-256 recorded in `docs/vendor/README.md`. **The site now makes zero external requests from any of its 13 pages.** Verified in Chromium: `vis` loads, no failed requests, no console errors, and the graph draws — 848×517 canvas, composition table and blue-line panel all rendering, where before the request was reset and nothing was drawn. The page also degrades with a message now instead of leaving a blank. One fix on merge: the viewport meta tag was dropped in the same edit that removed the unpkg `<script>`, which would have broken mobile layout |
| R-33 | CI does not run on a push to `main` | **Claude Code** | **Done.** `pr-checks.yml` triggered on pull requests only, so a direct push skips `check_branch_safety.py`, the compile step, the schema and query parse, and the credential scan. A direct push then landed `build_invention_page.py` with `from scripts.site_chrome import ...`, which cannot resolve under `python scripts/<name>.py` — `rebuild_all.py` died at step 5 and the committed page could not be regenerated by its own documented command. The compile step would have caught it. It now also runs `on: push: branches: [main]`; `branch-safety` is skipped there, since there is no branch to compare against main when the push IS main |
| R-35 | A removal / anonymisation request route | **Claude Code** | **Superseded by R-39**, which carries the same work with the suppression-list half written down |
| R-42 | **TEST** — a golden-file test for the page builders | **Gemini** | **Done** — PR #32. Structural snapshots of all 14 pages in `tests/golden/`, driven off `site_chrome.PAGES` so a page added without a snapshot **fails** rather than silently skipping. Negative-tested for real on merge, not just on synthetic HTML: removing a `<section>` from the published `ringers.html` fails the suite with the drifted keys named. **What it does not catch, stated so nobody assumes otherwise:** the stale-page drift that motivated this item is purely numeric, and numbers are masked by design — I checked, and the pre-republish `ringers.html` claiming 1,969,997 against a corpus of 1,969,949 passes cleanly. That was my error in writing the brief, not a fault in the delivery. The remaining half is R-50 |
| R-29 | `scratch/` is mistakable for the real pipeline | **Claude Code** | **Done.** All five deleted — throwaways superseded by `verify_corpus.py` and the recorded queries, and one (`patch.py`) hand-edited a page's nav bar, which is exactly what `site_chrome.py` exists to prevent and would now fail `verify_chrome.py`. `scratch/` is gitignored, so future ones stay untracked |
| R-36 | **JOIN** — bridge CompLib to the performance record by composer | **Claude Code** | **Done** — `docs/composer_bridge.md`, `scripts/resolve_composer_bridge.py`. **57,249 performances (19.5% of the corpus, 79.6% of those carrying a composer) attached to a named CompLib composer**, at a measured **99.80%** precision where checkable and an estimated **99.5%** where not. Two measurements, neither the matcher grading itself: a held-out subset of 26,917 performances where both sides spell the forename out, with all 69 residual disagreements read by hand and committed to `data/composer_bridge_adjudication.csv` — 127 of those 180 turned out to be the same person, so the naive reading understated precision by ten points; and corroboration against composer repertoire, which carries no name, at 94.3% versus a 43.1% null. That second test was itself checked against the hand labels before being used — it fires on 94.5% of known-right matches and 11.6% of known-wrong, and inverting it is what reaches the initial-only half. Five parser bugs found, two of them by the tests written for the first three. `performances.composition` confirmed 0% and closed |
| R-43 | Civic precision is 38.8% | **Gemini** | **Done** — PR #30. Scoped the royal patterns to royal-family terms (so the stage name in "1st Royal" no longer reads as a royal event) and demoted `civic` below the personal-event classes. Measured on the committed 400-row oracle: **civic precision 38.8% → 80.0%**, **overall accuracy 75.5% → 80.5%**. **Recall fell 82.6% → 52.2%** in the same change, so a civic count now *understates* by about half where it used to overstate; F1 still improved 0.528 → 0.632. `anniversary` regressed (F1 0.786 → 0.667), disclosed in the PR's own table. The fix does not reach the published page — see R-49 |
| R-40 | **VISUALISATION** — what a composition actually asks of a band | **Gemini** | **Done** — PR #33, `docs/calling.html` and `docs/composition_demands.md`. The largest untouched dataset in the corpus finally read: `calling` on 85,684 of 86,054 rows. **67.5% of Major peals are multi-part**, and 3-part is the single most common architecture (11,045, 37.7%); median 48 calls, mean 54.1. Every count and share reproduced exactly on merge. The derived conductor-memory column did not and was recomputed — it applied the overall mean (54) to the 1-part row, where the true mean is 42.4, so the headline contrast was 3.4× when it is 2.3×. `calls <= leads` invariant added after the published maximum (2,576 calls in a peal with at most 322 leads) turned out to be impossible; 18 of 29,302 rows (0.06%) parse over the ceiling, which leaves the median and mean untouched |
| R-52 | **SEARCH** — measure the contentious definitions before choosing them | **Claude Code** | **Done** — `docs/definitions_measured.md`, `scripts/measure_definitions.py`. Eight choices measured, and the ranking is not the one anyone would have guessed. **The largest is the spliced method double-count: 379,180 links on 228,479 performances, so "performances of method X" summed across methods overstates by 150,701 rows, +66.0%.** Then `bb_timestamp` turning out not to be a submission date at all (57,295 rows, 19.5%, sit on BellBoard's own bulk-import days — 11.1 MB of index on a column no query reads); handbells in a tower count (30,054, 10.2%); unknown `changes` (21,788, 7.4%, worth **1.43 points** on the headline peal share depending on denominator); the peal boundary (848, 1.62% of peals, and the `>` outlier is the query behind R-24's published result); ringer-per-row versus per-performance (3,414); and the stage-dependent minimum, which is **4 performances** and which my own first draft had wrongly led on. A recommendation is recorded per choice for R-53 to accept or overrule. Nothing was chosen here deliberately — choosing first and measuring after is how the flat threshold got there |
| R-53 | **FIX** — one place where a definition lives | **Claude Code** | **Done** — `scripts/semantics.py`, `schema/008_init_semantic_views.sql` (generated), `tests/test_semantics.py`. Every R-52 recommendation adopted. The rule is stated twice because the callers are split — 36 scripts in Python, recorded queries in SQL — and three things bind the two: the constants are shared, the SQL is **generated** from the Python by `build_semantic_views.py` with a `--check` that fails the build on a hand-edit or a stale regeneration (negative-tested both ways), and **the predicates and the view are compared row-for-row across all 293,471 performances**. `is_peal` is tri-state: **22,623 (7.7%) return None** rather than False — 21,788 with no length, 835 in [5000, 5040) with no resolved stage, where the two thresholds bracket the ambiguity exactly. Peal count under the adopted rule: **51,659**, and the four classes partition the corpus (51,659 + 205,292 + 13,897 + 22,623 = 293,471). Two named method measures rather than one, per R-52. **The agreement test immediately found an error in R-52's own document**: its arithmetic would not reconcile, because the stage rule is "seven or more bells" and the measurement had filtered `stage IN (5, 6)`, losing a stage-4 Minimus performance — 5, not 4. Corrected in both documents and both test files |
## Blocked, and on what

| # | Item | Owner | Blocked on |
| --- | --- | --- | --- |
| R-10 | Run the backfill to completion | Gemini | **Done** — 2012–2024 committed and verified. The only outstanding piece is *production* loading, which is **not scheduled**: the hosted database is dormant and whether it returns at all is R-51. Nothing in the corpus or on the site depends on it |
| R-8b | Method survival — adoption over time (option C, second half) | Claude Code | **Unblocked and superseded by R-46.** R-10 is done, so the adoption history exists; the work moved to Vibe as R-46 rather than staying here blocked on a thing that has happened |
| R-15 | Felstead — 360,000 peals back to the 1800s | Claude Code | **A reply from the CCCBR.** Enquiry sent 2026-08-15; `docs/felstead-enquiry.md`. The join is verified and the job is ~5,600 requests, so this starts the day there is an answer |
| R-12 | Consolidate data-quality caveats | Claude Code | Item 7, so the doc and the check agree |

## Held

| # | Item | Why held |
| --- | --- | --- |
| R-11 | Acoustic Landscape (option E) | Needs a ringer's review; getting bell acoustics wrong in public would be spotted instantly. The r/bellringing post may produce one |
| R-16 | Spliced ellipsis expansion *(was "abbreviation expansion")* | **Worked on 2026-08-15 and stopped again, one rung further along.** The name was wrong: measuring the leftovers rather than guessing showed abbreviations are 2% of the shortfall. The two real causes were a bug (nine Little Bob methods absent from the index) and an *ellipsis* — "St Clement's" for "St Clement's College", 471 rows. The bug is fixed; the ellipsis needs prefix matching with a threshold, which is tuning, which is the line. 1,487 rows remain one method short, recorded with their counts |

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

**What R-4 turned up, and why it changes how the rest should be read.** The
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
