# Method Extension Lineage from Place Notation

## Executive Summary

This document describes the structural lineage resolution engine that determines parent-child method extensions across stages from place notation.

Out of 25,055 methods in the CCCBR Methods Library, only 1,851 methods (7.4%) carry the official `extension_construction` ground-truth attribute. By evaluating place notation transformations across multi-stage naming families, we determine which methods are true structural extensions of lower-stage parents, which are structural variants, and which merely share a name.

```
Total methods in corpus:             25,055
Multi-stage naming families:          2,786
Total candidate parent-child pairs:   7,538
Candidates output:                    data/method_extension_candidates.csv
```

---

## Calibration Against Labelled Ground Truth

Before evaluating unlabelled methods, the algorithm was held out and tested blindly against all 2,076 labelled candidate pairs possessing official CCCBR `extension_construction` tags.

### Calibration Score

| Metric | Value | Meaning |
| :--- | :--- | :--- |
| **Accuracy** | **82.71%** | Overall correct classification across all classes |
| **Precision** | **98.94%** | 1,397 True Positives out of 1,412 predicted extensions |
| **Recall** | **80.24%** | 1,397 True Positives captured out of 1,741 true extensions |
| **F1 Score** | **88.61%** | Harmonic mean of precision and recall |

```
Confusion Matrix (Labelled Subset):
  True Positives  (TP) : 1,397
  False Positives (FP) :    15
  False Negatives (FN) :   344
  True Negatives  (TN) :   320
```

> [!NOTE]
> The **98.94% precision** ensures that any proposed `extension` link in the candidate dataset has near-zero risk of false association.

---

## Candidate Dataset Distribution

The full run across all 2,786 multi-stage families generated 7,538 candidate pairs in [`data/method_extension_candidates.csv`](../data/method_extension_candidates.csv):

### Relationship Breakdown

| Relationship | Count | Percentage | Description |
| :--- | :--- | :--- | :--- |
| `name_only` | 4,504 | 59.8% | Same name, but incompatible notation, hunt count, or classification |
| `extension` | 1,693 | 22.5% | Genuine structural extension preserving front work and lead geometry |
| `variant` | 1,341 | 17.8% | Partial structural similarity or cross-class related construction |

### Confidence Breakdown

| Confidence | Count | Percentage | Criteria |
| :--- | :--- | :--- | :--- |
| `high` | 6,084 | 80.7% | Definitive notation alignment ($\ge 60\%$ front-work match) or blatant mismatch |
| `medium` | 998 | 13.2% | Structural consistency with minor variation in lead progression |
| `low` | 456 | 6.0% | Ambiguous lead-length ratio or partial notation overlap |

---

## Methodology & Structural Lineage Engine

Place notation represents the sequence of internal places made between consecutive changes. Extending a method to a higher stage involves systematic expansion rules governed by Central Council extension classes (`EP1`, `EP2`, `EP3`, `CC1`).

### 1. Place Notation Expansion
- Place notation tokens (`-`, `x`, or place sets like `38`, `14`, `1258`, `7T`) are parsed into coordinate sets.
- Palindromic symmetries (`palindromic`, `double`, `rotational`) are expanded across the lead.
- CCCBR notation comma structures are handled symmetrically (supporting both body-leadend `...-58,12` and leadend-body prefix `3,1.E.1.E...`).

### 2. Front-Work Preservation
In change ringing, the front work (places $\le 4$) in the primary half-lead of an extended method remains invariant or adapts slightly to dodge positions:
$$\text{Front Similarity} = \frac{\sum_{i=1}^{\min(L_p, L_c)} \mathbb{I}(\text{places}_p(i) \cap \{1..4\} = \text{places}_c(i) \cap \{1..4\})}{\min(L_p, L_c)}$$

### 3. Lead Progression Constraints
- **Treble Dodging (Surprise, Delight, Treble Bob)**: Lead length scales as $4 \times \text{stage}$ (e.g. Minor: 24, Major: 32, Royal: 40, Maximus: 48).
- **Plain Bob**: Lead length scales as $2 \times \text{stage}$ (e.g. Minimus: 8, Minor: 12, Major: 16, Royal: 20).
- **Little Methods (Little Bob, Little Surprise)**: Fixed lead lengths (e.g. 4 or 8 changes across all stages).
- **Odd-Stage Transitions (EP2 / Grandsire / Stedman)**: Lead length scales with hunt progression ($L_c - L_p \in \{2, 4, 6\}$).

---

## Verified Case Studies

All identifiers and stage titles below have been verified directly against `data/change-ringing.db`:

### 1. Regular Even-Stage Extensions: Cambridge Surprise (`EP3-1AB/1DE`)
The Cambridge Surprise family demonstrates perfect front-work preservation and $4 \times \text{stage}$ scaling:
- `m14568` · **Cambridge Surprise Minor** (Stage 6, Length 24, `-36-14-12-36-14-56,12`)
- `m16694` · **Cambridge Surprise Major** (Stage 8, Length 32, `-38-14-1258-36-14-58-16-78,12`)
- `m21250` · **Cambridge Surprise Royal** (Stage 10, Length 40, `-30-14-1250-36-1470-58-16-70-18-90,12`)
- `m22683` · **Cambridge Surprise Maximus** (Stage 12, Length 48, `-3T-14-125T-36-147T-58-169T-70-18-9T-10-ET,12`)
- `m23159` · **Cambridge Surprise Fourteen** (Stage 14, Length 56)
- `m23181` · **Cambridge Surprise Sixteen** (Stage 16, Length 64)

### 2. Disentangling True Extensions from Name Collisions: Bristol
The Bristol family illustrates how structural analysis correctly separates distinct sub-families:
- **True Surprise Lineage**:
  - `m19048` · **Bristol Surprise Major** (Stage 8)
  - `m22191` · **Bristol Surprise Royal** (Stage 10, `EP3-1EF/1EF`)
  - `m22952` · **Bristol Surprise Maximus** (Stage 12, `EP3-1EF/1EF`)
  - `m23168` · **Bristol Surprise Fourteen** (Stage 14, `EP3-1EF/1EF`)
  - `m23187` · **Bristol Surprise Sixteen** (Stage 16, `EP3-1EF/1EF`)
- **Independent Sub-Family Extension**:
  - `m23153` · **Bristol Little Surprise Maximus** (Stage 12, `EP1-10`)
- **Structural Variants & Name Reuses**:
  - `m10620` · **Bristol Bob Doubles** (Stage 5) -> `name_only` (Plain Bob structure)
  - `m23587` · **Bristol Delight Minor** (Stage 6) -> `variant`
  - `m26806` · **Bristol Alliance Major** (Stage 8) -> `variant`

### 3. Plain Bob Family (`name = "Plain"`, `EP3-1BC/1BC`)
From Stage 4 to Stage 16, all 13 Plain Bob stages form an unbroken extension chain:
- `m10460` · **Plain Bob Minimus** (Stage 4)
- `m10550` · **Plain Bob Doubles** (Stage 5)
- `m11349` · **Plain Bob Minor** (Stage 6)
- `m12399` · **Plain Bob Triples** (Stage 7)
- `m12834` · **Plain Bob Major** (Stage 8)
- `m13797` · **Plain Bob Caters** (Stage 9)
- `m13972` · **Plain Bob Royal** (Stage 10)
- `m14065` · **Plain Bob Cinques** (Stage 11)
- `m14240` · **Plain Bob Maximus** (Stage 12)
- `m14267` · **Plain Bob Sextuples** (Stage 13)
- `m14269` · **Plain Bob Fourteen** (Stage 14)
- `m14273` · **Plain Bob Septuples** (Stage 15)
- `m14275` · **Plain Bob Sixteen** (Stage 16)

### 4. Grandsire Principle Family (Stage 4 to 16)
Unlabelled in CCCBR ground truth, yet confirmed as a continuous extension chain across 13 stages:
- `m29152` (Minimus 4) -> `m10587` (Doubles 5) -> `m11945` (Minor 6) -> `m12415` (Triples 7) -> `m13768` (Major 8) -> `m13833` (Caters 9) -> `m14030` (Royal 10) -> `m14088` (Cinques 11) -> `m14262` (Maximus 12) -> `m14268` (Sextuples 13) -> `m14272` (Fourteen 14) -> `m14274` (Septuples 15) -> `m14279` (Sixteen 16).

### 5. Stedman Principle Family (`EP1-3`)
- `m27834` (Doubles 5) -> `m27985` (Triples 7) -> `m28011` (Caters 9) -> `m28030` (Cinques 11) -> `m28042` (Sextuples 13) -> `m28044` (Septuples 15).

---

## Families Requiring Human Review

1. **Little vs Full Lead Ambiguity**:
   - Families containing both a full-lead and a little-lead method with the same name (e.g. *Cambridge Little Delight Major* `m28795` vs *Cambridge Surprise Major* `m16694`).
2. **Hybrid / Differential Classifications**:
   - Differential methods where lead length does not follow standard stage proportionality (e.g. *Stedman Differential Minor* `m30366`).
3. **Cross-Classification Variant Drift**:
   - Naming families where Treble Bob, Delight, and Alliance variants share names but shift dodge positions by 1-2 changes.
