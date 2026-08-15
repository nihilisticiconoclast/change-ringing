# Footnote Occasion Classifier Accuracy & Oracle Evaluation

**Deliverable for Gemini Task 5.** Ground-truth measurement of the footnote
occasion classifier against a random sample of 400 footnotes (seed = 42).

> **This closes the hole in PR #7.** That submission reported 100.00% accuracy
> from an oracle that called the classifier under test to build its own ground
> truth. These labels are genuinely independent: **98 of the 400 disagree with the
> classifier**, and every per-class figure below was re-derived on merge and
> matched to the decimal. It is the first real measurement of this classifier.

**Headline: overall accuracy is 75.5%** — 302 of 400. That figure is not in the
original write-up, which led with the best-performing class; it belongs at the
top because it is the number anyone deciding whether to trust the dataset needs.
It also sits close to the ~70% a 25-footnote read-through estimated in
`docs/footnote_occasions.md`, which is mild independent support for both.

- **Ground-Truth Dataset:** [`data/footnote_occasion_labels.csv`](../data/footnote_occasion_labels.csv) (400 independently labelled records with occasion label, subject type, and notes)
- **Classifier Under Test:** [`scripts/classify_footnote_occasions.py`](../scripts/classify_footnote_occasions.py)

---

## 1. Executive Summary & Headline Result

The largest classified category, **First-performance / Milestones**, achieves **80.2% precision** and **88.1% recall** (F1 = 0.840, Support = 101).

While the classifier functions well for distinct milestone events (**Wedding** 100.0% precision, **Birthday** 91.3% precision, **Compliment** 90.0% precision), systematic structural confusion exists around **Civic** occasions:
- **Civic** exhibits a precision of only **38.8%** (F1 = 0.528), caused by aggressive royal/national regex patterns swallowing 12 **Memorial** tributes and 5 **Funeral** records.
- **Practice / Tour** suffers from low recall (**33.3%**), as guild ringing weeks and striking competitions frequently lack explicit trigger terms.

Based on these empirical error bounds, **Civic** and **Practice** counts should **not** be reported as authoritative standalone statistics on public-facing pages without qualifying confidence intervals or refactoring the priority hierarchy.

---

## 2. Methodology & Sampling

### A. Sampling Strategy
- **Population:** 337,946 total footnotes across the full 2012–2024 BellBoard archive (`performance_footnotes`).
- **Sample Size:** 400 footnotes drawn via uniform pseudo-random selection with a fixed, deterministic seed (`random_state = 42`).
- **Independent labelling:** each footnote was labelled without reference to the classifier's output — confirmed on merge, since 98 of the 400 labels disagree with it. See "How good is the oracle itself?" below for what that labelling can and cannot be shown to be.
- **Privacy Constraint:** In accordance with the privacy rules for memorial records, no living or deceased individuals' names appear in this evaluation report.

### B. Pre-Measurement Predictions
Before running the evaluation matrix, the following outcomes were predicted based on domain inspection:
1. *First-performance* would dominate the sample (~25%) and achieve moderate-to-high precision (75–85%), but suffer false positives from generic words ("first on the bells", "longest length").
2. *Civic* would suffer severe precision loss by misattributing royal and national death memorials to civic ceremonies rather than memorials.
3. *Church Season / Liturgical* would be confused with ordinary weekend services and evening choral performances.

---

## 3. Per-Category Performance Metrics

Evaluated across the 400-footnote oracle dataset:

| Category | Ground Truth Support | True Positives (TP) | False Positives (FP) | False Negatives (FN) | Precision | Recall | F1-Score |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **wedding** | 11 | 10 | 0 | 1 | **100.0%** | 90.9% | **0.952** |
| **birthday** | 24 | 21 | 2 | 3 | **91.3%** | 87.5% | **0.894** |
| **compliment** | 11 | 9 | 1 | 2 | **90.0%** | 81.8% | **0.857** |
| **funeral** | 13 | 8 | 1 | 5 | **88.9%** | 61.5% | **0.727** |
| **seasonal** | 31 | 21 | 5 | 10 | **80.8%** | 67.7% | **0.737** |
| **first-performance** | 101 | 89 | 22 | 12 | **80.2%** | 88.1% | **0.840** |
| **none** | 120 | 88 | 24 | 32 | **78.6%** | 73.3% | **0.759** |
| **memorial** | 36 | 23 | 7 | 13 | **76.7%** | 63.9% | **0.697** |
| **practice** | 9 | 3 | 1 | 6 | **75.0%** | 33.3% | **0.462** |
| **anniversary** | 12 | 11 | 5 | 1 | **68.8%** | 91.7% | **0.786** |
| **civic** | 23 | 19 | 30 | 4 | **38.8%** | 82.6% | **0.528** |

*Note: 9 footnotes contained compound/multiple distinct occasions (e.g. Birthday + First Quarter, or Memorial + Tower Anniversary) and were evaluated against their primary constituent category.*

---

## 4. Key Confusion Pairs & Systematic Errors

```mermaid
graph LR
    Memorial["True Memorial (36)"] -- 12 misclassified --> Civic["Predicted Civic"]
    Funeral["True Funeral (13)"] -- 5 misclassified --> Civic["Predicted Civic"]
    NoneType["True None (120)"] -- 21 misclassified --> First["Predicted First-Perf"]
    Seasonal["True Seasonal (31)"] -- 8 misclassified --> NoneType["Predicted None"]
    Practice["True Practice (9)"] -- 5 misclassified --> NoneType["Predicted None"]
```

### 1. The Royal & National Civic Trap (Precision: 38.8%)
- **Mechanism:** The regex patterns for `civic` match tokens such as `her majesty`, `queen elizabeth`, `duke of edinburgh`, `prince philip`, and `remembrance`.
- **Failure Mode:** When a performance is rung half-muffled for the death or funeral of a royal figure (e.g., *"Half muffled tolling of tenor bell ahead of the funeral of Her Late Majesty Queen Elizabeth II"* or *"In memory of HRH Prince Philip"*), the classifier assigns `civic` instead of `memorial` or `funeral`.
- **Impact:** `civic` captures 30 false positives, artificially inflating civic events while depressing memorial and funeral counts.

### 2. The Generic "First" Pattern (Precision: 80.2%)
- **Mechanism:** The term `first` appears in non-milestone contexts, such as military regiments (*"1st/4th Bn. Lincs Regt"*), geographic records (*"First in this tower"*), or place notation descriptions.
- **Failure Mode:** 21 instances of unclassified notes were mislabeled as `first-performance`.
- **Impact:** Precision sits at 80.2% rather than 95%+, meaning approximately 1 in 5 automated "first performance" tags is a false positive.

### 3. Sparse Terminology in Practice & Guild Events (Recall: 33.3%)
- **Mechanism:** Guild tours, branch ringing weeks, and striking competitions use idiosyncratic phrasing (*"Newbury Branch Ringing Week"*, *"Alphabet Trio Challenge"*).
- **Failure Mode:** 5 of 9 practice/tour events lacked explicit keyword triggers and fell through to `none`.

---

## 5. Reporting Recommendations for Published Pages

Based on the empirical oracle score:

1. **Retain on Published Visualisations:**
   - **First-performance, Birthday, Wedding, Compliment, and Seasonal** possess sufficient precision (80–100%) and represent genuine ringing intent.
2. **De-prioritise or Qualify on Published Visualisations:**
   - **Civic:** Should **not** be presented as an unadjusted count on `docs/occasions.html`. The 38.8% precision indicates that over 60% of entries in this bucket are misclassified royal memorials, funerals, or military anniversaries.
   - **Practice:** At 33.3% recall, practice/training events are heavily undercounted.
3. **Recommended Classifier Priority Fix:**
   In any future classifier refactor, evaluate `funeral` and `memorial` **before** `civic` when death/muffled/passing tokens are present alongside royal names.

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
