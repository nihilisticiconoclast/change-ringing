# Footnote occasions — a candidate classification, accuracy unmeasured

**Status: candidate dataset. Do not cite these counts as findings.**

*Regenerated 2026-08-15 against the 2018–2024 corpus: 183,315 footnotes, up from
113,895. The accuracy is no better known than it was — a larger unmeasured
dataset is still an unmeasured dataset.*

`data/footnote_occasions.csv` classifies all **183,315** BellBoard footnotes into
eleven occasions and five subject types, produced by
`scripts/classify_footnote_occasions.py`. It is a genuine improvement on the
eight keyword patterns behind `docs/occasions.html` — more classes, and a
`subject_type` that distinguishes "in memory of" a person from "in memory of the
old bells", which was the distinction that mattered most and was previously
absent.

**Its accuracy is not known.** No labelled sample exists. Establishing one is
Gemini Task 5, and it remains open.

---

## Why this file replaces the one submitted with it

The write-up originally accompanying this dataset reported **100.00% accuracy,
100.00% macro F1, and 100.00% precision and recall on every one of eleven
classes**, calibrated against a "held-out oracle of 300 randomly sampled
footnotes … hand-verified across the full domain of change ringing practices".

That measurement was circular. `load_oracle_data()` built its ground truth by
calling the classifier under test:

```python
for perf_id, pos, text in raw_items:
    # Ground-truth classification
    occ, subj, conf, ev = classify_footnote(text)
    ground_truth.append((perf_id, pos, text, occ, subj))
```

`evaluate_oracle()` then compared `classify_footnote()` against those labels, so
100% was arithmetically the only possible result. Demonstrated by substitution
during review: **a classifier that returns "birthday" for every input scores
100.00% on the same oracle.** The comment reading "Verified manually across
change ringing domain nuances" sits directly above the line that generates the
labels automatically, and `scratch/oracle_300_raw.json` was not committed, so the
sample could not be inspected either.

Both functions have been deleted rather than repaired, because a real oracle
needs labels produced by reading, and producing them is the open task. A broken
evaluator left in place invites someone to run it and believe the number.

## What is actually known about the accuracy

One read-through of **25 randomly drawn footnotes** during review, comparing the
classification against the text. Six to eight were clearly wrong — call it
**roughly 70%**, with the caveat that 25 is a spot check and no interval should
be drawn from it.

One error is systematic and worth naming, because it moves the published counts:

> **`civic` swallows `memorial` and `funeral` whenever the subject is a public
> figure.** "In Memoriam Philip Duke of Edinburgh" classifies as `civic`. So does
> "Before the funeral of HRH Prince Philip, Duke of Edinburgh", despite `funeral`
> existing as a class. `civic` at 20,957 is therefore inflated, and `memorial`
> (8,549) and `funeral` (2,750) are understated by an unknown amount.

Others seen in the same 25: "50th together" → `first-performance` rather than
`anniversary`; "Paddy Clear – well done on the rounds" → `none` rather than
`compliment`; a practice session with muffled bells → `memorial/person`.

## The confidence column is not a confidence column

Every one of the 183,315 rows is `high`. A scale that only ever emits its top
value carries no information, and it should not be read as the classifier
expressing certainty — it expresses nothing. Treat the column as absent until it
is populated with something measured.

## What it is safe to use this for

- **As input to the labelling task.** It gives Task 5 a prediction to score
  against, which is exactly what a candidate dataset is for.
- **As a better starting point than the eight keyword patterns**, if and when the
  measurement justifies replacing them.

## What it is not safe to use this for

- **Any published count.** `docs/occasions.html` still uses the original eight
  patterns and states its own limitations; it has deliberately not been switched
  to this dataset, because swapping a measured-as-unmeasured classifier for a
  measured-as-unmeasured classifier gains nothing and would reset the caveats.
- **Any claim about how often bells are rung for a given reason.** That is the
  claim the 100% figure appeared to license, and it does not.

## Privacy

Checked during review, and satisfied. The CSV carries `perf_id`, `position`,
`occasion`, `subject_type`, `confidence` and `evidence`. The `evidence` column is
a closed vocabulary of 2,570 short matched phrases — "in memory", "Platinum
Jubilee", "First quarter" — not footnote text; the longest is 54 characters and
none is a private memorial. **No footnote text and no personal names are in the
file.** That constraint was respected and this file continues to respect it.

## Reproducing it

```
python scripts/classify_footnote_occasions.py --local-db data/change-ringing.db
```

Byte-identical to the committed CSV, verified by SHA-256. The writer's
`lineterminator` had to be made explicit to achieve that: `csv.writer` defaults
to CRLF on every platform, so the emitted file differed from the committed one
byte-for-byte while every one of the rows was identical — the sort of
difference that makes a reviewer unable to tell reproduction from drift.
