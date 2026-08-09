# Decision 002 — adjudicating the backfill row counts

**Status:** decided
**Date:** 2026-08-09
**Ruling:** Gemini's counts are right. Mistral's backfill run captured about
16% of the corpus and stopped without saying so.

## The dispute

| | Claim | Implied rate |
| --- | --- | --- |
| Mistral | 55,000 rows across all years, file >110 MB | ~3,700/year over 15 years |
| Gemini | 50,000 rows in 2023–2024 alone, 50 MB combined | ~25,000/year |

The two cannot both be right: they differ by roughly seven times on the same
source.

## Ground truth

BellBoard's own search page reports a result count, which settles this in three
requests rather than by argument. Measured 2026-08-09:

| Window | Performances |
| --- | ---: |
| 2023-01-01 → 2023-12-31 | **25,859** |
| 2024-01-01 → 2024-12-31 | **25,267** |
| 2012-01-01 → 2026-08-09 | **336,654** |

2023 and 2024 together are **51,126**. Gemini's ~50,000 for those two years is
correct.

Mistral's 55,000 for the whole period is **16.3% of 336,654**. The run is
missing roughly **281,000 performances** — and reported completion rather than
failure.

## Why this happened

This is the failure mode the brief warned about, in the exact shape predicted:

> BellBoard answers sustained querying by silently truncating responses, not by
> returning an error status. A naive loop reads a short page as "end of data"
> and stops early, producing a partial corpus that looks complete.

A run that ends early looks identical to a run that finished. Nothing in the
output distinguishes them, which is why the brief asked for the corpus size to
be estimated independently — an estimate would have caught this immediately,
because 55,000 across fifteen years is implausible against 25,000 in one.

The PR did report a corpus estimate, and it was honest about being unsure:
"could be in the hundreds of thousands". That instinct was right and the run
contradicted it. The lesson is that the sanity check has to *gate* the run, not
sit beside it in the write-up.

## The file-size signal

Mistral's artefact is ~2.0 KB per row (110 MB / 55k); Gemini's is ~1.0 KB per
row (50 MB / 50k). Mistral's is twice the size per record while holding
*fewer* unique records.

I have not inspected either file, so this is a hypothesis rather than a
finding: the most likely explanation is that overlapping or non-advancing
windows fetched the same performances repeatedly. Writes are idempotent
(`INSERT OR REPLACE` on BellBoard's ID), so duplicates collapse in the database
while still inflating any raw cache or log on disk. That would produce exactly
this signature — a large file, a small corpus, and no error.

If that is what happened, the window loop is advancing wrongly or falling back
to `changed_since` semantics, which sort by modification date and will keep
returning the same recently-edited records no matter which window is requested.

## Actions

1. **Do not load Mistral's output into any database.** A corpus that is 16%
   complete but presents as whole is worse than an empty one: every downstream
   count would be wrong in a way nothing detects.
2. **`336,654` is now a known number, not an unknown.** It goes in the README
   and the roadmap. Any backfill that ends materially below it has failed.
3. **The runner needs a completeness gate**, not just throttle handling. Before
   a window is marked complete, compare the rows fetched against the count
   BellBoard reports for that window via `search.php`, and refuse to checkpoint
   a window that falls short. A backfill that stops early must exit non-zero.
4. **Re-run from scratch** once that gate exists. The existing checkpoint file
   records windows as complete that are not, so it must be discarded rather
   than resumed.

## Note on the adjudication itself

Neither agent did anything unreasonable. Gemini measured a narrow window
carefully and got the right answer; Mistral built the harder thing and was
defeated by a server that lies quietly. The difference in outcome is mostly
the difference between a small job and a long one against a throttling source.

What resolved it was not judgement between two accounts but a third
measurement, costing three HTTP requests. That is the general lesson: when two
agents disagree on a quantity, go and measure the quantity.
