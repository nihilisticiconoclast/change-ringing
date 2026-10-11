# The corpus dashboard

A three-page dashboard over the committed corpus: **ringing activity** across
2012–24, **corpus health** (how complete, how linked, where the traps are), and
the **project itself** (roadmap, predictions, commits, and the figures the docs
state, recounted). It lives as a claude.ai Dashboard artifact; every figure on it
comes from one of eighteen JSON datasets written by
`scripts/build_dashboard_data.py`, and the page source is in `dashboard/`.

The figures below are from a build at `c0cb3d2` (27 September 2026), and each one
is in a dataset the script writes, so it can be recomputed rather than trusted.

## Rebuild it

```
pip install -r requirements.txt
python scripts/build_dashboard_data.py          # writes dashboard/data/*.json, about 30 seconds
```

Nothing touches the network or the database. The inputs are
`data/bellboard/*.csv`, `data/complib/*.csv`, the committed resolution files, the
Markdown and the git history, so the clone must be a full one: the build refuses
a shallow clone rather than publish a project history of a single commit.
`dashboard/data/` is ignored, because the datasets are build products like the
replica.

The build fails on an internal invariant, and only on one of those (the stage
substitution below, a setting that does not partition the corpus, a commit author
nobody has grouped). It does **not** fail because a document disagrees with a
recount. That is reported, in `doc_claims.json`, because the usual reason a
stated figure stops matching is that someone has since corrected the sentence.

## Definitions

**Peal, quarter, unknown** come from `scripts/semantics.py` through `is_peal` and
`length_class`; no threshold is restated. The one input semantics.py takes that the
build has to supply is the stage, and it only matters for lengths in [5000, 5040).
The views read it from the resolved CCCBR method, which needs the Methods Library;
the build reads it from the stage word in BellBoard's method name. For a
performance with a resolved method the two agree, because the resolver matched the
method by that name, and a performance with no resolved method is left unknown,
exactly as `v_performance_length` leaves it. The substitution could differ in two
cases -- a resolved performance whose name states no stage, or stages either side
of seven -- and the build counts both and fails if either is non-zero. At
`c0cb3d2` both are zero, and the result reproduces the views:

| Class | Performances |
| --- | ---: |
| Peal | 51,659 |
| Quarter | 205,292 |
| Shorter | 13,897 |
| Unknown | 22,623 |
| **All** | **293,471** |

The 22,623 unknown are the 21,788 with no recorded length and the 835 of
5,000–5,039 changes with no resolved method, which is the figure `semantics.py`
states.

**Setting.** Virtual is any performance BellBoard flags `simulated-sound`,
whatever its ring type; tower bells and handbells are the rest, split by
`TOWER_RING_TYPE`. That gives 258,835 tower-bell, 25,532 handbell and 9,104
virtual performances.

**Ringers** are the resolved name clusters in
`data/ringer_identity_candidates.csv`, counted per performance rather than per
row. They are clusters, not verified people (R-9). A name the identity file lacks
counts as its own cluster; 3,029 of 1,962,715 appearances carry one.

**Towers rung** is the number of distinct Dove tower IDs among tower-bell
performances. **First quarters** and **first peals** are BellBoard's own
per-ringer flags.

## What the pages show

- **Ringing activity**, filtered by setting and year: performances, peals, quarter
  peals, ringers, towers rung and first quarters, each against the year before;
  performances by month; peals and quarters by year; firsts by year; the stage
  mix; the top 20 counties; and searchable tables of the 100 most-rung method
  names and the 100 busiest towers.
- **Corpus health**: per-year completeness against BellBoard's own count, a
  field-by-year coverage grid, the peal/quarter/unknown mix by year, what the
  unlinked performances are, how far each join between the corpora reaches, and
  the known traps with the records each touches.
- **Project tracker**: roadmap items by state, the hypotheses and their verdicts,
  commits by day and contributor, and the recount of stated figures.

## What it found

**Virtual ringing is counted as tower ringing.** 4,582 performances carry the
`simulated-sound` flag -- rung on a virtual platform or a simulator -- and ring
type `tower`, so `is_tower`, and every tower-level figure built on it, counts
them as ringing in a tower. The dashboard separates them; `semantics.py` does not
yet, and whether it should is a definitions decision of the R-53 kind.

**Eight stated figures, in six sentences, have drifted.** The build reads 34
figures from the README, `docs/HYPOTHESES.md`, `scripts/semantics.py`,
`docs/definitions_measured.md` and the data docs, and recounts each. Twenty-six
agree, including every per-year count in `data/SOURCES.md`. These do not:

| Where | Stated | Now |
| --- | ---: | ---: |
| README.md:18, “Thirteen pages” | 13 | 14 |
| README.md:43, “All 13 pages carry the same nav” | 13 | 14 |
| README.md:46, “39 unit and oracle tests” | 39 | 97 |
| README.md:121, “~94% of performances carry it” (a Dove tower ID) | 94% | 88.1% |
| README.md:267, “Three of twenty-three predictions held” | 3 of 23 | 4 of 29 |
| docs/HYPOTHESES.md:8, “Twenty-four of the twenty-eight entries” | 24 of 28 | 25 of 29 |

The Dove-ID share is 98.2% for ring type `tower` alone, so the sentence may mean
tower ringing; it does not say so. The test count is unittest's, at this commit,
before `tests/test_dashboard_data.py` was added. This is the stale-figure problem
R-50 describes, measured once rather than solved: the recount runs when the
dashboard is rebuilt, not on every change.

**Ringers fell by a third in 2024 while ringing barely moved.** Resolved ringers
went from 25,890 in 2023 to 17,212 in 2024, down 33.5%, against performances down
2.3% (25,859 to 25,267). It is not yet explained, which makes it a candidate for
`docs/HYPOTHESES.md` -- with the prediction written down before anyone measures it.

## What is not counted here

Dove's Guide and the CCCBR Methods Library are fetched at build time by
`build_local_db.py`, so their sizes (7,262 ringing towers, 63,894 bells, 25,055
methods, 30,734 first-performance events) are read from `data/LICENCE-DATA.md` and
labelled as stated, as is the 95.6% place-notation resolution rate for CompLib
method rows. Everything else is counted.

## Privacy and licence

Aggregates only. Ringer names are read to count distinct ringers and are never
written out; footnote text is not read at all. Towers are named, because a tower
is a building. The datasets derive from BellBoard, CompLib, Dove's Guide and the
CCCBR Methods Library and carry CC BY-SA 4.0 (`data/LICENCE-DATA.md`). The
dashboard is private to its owner unless shared, and anyone it is shared with can
read its attached datasets.

## The datasets

| Dataset | Rows | What it holds |
| --- | ---: | --- |
| `activity_yearly` | 56 | Each year and setting, plus 2012–24 totals: performances, peals, quarters, ringers, firsts, and change on the year before |
| `towers_yearly` | 14 | Distinct Dove towers rung by tower bells, per year |
| `activity_monthly` | 468 | Performances, peals and quarters per month and setting |
| `stage_mix` | 784 | Performances per stage group, year and setting |
| `top_methods` | 5,077 | The 100 most-rung method names per year and setting |
| `top_towers` | 1,400 | The 100 busiest towers per year, by tower-bell performances |
| `counties` | 1,093 | The 20 busiest counties per year and setting |
| `corpus_tables` | 12 | Row counts per corpus, counted or stated |
| `completeness_by_year` | 13 | Per-year recount against `data/SOURCES.md` and its search.php re-check |
| `field_coverage` | 140 | Share of each year's performances carrying each field or link |
| `linkages` | 7 | How far each join between the corpora reaches |
| `unresolved_methods` | 7 | What the performances without a method link are |
| `hazards` | 7 | The documented data traps, and the virtual-tower one, with records touched |
| `commits_daily` | 21 | Commits per day by contributor group |
| `snapshot` | 1 | The commit the datasets describe |
| `roadmap` | 57 | Every R- item, with type, owner and state |
| `hypotheses` | 29 | Every H entry, with its verdict |
| `doc_claims` | 34 | Stated figures against a recount |
