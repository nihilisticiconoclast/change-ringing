# Footnote Occasion Classifier Accuracy & Oracle Evaluation

> **Summary:** Ground-truth measurement and accuracy evaluation of the footnote occasion classifier across 400 independently labelled footnotes (seed = 42).
>
> **The labels are independent, and here is the evidence** — restored on merge because
> asserting independence is not the same as showing it. PR #7 reported 100.00%
> accuracy from an oracle that called the classifier under test. These labels
> disagreed with the classifier on **98 of 400** at the time they were written, and
> every per-class figure was re-derived on merge and matched to the decimal. That
> disagreement rate is the reason any number here means anything.
> Delivers Roadmap items **[R-19](ROADMAP.md)** (baseline measurement) and **[R-43](ROADMAP.md)** / Gemini task **G-14** (precision fix).
> Code: [`scripts/classify_footnote_occasions.py`](../scripts/classify_footnote_occasions.py) | Evaluation: [`scripts/evaluate_footnote_classifier.py`](../scripts/evaluate_footnote_classifier.py) | Oracle: [`data/footnote_occasion_labels.csv`](../data/footnote_occasion_labels.csv).

---

## 1. Executive Summary & Headline Results

- **Overall Accuracy:** **80.5%** (322 / 400), improved from **75.5%** (302 / 400).
- **Civic Class Precision:** **80.0%** (12 / 15), resolved from **38.8%** (19 / 49).
- **Funeral Precision / Recall:** **92.9% precision / 100.0% recall** (F1 = 0.963, Support = 13).
- **Memorial Precision / Recall:** **81.4% precision / 97.2% recall** (F1 = 0.886, Support = 36).
- **First-Performance Precision / Recall:** **80.5% precision / 94.1% recall** (F1 = 0.868, Support = 101).

---

## 2. The Civic Precision Fix (Delivering R-43 / G-14)

In the initial evaluation, **Civic** exhibited a precision of only **38.8%** due to two systematic root causes:

1. **Stage Name Conflation with Royalty:** The word `royal` appeared as an unconstrained keyword in `P_CIVIC`. In change ringing, "Royal" is the standard name for ringing on 10 bells. Phrases such as *"1st Royal - 7."*, *"First Royal as conductor"*, and *"Canterbury Little Bob Royal"* triggered `civic` instead of `first-performance` or `none`.
   - **Fix:** Scoped `royal` in `P_CIVIC` to royal family terms (`royal family`, `royal household`, `royal visit`, `royal wedding`, `royal baby`, `royal air force`, `royal navy`, `royal british legion`).
2. **Royal Death / Funeral Precedence:** When ringers rang muffled bells or attended funeral services for monarchs or princes (e.g. *"Half muffled tolling ahead of the funeral of Her Late Majesty Queen Elizabeth II"*, *"In memoriam HRH The Prince Philip"*), the classifier assigned `civic` rather than `funeral` or `memorial`.
   - **Fix:** Refactored classifier priority so that `funeral` and `memorial` take precedence over generic civic terms, ensuring tributes and funerals are classified as life events rather than civic celebrations.

### Benchmark Comparison (Before vs After)

| Category | Support | Precision before → after | **Recall before → after** | F1 before → after |
| :--- | ---: | :--- | :--- | :--- |
| **civic** | 23 | 38.8% → **80.0%** | **82.6% → 52.2%** | 0.528 → **0.632** |
| **funeral** | 13 | 88.9% → 92.9% | 61.5% → **100.0%** | 0.727 → **0.963** |
| **memorial** | 36 | 76.7% → 81.4% | 63.9% → **97.2%** | 0.697 → **0.886** |
| first-performance | 101 | 80.2% → 80.5% | 88.1% → 94.1% | 0.840 → 0.868 |
| none | 120 | 78.6% → 81.5% | 73.3% → 73.3% | 0.759 → 0.772 |
| birthday | 24 | 91.3% → 85.2% | 87.5% → 95.8% | 0.894 → 0.902 |
| wedding | 11 | 100.0% → 100.0% | 90.9% → **100.0%** | 0.952 → **1.000** |
| compliment | 11 | 90.0% → 90.0% | 81.8% → 81.8% | 0.857 → 0.857 |
| seasonal | 31 | 80.8% → 80.8% | 67.7% → 67.7% | 0.737 → 0.737 |
| **anniversary** | 12 | **68.8% → 50.0%** | 91.7% → 100.0% | **0.786 → 0.667** |
| practice | 9 | 75.0% → 75.0% | 33.3% → 33.3% | 0.462 → 0.462 |
| `multiple` | 9 | 0.0% → 0.0% | 0.0% → 0.0% | 0.000 → 0.000 |
| **Overall accuracy** | **400** | **75.5% (302/400) → 80.5% (322/400)** | | |

**Read the recall column before quoting the precision one.** Civic precision more
than doubled, and civic *recall* fell from 82.6% to 52.2%: the class went from
over-detected to under-detected, and roughly half of genuine civic footnotes are
now missed. F1 still improved, so this is a net win — but a civic COUNT is now an
undercount by nearly half, and that caveat has to travel with the number.

`anniversary` regressed (F1 0.786 → 0.667) because demoting `civic` below the
personal-event classes sends some national-anniversary footnotes to
`anniversary`. Disclosed here rather than dropped.

---

## 3. Methodology & Oracle Integrity

- **Population:** 337,946 total footnotes across the full 2012–2024 BellBoard archive (`performance_footnotes`).
- **Sample Size:** 400 footnotes drawn via uniform pseudo-random selection with a fixed, deterministic seed (`random_state = 42`).
- **Independent Labelling:** Each footnote was labelled without reference to the classifier's output.
- **Evaluation Harness:** Re-runnable via `python scripts/evaluate_footnote_classifier.py --local-db local_corpus.db`.

---

## 4. Deliverables

1. `scripts/classify_footnote_occasions.py` — updated classifier with scoped royal patterns and event precedence.
2. `scripts/evaluate_footnote_classifier.py` — automated evaluation tool testing against the 400-row oracle.
3. `tests/test_footnote_classifier.py` — unit regression tests verifying royal funeral/memorial classification and stage-name immunity.
4. `data/footnote_occasions.csv` — regenerated candidate dataset (337,946 rows) matching the updated classifier.

---

## 5. Reporting Recommendations for Published Pages

Restored on merge and updated for the post-fix figures. The previous version of
this section was deleted in the rewrite; its item 3 recommended precisely the fix
this work implements, so it is worth keeping the record that the document
predicted its own repair.

1. **Safe to publish as counts:** first-performance, birthday, wedding,
   compliment, seasonal, funeral, memorial. All now sit at 80–100% precision with
   recall to match.
2. **Still not safe as an unadjusted count — for the opposite reason to before:**
   - **Civic.** Precision is fixed (80.0%), but recall is **52.2%**, so a published
     civic count now understates by roughly half. Before the fix it overstated.
   - **Practice.** Unchanged at 33.3% recall; heavily undercounted.
   - **`multiple`.** 0.0% precision and 0.0% recall on 9 supported footnotes — the
     classifier never predicts it. Either predict it or remove it from the schema;
     a class that can never be emitted is not a class.
3. **A second, unmeasured classifier exists and the published page uses it.**
   `docs/occasions.html` is built by `build_occasions_page.py`, which carries its
   own `CATEGORIES` dict and does **not** call `classify_footnote_occasions.py`.
   Its `Royal / National` bucket is still
   `\b(jubilee|coronation|queen|king|royal|majesty|accession|platinum|remembrance|armistice)\b`
   — bare `royal`, bare `queen`, bare `remembrance`: the exact over-broad pattern
   fixed here. So the published page gets no benefit from this work, and the only
   occasion classifier that has ever been measured is the one the site does not
   use. Filed as R-49.


---

## How good is the oracle itself?

Every number above treats the 400 labels as truth. They are not truth; they are a
second opinion, and a review pass found they are wrong often enough to matter.

**Read 16 of the 98 disagreements at random (seed 7) and judged each side.**
Roughly 11 favoured the label and 4 favoured the classifier, with one genuinely
arguable. Extrapolated, the oracle is right on about three quarters of the cases
where it differs, so it carries an error rate of **roughly 7% overall**
(0.245 × 0.28). The classifier's true accuracy is therefore near 75.5% but not
pinned to it, and no figure in this document should be quoted to a tenth of a
per cent as though the denominator were exact.

Cases where the **classifier** was right and the label wrong:

| Footnote | Label | Classifier |
| --- | --- | --- |
| `In loving memory of our friend Chris Kippin` | `none` | `memorial` |
| `First on the Treble for 1` | `none` | `first-performance` |
| `1st blows in Method: 5` | `none` | `first-performance` |
| `150th quarter peal on the bells:1` | `none` | `first-performance` |

That is a **systematic** gap, not four unlucky draws: terse milestone forms —
`1st blows in`, `First on the Treble`, an ordinal followed by a colon — are
labelled `none` while the classifier catches them. The `first-performance` recall
of 88.1% is therefore understated, and `none` precision of 78.6% overstated.

**The `notes` column does not evidence a hand read.** It holds 18 distinct values
across 400 rows — roughly one per class — so it is a legend rather than
per-footnote reasoning. The labels are demonstrably independent of the classifier,
which is the property that matters and the one PR #7 lacked; but "annotated by
hand" is not a claim this file can support, and it has been softened to
"independently labelled" throughout.

**`multiple` is scored as nine straight failures.** The methodology section says
compound footnotes were "evaluated against their primary constituent category",
but `multiple` appears as a label in the CSV and the classifier can never emit it,
so all nine count against accuracy. Resolving them to a primary category, as
described, would lift overall accuracy by up to 2.3 points.

### What would finish this

1. Re-label the terse milestone forms and re-run — the single highest-value fix.
2. Resolve the nine `multiple` rows to a primary class, or score them separately.
3. Have a second annotator label an overlapping subset, and publish the agreement
   between them. Until two independent readers agree, the oracle's own accuracy is
   estimated from a 16-case spot check, which is thin.

None of that undermines the finding. **`civic` precision of 38.8% is real**, the
royal-death patterns swallowing memorial and funeral records are exactly the bug
`docs/footnote_occasions.md` predicted, and the recommendation not to publish
`civic` or `practice` counts stands.
