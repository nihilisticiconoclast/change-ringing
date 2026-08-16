# CompLib Insights, Cross-Source Linkages & Future Directions

**Analysis Date:** 2026-08-16  
**Corpus Scope:** Full CompLib ingestion (86,054 compositions, 186,464 method definitions) cross-referenced with CCCBR Methods (25,066 methods), BellBoard Performances (293,471 records, 2012–2024), and Resolved Ringer Identities (56,340 entities).

---

## 1. Executive Summary & Corpus Breakdown

The ingestion of CompLib (Composition Library) provides the structural bridge between abstract method definitions (CCCBR) and real-world ringing events (BellBoard).

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

- **Single-Method Compositions:** 62,379 (72.5%)
- **Spliced / Multi-Method Compositions:** 23,675 (27.5% across 14,351 distinct composition groupings)

---

## 2. The Four Cross-Source Linkages

### Junction 1: CompLib $\longleftrightarrow$ CCCBR Methods Library
- **Direct Title Linkage:** 178,206 out of 186,464 method definition rows (**95.6%**) match an existing CCCBR method title by exact case-insensitive lookup.
- **Coverage:** Spans **10,860 distinct methods** in the CCCBR library.
- **Unmatched Rows (4.4%):** Primarily internal search codes and provisional working names used during computer searches (e.g. `Op204-M4 Surprise Major`, `23SpY-Method 2 Delight Major`) or historical pre-CCCBR names.

### Junction 2: CompLib $\longleftrightarrow$ BellBoard Performances
- **Performance Match Rate:** 175,831 BellBoard peals and quarters (**68.2% of all 2012–2024 performances with known methods**) match an exact composition in CompLib by `(method_id, length)`.
- **Active Compositions:** **38,034 distinct CompLib compositions** have direct matching real-world ringing events in the 13-year corpus.
- **Library vs Belfry Gap:** ~38,000 compositions have real-world peal/quarter occurrences; the remaining ~48,000 represent theoretical compositions, practice-night touches, or computer-generated candidates.

### Junction 3: Composers $\longleftrightarrow$ Conductors & Ringers
- **Attribution Rate:** 79,056 compositions (**91.9%**) carry an explicit composer name across 2,547 distinct individuals.
- **Practitioner-Driven Composition:** In change ringing, modern composers are overwhelmingly active conductors and ringers who ring their own compositions.

| Composer | CompLib Compositions | BellBoard 2012–2024 Performances | Performances Conducted | Active Period |
|---|---|---|---|---|
| **Robert D S Brown** | 11,195 | 1,230 | 394 | 2012–2024 |
| **Donald F Morrison** | 8,146 | 154 | 98 | 2012–2024 |
| **John Hyden** | 3,112 | 147 | 1 | 2012–2024 |
| **David B Wilson** | 1,884 | 276 | 74 | 2012–2024 |
| **Michael Maughan** | 1,624 | 911 | 754 | 2012–2024 |
| **Brian E Whiting** | 978 | 1,624 | 946 | 2012–2024 |
| **Alan G Reading** | 613 | 1,392 | 937 | 2012–2024 |
| **Richard I Allton** | 604 | 1,069 | 601 | 2012–2024 |
| **Anthony J Cox** | 550 | 1,131 | 698 | 2012–2024 |

### Junction 4: Spliced Method Compatibility Networks
- CompLib contains 14,351 multi-method spliced compositions combining 8,314 distinct methods.
- **Top Co-occurring Method Pairs:**
  1. *Cambridge Surprise Major + Superlative Surprise Major*: **3,393 compositions**
  2. *Cambridge Surprise Major + Yorkshire Surprise Major*: **3,291 compositions**
  3. *Bristol Surprise Major + Superlative Surprise Major*: **3,049 compositions**
  4. *Bristol Surprise Major + London Surprise Major*: **2,974 compositions**
  5. *Superlative Surprise Major + Yorkshire Surprise Major*: **2,959 compositions**
  6. *Bristol Surprise Major + Cambridge Surprise Major*: **2,882 compositions**
- **Structural Constraint:** Splicing is strongly governed by place notation compatibility (matching lead ends `12` vs `18`, identical half-lead works, and symmetry).

---

## 3. Novel Visualisation Concepts

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

## 4. Recommended Next Steps

1. **Bulk Method ID Backfill (`schema/` / `scripts/`):**
   - Populate `composition_methods.method_id` from the 95.6% exact title matches to enable zero-overhead joins in `v_composition_methods`.
2. **Composer Entity Resolution:**
   - Add CompLib composer strings into `data/ringer_identity_candidates.csv` to resolve initial variations and link composers to `performance_ringers`.
3. **Interactive Spliced Visualizer (`docs/spliced.html`):**
   - Create an offline, self-contained visualization of spliced method compatibility networks.
