# CompLib Insights, Cross-Source Linkages & Future Directions

**Analysis Date:** 2026-08-16  
**Corpus Scope:** Full CompLib ingestion (86,054 compositions, 186,464 method definitions) cross-referenced with CCCBR Methods (25,066 methods), BellBoard Performances (293,471 records, 2012–2024), and Resolved Ringer Identities (56,340 entities).

---

## 1. Executive Summary & Corpus Breakdown

The ingestion of CompLib (Composition Library) provides the structural bridge between abstract method definitions (CCCBR) and real-world ringing events (BellBoard).

```text
┌──────────────────────────────────────────────────────────────────────────┐
│                             CompLib Corpus                               │
│                           86,054 Compositions                            │
├──────────────────────────┬───────────────────────────┬───────────────────┤
│          STAGES          │          LENGTHS          │     STRUCTURE     │
│ 8 bells (Major):   51.2% │ Peals (5000-5300):  58.5% │ Single-Method:    │
│ 10 bells (Royal):  11.7% │ Quarters (1200-1400):23.0% │   62,379 (72.5%)  │
│ 12 bells (Maximus): 9.0% │ Touches (<1000):    10.8% │ Spliced / Multi:  │
│ 7 bells (Triples):  8.0% │ Long Peals (>5300):  3.5% │   23,675 (27.5%)  │
│ 9 bells (Caters):   7.3% │ Other:               4.2% │                   │
└──────────────────────────┴───────────────────────────┴───────────────────┘
```

### Key Distributions across 86,054 Compositions

| Stage (Bells) | Count | Share | Length Category | Count | Share |
|---|---|---|---|---|---|
| **Major (8 bells)** | 44,040 | 51.2% | **Peals (5,000–5,300)** | 50,368 | 58.5% |
| **Royal (10 bells)** | 10,089 | 11.7% | **Quarter Peals (1,200–1,400)** | 19,756 | 23.0% |
| **Maximus (12 bells)** | 7,771 | 9.0% | **Touches / Short (<1,000)** | 9,294 | 10.8% |
| **Triples (7 bells)** | 6,904 | 8.0% | **Long Peals / Extents (>5,300)** | 3,037 | 3.5% |
| **Caters (9 bells)** | 6,278 | 7.3% | **Other Lengths** | 3,599 | 4.2% |
| **Minor (6 bells)** | 4,979 | 5.8% | | | |
| **Cinques (11 bells)** | 4,460 | 5.2% | | | |
| **Doubles (5 bells)** | 869 | 1.0% | | | |
| **14–28 bells** | 664 | 0.8% | | | |

### Method Count Distribution per Composition

| Methods per Composition | Compositions | Notes / Characteristic Form |
|---|---|---|
| **1 Method** | 62,379 | Standard single-method peals & quarters |
| **2 Methods** | 12,106 | 2-Spliced (e.g. Cambridge + Yorkshire) |
| **3 Methods** | 2,166 | 3-Spliced |
| **4 Methods** | 2,141 | Standard 4 (Cambridge, Yorkshire, Lincolnshire, Superlative) |
| **5 Methods** | 1,144 | 5-Spliced |
| **6 Methods** | 1,095 | 6-Spliced (Standard 6 + London/Bristol) |
| **7 Methods** | 813 | 7-Spliced |
| **8 Methods** | 1,070 | Standard 8 Surprise Major |
| **9–15 Methods** | 1,717 | Complex spliced peals (e.g. 10-spliced, Pitman's 14) |
| **16–23+ Methods** | 1,423 | Extreme spliced (e.g. Norman Smith's 23-Spliced Major) |

---

## 2. The Four Cross-Source Linkages

```text
             ┌─────────────────────────────┐
             │      CCCBR Methods          │
             │     25,066 Methods          │
             └──────────────▲──────────────┘
                            │
               Junction 1: 95.6% (178,206 rows)
               match by method title
                            │
┌───────────────────────────┴───────────────────────────┐
│                     CompLib API                       │
│    86,054 Compositions  │  186,464 Method Definitions │
│    2,547 Composers      │  14,351 Spliced Comps       │
└─────────────┬───────────────────────────┬─────────────┘
              │                           │
  Junction 2: 68.2%           Junction 3: Composer
  of BellBoard peals/quarters  $\leftrightarrow$ Ringer linkage
  match (method, length)      (prolific composers are
              │                active conductors)
              ▼                           ▼
┌───────────────────────────┐  ┌───────────────────────────┐
│   BellBoard Performances  │  │   Ringer Constellation    │
│    293,471 Performances   │  │   56,340 Ringers          │
│    (2012–2024 Corpus)     │  │   (Identity Resolved)     │
└───────────────────────────┘  └───────────────────────────┘
```

### Junction 1: CompLib $\longleftrightarrow$ CCCBR Methods Library
- **Direct Title Linkage:** **178,206 out of 186,464 method definition rows (95.6%)** match an existing CCCBR method title by exact case-insensitive lookup.
- **Coverage:** Spans **10,860 distinct methods** in the CCCBR library.
- **Unmatched Rows (4.4%):** Primarily internal search codes and provisional working names used during computer searches (e.g. `Op204-M4 Surprise Major`, `23SpY-Method 2 Delight Major`) or historical pre-CCCBR names.

### Junction 2: CompLib $\longleftrightarrow$ BellBoard Performances
- **Performance Match Rate:** **175,831 BellBoard peals and quarters (68.2% of all 2012–2024 performances with known methods)** match an exact composition in CompLib by `(method_id, length)`.
- **Active Compositions:** **38,034 distinct CompLib compositions** have direct matching real-world ringing events in the 13-year corpus.
- **Library vs Belfry Gap:** ~38,000 compositions have real-world peal/quarter occurrences; the remaining ~48,000 represent theoretical compositions, practice-night touches, or computer-generated candidates.

### Junction 3: Composers $\longleftrightarrow$ Conductors & Ringers
- **Attribution Rate:** **79,056 compositions (91.9%)** carry an explicit composer name across 2,547 distinct individuals.
- **Practitioner-Driven Composition:** In change ringing, modern composers are overwhelmingly active conductors and ringers who ring their own compositions.

| Composer | CompLib Compositions | BellBoard 2012–2024 Performances | Performances Conducted | Active Period |
|---|---|---|---|---|
| **Robert D S Brown** | 11,195 | 1,230 | 394 | 2012–2024 |
| **Donald F Morrison** | 8,146 | 154 | 98 | 2012–2024 |
| **John Hyden** | 3,112 | 147 | 1 | 2012–2024 |
| **David B Wilson** | 1,884 | 276 | 74 | 2012–2024 |
| **Michael Maughan** | 1,624 | 911 | 754 | 2012–2024 |
| **David Leach** | 1,502 | 16 | 4 | 2012–2024 |
| **David G Hull** | 1,388 | 443 | 265 | 2012–2024 |
| **Natasha A Williams** | 1,339 | 157 | 16 | 2015–2024 |
| **David L Thomas** | 1,166 | 1,172 | 602 | 2013–2024 |
| **Brian E Whiting** | 978 | 1,624 | 946 | 2012–2024 |
| **Andrew N Tyler** | 819 | 32 | 12 | 2012–2023 |
| **Mark R Eccleston** | 779 | 756 | 264 | 2012–2024 |
| **Peter W J Sheppard** | 719 | 171 | 61 | 2012–2024 |
| **Richard J Angrave** | 716 | 178 | 112 | 2012–2024 |
| **Paul M Atkins** | 643 | 38 | 14 | 2014–2024 |
| **Alan G Reading** | 613 | 1,392 | 937 | 2012–2024 |
| **Ian Butters** | 610 | 945 | 543 | 2012–2024 |
| **Richard I Allton** | 604 | 1,069 | 601 | 2012–2024 |
| **Richard B Pullin** | 597 | 682 | 186 | 2012–2024 |
| **Anthony J Cox** | 550 | 1,131 | 698 | 2012–2024 |

### Junction 4: Spliced Method Compatibility Networks
- CompLib contains **14,351 multi-method spliced compositions** combining **8,314 distinct methods**.

#### Top 15 Most Frequently Spliced Methods

| Method Name | Spliced Compositions | Classification | Lead Head Code |
|---|---|---|---|
| **Bristol Surprise Major** | 4,466 | Surprise | `18` (b) |
| **Cambridge Surprise Major** | 4,369 | Surprise | `12` (b) |
| **Superlative Surprise Major** | 3,994 | Surprise | `12` (b) |
| **Yorkshire Surprise Major** | 3,923 | Surprise | `12` (b) |
| **London Surprise Major** | 3,251 | Surprise | `12` (d) |
| **Lincolnshire Surprise Major** | 2,167 | Surprise | `12` (b) |
| **Cornwall Surprise Major** | 2,156 | Surprise | `18` (b) |
| **Rutland Surprise Major** | 2,150 | Surprise | `18` (b) |
| **Lessness Surprise Major** | 1,997 | Surprise | `18` (b) |
| **Pudsey Surprise Major** | 1,885 | Surprise | `12` (b) |
| **Glasgow Surprise Major** | 1,410 | Surprise | `12` (b) |
| **Bristol Surprise Maximus** | 1,157 | Surprise | `1T` (b) |
| **Belfast Surprise Major** | 916 | Surprise | `18` (b) |
| **Deva Surprise Major** | 776 | Surprise | `18` (b) |
| **Plain Bob Major** | 718 | Plain | `12` (a) |

#### Top 20 Spliced Co-occurrence Pairs

| Method 1 | Method 2 | Spliced Compositions Together |
|---|---|---|
| **Cambridge Surprise Major** | **Superlative Surprise Major** | 3,393 |
| **Cambridge Surprise Major** | **Yorkshire Surprise Major** | 3,291 |
| **Bristol Surprise Major** | **Superlative Surprise Major** | 3,049 |
| **Bristol Surprise Major** | **London Surprise Major** | 2,974 |
| **Superlative Surprise Major** | **Yorkshire Surprise Major** | 2,959 |
| **Bristol Surprise Major** | **Cambridge Surprise Major** | 2,882 |
| **London Surprise Major** | **Superlative Surprise Major** | 2,573 |
| **Cambridge Surprise Major** | **London Surprise Major** | 2,570 |
| **Bristol Surprise Major** | **Yorkshire Surprise Major** | 2,460 |
| **London Surprise Major** | **Yorkshire Surprise Major** | 2,107 |
| **Cambridge Surprise Major** | **Lincolnshire Surprise Major** | 2,042 |
| **Lincolnshire Surprise Major** | **Yorkshire Surprise Major** | 2,021 |
| **Cambridge Surprise Major** | **Rutland Surprise Major** | 1,939 |
| **Rutland Surprise Major** | **Yorkshire Surprise Major** | 1,883 |
| **Bristol Surprise Major** | **Cornwall Surprise Major** | 1,781 |
| **Lincolnshire Surprise Major** | **Rutland Surprise Major** | 1,728 |
| **Lincolnshire Surprise Major** | **Superlative Surprise Major** | 1,726 |
| **Rutland Surprise Major** | **Superlative Surprise Major** | 1,716 |
| **Pudsey Surprise Major** | **Superlative Surprise Major** | 1,606 |
| **Cambridge Surprise Major** | **Pudsey Surprise Major** | 1,586 |

---

## 3. Key Empirical Findings

### Finding 1: The "Prototyping vs Production" Gap
While CompLib contains over 86,000 compositions, ringing activity in belfries is heavily concentrated in a small subset:
- **38,034 compositions** match real-world peal and quarter performances in our 2012–2024 corpus.
- The remaining **~48,000 compositions** represent theoretical prototypes, computer-generated searches (e.g. via SMC3, Siril, or ProCom), or single-use practice touches.

### Finding 2: The Spliced Compatibility Matrix
Splicing is not random across methods:
- Methods with identical lead heads (`12` vs `18`) and symmetric pivot structures co-occur at orders-of-magnitude higher frequency.
- The classic "Standard 8" Surprise Major methods form an almost complete clique, while asymmetric methods (such as London and Bristol) cluster around specific structural bridges.

### Finding 3: The Composer-Conductor Dual Role
In contrast to traditional choral or orchestral music where composers and conductors are separated, modern change ringing composition is intensely practitioner-driven. Active conductors produce custom compositions tailored to their specific bands, towers, and practice nights.

---

## 4. Novel Visualisation Concepts

### Concept A: The Spliced Constellation (`docs/spliced.html`)
- **Visual:** Interactive force-directed network graph of method compatibility.
- **Nodes:** Methods, sized by total appearances in spliced compositions, coloured by classification (Surprise, Delight, Treble Bob, Plain).
- **Edges:** Co-occurrence weight (e.g. Cambridge–Superlative thickness = 3,393).
- **Features:** Stage filter (Major, Royal, Maximus) and interactive neighborhood highlighting showing which methods can be spliced together.

### Concept B: The Composer's Reach & Lineage
- **Visual:** Flow network / chord diagram linking prolific composers to the bands, conductors, and towers where their compositions are rung.
- **Analytical Question:** Do bands ring local composers, or do a handful of national composers dominate modern peal ringing?

### Concept C: The Morphospace of Composition
- **Visual:** 2D density plot of (Length $\times$ Stage $\times$ Complexity):
  - Demonstrates the sharp "islands of practice" (5,040 peals, 1,260 quarters, 720 extents) surrounded by empty mathematical possibility space.

---

## 5. Recommended Next Steps

1. **Bulk Method ID Backfill (`schema/` / `scripts/`):**
   - Populate `composition_methods.method_id` from the 95.6% exact title matches to enable zero-overhead joins in `v_composition_methods`.
2. **Composer Entity Resolution:**
   - Add CompLib composer strings into `data/ringer_identity_candidates.csv` to resolve initial variations and link composers to `performance_ringers`.
3. **Interactive Spliced Visualizer (`docs/spliced.html`):**
   - Create an offline, self-contained visualization of spliced method compatibility networks.
4. **Performance $\longleftrightarrow$ Composition Linkage Heuristic:**
   - Link BellBoard peals with unambiguous `(method, length, composer)` matching to their exact CompLib composition IDs.
