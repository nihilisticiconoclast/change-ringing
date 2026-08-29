# Footnote Occasion Classifier Accuracy & Oracle Evaluation

> **Summary:** Ground-truth measurement and accuracy evaluation of the footnote occasion classifier across 400 independently labelled footnotes (seed = 42).
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

| Category | Ground Truth Support | Baseline Precision (R-19) | Post-Fix Precision (R-43) | Baseline F1 | Post-Fix F1 |
| :--- | ---: | ---: | ---: | ---: | ---: |
| **civic** | 23 | **38.8%** | **80.0%** | 0.528 | **0.632** |
| **funeral** | 13 | 88.9% | **92.9%** | 0.727 | **0.963** |
| **memorial** | 36 | 76.7% | **81.4%** | 0.697 | **0.886** |
| **first-performance** | 101 | 80.2% | **80.5%** | 0.840 | **0.868** |
| **none** | 120 | 78.6% | **81.5%** | 0.759 | **0.772** |
| **birthday** | 24 | 91.3% | 85.2% | 0.894 | **0.902** |
| **wedding** | 11 | 100.0% | **100.0%** | 0.952 | **1.000** |
| **compliment** | 11 | 90.0% | 90.0% | 0.857 | 0.857 |
| **seasonal** | 31 | 80.8% | 80.8% | 0.737 | 0.737 |
| **anniversary** | 12 | 68.8% | 50.0% | 0.786 | 0.667 |
| **practice** | 9 | 75.0% | 75.0% | 0.462 | 0.462 |
| **Overall Accuracy** | **400** | **75.5%** (302/400) | **80.5%** (322/400) | — | — |

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
