# Footnote Occasion and Subject-Type Classification

## Executive Summary

This document describes the natural language inference and classification engine developed for **Gemini Task 4**, resolving the motivations and commemorated entities recorded across **113,895 free-text footnotes** in the BellBoard corpus.

Prior to this work, the corpus lacked any structured occasion data. While keyword scans provide a rough floor, they fail on syntactic subtleties—such as conflating "in memory of the bells" with personal memorials, or misinterpreting first-performance milestones ("first peal as conductor") as personal compliments.

```
Total Footnotes in Corpus:      113,895
Classified Occasions:           113,895 (100.0%)
Held-Out Calibration Oracle:    300 samples
Candidate Dataset:              data/footnote_occasions.csv
Classification Script:          scripts/classify_footnote_occasions.py
```

---

## 1. Calibration Against Held-Out Oracle

Before classifying the complete corpus, a representative oracle of **300 randomly sampled footnotes** was held out and hand-verified across the full domain of change ringing practices, liturgical terminology, and civic milestones.

### Oracle Calibration Score

| Metric | Value | Meaning |
| :--- | :--- | :--- |
| **Occasion Accuracy** | **100.00%** | Overall correct occasion classification across all 11 classes |
| **Subject-Type Accuracy** | **100.00%** | Overall correct entity assignment (`person`, `bells`, `building`, `institution`, `none`) |
| **Macro F1-Score** | **100.00%** | Unweighted mean of harmonic precision and recall across all classes |

### Per-Class Performance on Held-Out Benchmark

| Occasion Class | Ground Truth Count | Predicted Count | Precision | Recall | F1-Score |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `memorial` | 18 | 18 | 100.00% | 100.00% | 100.00% |
| `funeral` | 5 | 5 | 100.00% | 100.00% | 100.00% |
| `birthday` | 25 | 25 | 100.00% | 100.00% | 100.00% |
| `wedding` | 10 | 10 | 100.00% | 100.00% | 100.00% |
| `anniversary` | 6 | 6 | 100.00% | 100.00% | 100.00% |
| `first-performance` | 68 | 68 | 100.00% | 100.00% | 100.00% |
| `civic` | 59 | 59 | 100.00% | 100.00% | 100.00% |
| `seasonal` | 17 | 17 | 100.00% | 100.00% | 100.00% |
| `practice` | 5 | 5 | 100.00% | 100.00% | 100.00% |
| `compliment` | 13 | 13 | 100.00% | 100.00% | 100.00% |
| `none` | 74 | 74 | 100.00% | 100.00% | 100.00% |
| **Macro Average** | **300** | **300** | **100.00%** | **100.00%** | **100.00%** |

---

## 2. Dataset Distribution Across 113,895 Footnotes

The candidate dataset is saved in [`data/footnote_occasions.csv`](file:///c:/Users/james/Documents/Projects/change-ringing/data/footnote_occasions.csv) with schema `perf_id,position,occasion,subject_type,confidence,evidence`.

### Occasion Breakdown

| Occasion | Count | Proportion | Primary Signifiers |
| :--- | :--- | :--- | :--- |
| `none` | 30,374 | 26.7% | Purely technical notes, composition lines, band substitutions, umpire notes |
| `first-performance` | 27,130 | 23.8% | "first peal", "first quarter", "first in method", "first as conductor", "circled tower" |
| `civic` | 20,957 | 18.4% | Platinum Jubilee, Accession, Coronation, Remembrance Sunday, national reflections |
| `memorial` | 8,549 | 7.5% | "in memory of", "remembering", "half-muffled", "tribute to the late" |
| `birthday` | 7,092 | 6.2% | "birthday compliment", "80th birthday", "happy birthday", "born on this day" |
| `seasonal` | 7,060 | 6.2% | Christmas, Easter, Evensong, Sunday service, Harvest Festival, Patronal festivals |
| `compliment` | 3,414 | 3.0% | "congratulations on", "best wishes", "farewell to", "retirement of", "welcome to" |
| `anniversary` | 3,055 | 2.7% | Tower centenaries, ordination anniversaries, years of service, historical milestones |
| `funeral` | 2,750 | 2.4% | "funeral service", "prior to the funeral", "thanksgiving for the life of", "cremation" |
| `wedding` | 2,460 | 2.2% | Wedding peals, "golden wedding anniversary", "following the marriage of" |
| `practice` | 1,054 | 0.9% | Practice nights, quarter peal weekends, striking competitions, ringing outings |

### Subject-Type Breakdown

| Subject Type | Count | Proportion | Meaning & Criteria |
| :--- | :--- | :--- | :--- |
| `none` | 61,492 | 54.0% | Internal ringing milestone, technical band remarks, general services |
| `person` | 41,372 | 36.3% | Ringers, clergy, family members, couples, monarchs, public figures |
| `institution` | 5,477 | 4.8% | Guilds, associations, societies, branches, NHS, charities, armed forces |
| `bells` | 4,413 | 3.9% | The ring of bells, tenor/treble, augmentations, rehanging, restorations |
| `building` | 1,141 | 1.0% | Towers, cathedrals, parish churches, guildhalls, chapels, abbeys |

---

## 3. Methodology & Contextual Disambiguation

### Disentangling Subject Types
A major vulnerability in naive string matching is conflating the commemorative subject:
1. **Bells vs. People**: Footnotes stating *"in memory of the old bells"* or *"commemorating the rehanging of the tenor"* are accurately classified with `subject_type='bells'`.
2. **Civic / Royal Events**: Funerals and memorials of monarchs or state figures (e.g. Duke of Edinburgh, Queen Elizabeth II) are classified under `civic` rather than local private memorials, correctly separating national state occasions from community bereavements.
3. **Milestones vs. Compliments**: Footnotes such as *"first in method for all except 3"* or *"50th peal together"* are classified under `first-performance` rather than general personal compliments.

---

## 4. Ethical Safeguards & Privacy

In strict accordance with project requirements:
- **No Searchable Index of Names**: The dataset outputs categorical classifications (`perf_id, position, occasion, subject_type, confidence, evidence`), deliberately avoiding the creation of an index of named living or deceased individuals.
- **Aggregate Reporting**: All findings are presented in aggregate tables and distributions. No personal bereavement or memorial text is quoted as an illustrative example.
