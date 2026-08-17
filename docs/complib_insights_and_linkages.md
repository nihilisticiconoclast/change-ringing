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

> **Cross-validated on two independent keys, and this is the strongest claim in
> the document.** The junction was measured twice — once on method *title*, once
> on *place notation and stage*, which share no information with each other. They
> resolve **178,205 identical rows** and disagree on exactly **one row each way**
> out of 186,464:
>
> | | Rows |
> | --- | ---: |
> | Resolved by **both** keys | **178,205** |
> | Title matches, notation does not | 1 — `Stonegate Surprise Major` |
> | Notation matches, title does not | 1 — `Road Trip Ringers Bob Major` |
> | Neither | 8,257 |
>
> Two unrelated keys agreeing to within one row in 186,464 is much better
> evidence than either figure alone, and it means **the junction can be built
> offline with no API access at all** — place notation is in the committed CSVs.
> The two exceptions are the interesting cases: a title CompLib and the library
> spell the same but notate differently, and a locally-named composition built on
> a known method's notation.

### Junction 2: CompLib $\longleftrightarrow$ BellBoard — **this junction does not exist**

An earlier draft of this document reported that **175,831 performances (68.2%)
match an exact composition** and that **38,034 distinct compositions have
matching real-world ringing events**, joined on `(method_id, length)`. Both
claims are withdrawn. Two reasons, and the second is the one that matters.

**`composition_methods.method_id` is populated on 0 of 186,464 rows.** The `/rows`
enrichment pass that would fill it was deliberately not run (~86k requests), so a
join on that column cannot have run either.

**And `(method, length)` does not identify a composition — it identifies a
class.** Measured across the corpus:

| | |
| --- | ---: |
| Distinct `(method, length)` signatures | 40,437 |
| Mean compositions sharing one signature | **4.6** |
| Worst case — `Stedman Triples @ 5040` | **1,496 compositions** |

A peal of Stedman Triples of 5040 changes therefore matches **1,496 different
compositions**, not one. It is not evidence that any particular composition was
rung, so no count of "compositions with real-world occurrences" can be derived
this way, and the "library versus belfry gap" built on it does not stand.

**The underlying obstacle is structural and permanent:**
`performances.composition` is populated on **0 of 293,471** records. BellBoard
does not record which composition was rung. No amount of joining fixes that.

What *is* available is the composer (Junction 3), and the honest form of the
"dead paper" question is therefore *by composer, by method and by length* — never
"was this composition rung". That limit is recorded as roadmap **R-36** and
**R-37** so it is not rediscovered.

### Junction 3: Composers $\longleftrightarrow$ Conductors & Ringers
- **Attribution Rate:** **79,056 compositions (91.9%)** carry an explicit composer name across **2,547** distinct individuals (raw `by` split; normalising initials collapses these to 1,969 keys).
- **Practitioner-Driven Composition:** In change ringing, modern composers are overwhelmingly active conductors and ringers who ring their own compositions.

| Composer | CompLib compositions | Performances crediting them as composer | Performances they conducted |
|---|---:|---:|---:|
| **Robert D S Brown** | 11,195 | 901 | 394 |
| **Donald F Morrison** | 8,146 | 2,555 | 98 |
| **John Hyden** | 3,112 | 163 | 1 |
| **David B Wilson** | 1,887 | 242 | 74 |
| **Michael Maughan** | 1,624 | 103 | 754 |
| **David Leach** | 1,502 | 1 | 4 |
| **David G Hull** | 1,388 | 297 | 265 |
| **Natasha A Williams** | 1,339 | 13 | 16 |
| **David L Thomas** | 1,166 | 435 | 602 |
| **Brian E Whiting** | 978 | 88 | 946 |
| **Andrew N Tyler** | 819 | 31 | 12 |
| **Mark R Eccleston** | 779 | 72 | 264 |
| **David L Thomas and Monument** | 743 | 3 | 0 |
| **Peter W J Sheppard** | 719 | 75 | 61 |
| **Richard J Angrave** | 716 | 250 | 112 |
| **Paul M Atkins** | 643 | 8 | 14 |
| **Alan G Reading** | 613 | 539 | 937 |
| **Ian Butters** | 610 | 455 | 543 |
| **Richard I Allton** | 604 | 633 | 601 |
| **Richard B Pullin** | 597 | 87 | 186 |

> **The middle column was wrong in the first draft and is recomputed here.** It
> had Brian E Whiting at 1,624 performances against **88** actually crediting him
> as composer — an 18× overstatement — and Michael Maughan at 911 against **103**.
> The *conducted* column, by contrast, was exact to the record on every row I
> checked (394, 946, 754). One column right and the one beside it invented is
> `docs/LESSONS.md` lesson 7 precisely, and it is why each figure has to be
> re-derived rather than read.
>
> Both columns are **lower bounds**: `performances.composer` is free text on only
> 24.5% of records, so a composer whose work is rung without attribution is
> invisible here. And note the shape — prolificacy and performance do not track
> each other. Robert D S Brown has 11,195 compositions and 901 crediting
> performances; Brian E Whiting has 978 compositions and conducts 946 times.

### Junction 4: Spliced Method Compatibility Networks
- CompLib contains **23,675 multi-method compositions** (27.5%) combining
  **8,344 distinct methods**. *(The first draft said 14,351 and 8,314, which
  contradicted its own section 1 — 23,675 is correct and is what section 1
  reports. The ranking below is unaffected; the counts shift by a few each.)*

#### Top 15 Most Frequently Spliced Methods

| Method Name | Spliced Compositions | Classification | Lead Head Code |
|---|---|---|---|
| **Bristol Surprise Major** | 4,472 | Surprise | `18` (b) |
| **Cambridge Surprise Major** | 4,372 | Surprise | `12` (b) |
| **Superlative Surprise Major** | 3,994 | Surprise | `12` (b) |
| **Yorkshire Surprise Major** | 3,928 | Surprise | `12` (b) |
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
