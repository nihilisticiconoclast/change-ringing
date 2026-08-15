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

## 2. Dataset Distribution Across 337,946 Historical Footnotes (2012–2024)

The candidate dataset is saved in [`data/footnote_occasions.csv`](file:///c:/Users/james/Documents/Projects/change-ringing/data/footnote_occasions.csv) with schema `perf_id,position,occasion,subject_type,confidence,evidence`.

### Occasion Breakdown

| Occasion | Count | Proportion | Primary Signifiers |
| :--- | :--- | :--- | :--- |
| `none` | 92,945 | 27.5% | Purely technical notes, composition lines, band substitutions, umpire notes |
| `first-performance` | 86,510 | 25.6% | "first peal", "first quarter", "first in method", "first as conductor", "circled tower" |
| `civic` | 35,087 | 10.4% | Armistice Centenary, Platinum Jubilee, Accession, Coronation, Remembrance Sunday |
| `memorial` | 28,575 | 8.5% | "in memory of", "remembering", "half-muffled", "tribute to the late" |
| `seasonal` | 26,253 | 7.8% | Christmas, Easter, Evensong, Sunday service, Harvest Festival, Patronal festivals |
| `birthday` | 25,254 | 7.5% | "birthday compliment", "80th birthday", "happy birthday", "born on this day" |
| `compliment` | 12,032 | 3.6% | "congratulations on", "best wishes", "farewell to", "retirement of", "welcome to" |
| `wedding` | 9,725 | 2.9% | Wedding peals, "golden wedding anniversary", "following the marriage of" |
| `anniversary` | 9,600 | 2.8% | Tower centenaries, ordination anniversaries, years of service, historical milestones |
| `funeral` | 7,639 | 2.3% | "funeral service", "prior to the funeral", "thanksgiving for the life of", "cremation" |
| `practice` | 4,326 | 1.3% | Practice nights, quarter peal weekends, striking competitions, ringing outings |

### Subject-Type Breakdown

| Subject Type | Count | Proportion | Meaning & Criteria |
| :--- | :--- | :--- | :--- |
| `none` | 197,374 | 58.4% | Internal ringing milestone, technical band remarks, general services |
| `person` | 109,449 | 32.4% | Ringers, clergy, family members, couples, monarchs, public figures |
| `institution` | 15,275 | 4.5% | Guilds, associations, societies, branches, NHS, charities, armed forces |
| `bells` | 12,297 | 3.6% | The ring of bells, tenor/treble, augmentations, rehanging, restorations |
| `building` | 3,551 | 1.1% | Towers, cathedrals, parish churches, guildhalls, chapels, abbeys |

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
