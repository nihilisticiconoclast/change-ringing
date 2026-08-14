# Queries

The SQL behind the corpus, kept as files rather than buried in scripts so the
figures on the atlas can be traced back to the statement that produced them.

Run any of them against the committed snapshot with no setup:

```
sqlite3 data/change-ringing.db < queries/findings/rudhall_territory.sql
```

or open `data/change-ringing.db` in DB Browser for SQLite, DBeaver, TablePlus,
or a VS Code SQLite extension, and paste. Nothing here needs Turso — see
`docs/CONNECTING.md` for why the live database is frozen until 2026-09-01.

## `atlas/` — what builds the page

These are not a copy of the queries the atlas uses. They **are** the queries:
`scripts/build_atlas.py` reads these files at build time. A `queries/` folder
that duplicates the real thing is worse than none, because it looks
authoritative while quietly going stale — so the duplication is removed rather
than managed.

| File | Produces |
| --- | --- |
| `01_bells_by_founder_group.sql` | Every attributed bell with its coordinates and foundry tradition — the map and the timeline |
| `02_first_peals_by_foundry.sql` | The three-corpus join: methods first rung on each tradition's bells |
| `03_foundry_group_metadata.sql` | The foundry cards — working life, firms, output, home town |
| `04_corpus_totals.sql` | The four headline figures, and the deliberately-unlinked count |

Aggregation happens in Python, not SQL: dominant tradition per tower,
quarter-century bucketing, and casting years, which need extracting from free
text (`Cast_Date` holds `c1897`, `(1834`, `[1902`). The SQL fetches rows; the
script shapes them.

## `rhythm/` — what builds the Rhythm page

Same arrangement: `scripts/build_rhythm_page.py` reads these, it does not copy
them.

| File | Produces |
| --- | --- |
| `01_daily_profile.sql` | One row per calendar day — volume, tower/handbell, length class, tolling, muffled. The calendar, the weekday pulse, the seasonal shape, the anomaly detection and the register scatter are all derived from these ~1,460 rows |
| `02_day_footnotes.sql` | The most repeated footnote per day, which is how an anomalous day gets named from the corpus rather than from the author's memory of the news |
| `03_window_totals.sql` | Headline figures, and the 5.7% background rate of muffled ringing |
| `04_counted_tolls.sql` | Tolling records whose method field starts with a number — "99 Tolling" is ninety-nine strokes, one per year of life |

Anomaly detection is in Python, not SQL: each day is compared with the median of
the same weekday within six weeks either side. Same weekday because Sunday is
two and a half times Monday, so a plain rolling mean flags every Sunday; median
because the thing being detected would otherwise inflate its own baseline.

## `occasions/` — what builds the Occasions Archive

| File | Produces |
| --- | --- |
| `01_footnotes_with_length.sql` | Every footnote with its date and performance length, plus the denominators the page needs to state its own coverage |

One row per **footnote**, not per performance: 113,894 footnotes attach to 76,163
performances. Calling those counts performances overstates by half, which the page
did until it was corrected.

## `findings/` — the claims in the prose

One file per assertion made on the atlas page or in the commit history, so
each can be checked rather than taken on trust.

| File | Checks |
| --- | --- |
| `busiest_towers_for_first_peals.sql` | Loughborough's Bell Foundry Tower tops first-peals at 507 |
| `rudhall_territory.sql` | Rudhall is regional — the Severn valley and Welsh marches |
| `founder_reach_by_methods.sql` | Why the `Group` column matters: Taylor under two names |
| `first_peals_by_decade.sql` | Post-war growth in new methods |
| `unlinked_performances.sql` | The 8,623 records deliberately left unlinked, and why |
| `most_rung_methods.sql` | Which methods are actually rung — and that 81.6% of Major methods were not rung once in four years |
| `method_linkage_coverage.sql` | The coverage and confidence claims for `schema/005`, including the unresolved half |
| `september_is_one_funeral.sql` | Why "September is the busiest ringing month" was wrong: 54% of the month is one fortnight of 2022 |
| `remembrance_muffle_rate.sql` | 73% / 74% / 72% / 74% half-muffled on Remembrance Sunday, against a 5.7% baseline |
| `counted_tolls_are_ages.sql` | "99 Tolling" peaks the day after a 99-year-old died; "96" the day after a 96-year-old; "365" one year after the first lockdown |

## A third thing that will bite you

**Any aggregate over `perf_date` needs to say whether the national days are in
or out.** 24 days carry 21.0% of the four-year corpus. A monthly total that
includes them is measuring the news: September leads the raw figures and comes
7th once they are removed, and the weekly trough moves from Wednesday to Monday.
`queries/rhythm/01_daily_profile.sql` gives you the per-day counts to exclude
from; the rule that identifies them is in `scripts/build_rhythm_page.py`.

## Two things that will bite you

**`dove.TowerID` is not unique.** 7,262 rows carry 7,249 distinct IDs, because
13 towers hold more than one ring — Farnham S Andrew has a full-circle and a
lightweight ring under `TowerID 11301`. Joining on it alone fans out and
inflates counts. Use `RingID` where the question is about a specific ring.

**Founder counts overlap and must not be summed.** A ring usually mixes
founders, so a first-peal can count towards more than one tradition. The
figures are per-tradition reach, not a partition of the total.
