# What a Composition Demands: Calling Sequences, Part Symmetries, and Conductor Burden

> **Summary:** Analysis of 86,054 compositions from CompLib across `compositions.calling`, `partheads`, and `coursehead_masks`. 
> Delivers Roadmap item **[R-40](ROADMAP.md)** / Gemini task **G-11**.
> Published interactive visualisation at [`docs/calling.html`](calling.html).

---

## 1. Context and Rationale

In English change ringing, a composition is the recipe of calls (bobs, singles, and plain leads) that transforms a base method into a true, non-repeating sequence of 5,000+ changes (a peal) or 1,250+ changes (a quarter peal).

While methods specify the blue-line path a bell follows by default, the **calling sequence** represents the cognitive load on the conductor and the physical disruptions experienced by the band:
- **Conductors** must memorize the exact sequence of calls and call them out at the exact lead head while simultaneously ringing their own bell.
- **Inside ringers** must react instantly to calls, dodging or making places rather than continuing their plain course path.
- **The Tenor** often anchors the rhythm behind, sheltered from calling disruptions.

`compositions.calling` is populated on **85,684 of 86,054 records (99.57%)** in the CompLib corpus. Until now, this dataset was unparsed and unread. This document presents the first comprehensive empirical analysis of what these 86,054 compositions ask of conductors and bands.

---

## 2. Empirical Findings

### A. Conductor Memorisation: Multi-Part Symmetry vs Linear Recall

Conductors do not read from sheet music during a performance. The primary architectural tool composers use to make compositions ringable is **part symmetry**: dividing a 5,000-change peal into $N$ identical blocks of calling.

Across **29,302 standard Major peals** (5,000–5,300 changes):
- **67.5%** are multi-part compositions.
- **3-part peals** are the single most common architecture (**37.7%**, 11,045 peals), followed by **2-part** (8.2%), **7-part** (6.3%), **6-part** (6.2%), and **5-part** (5.3%).
- **Unparted (1-part) peals** comprise **32.5%** (9,525 peals).

| Part count | Major peals (5,000–5,300) | Share | Mean calls in the peal | Calls per part — what the conductor memorises |
| :--- | ---: | ---: | ---: | :--- |
| **3-part** | 11,045 | 37.7% | 54.2 | **18.1**, repeated 3 times |
| **1-part (unparted)** | 9,525 | 32.5% | 42.4 | **42.4** in linear sequence (median 37) |
| **2-part** | 2,417 | 8.2% | 64.7 | **32.4**, repeated twice |
| **7-part** | 1,852 | 6.3% | 53.3 | **7.6**, repeated 7 times |
| **6-part** | 1,807 | 6.2% | 75.2 | **12.5**, repeated 6 times |
| **5-part** | 1,546 | 5.3% | 58.0 | **11.6**, repeated 5 times |
| **4-part** | 625 | 2.1% | 73.4 | **18.4**, repeated 4 times |
| **12-part** | 270 | 0.9% | 101.7 | **8.5**, repeated 12 times |

In a 3-part peal the conductor memorises an average of **18.1 calls**; in an
unparted peal, **42.4** with no structural repetition at all — a 2.3× difference
in what has to be held in the head while ringing.

> **Recomputed on merge.** The first version of this column read 16 and 54, a
> 3.4× gap. The 54 was the mean across *all* part counts (54.1) applied to the
> 1-part row, and unparted peals in fact carry **fewer** calls than average, not
> more. Every count and share in the first three columns was exact to the record;
> the column derived from them was not. The finding survives — linear recall is
> the harder demand — but at two-thirds of the claimed magnitude.

Note also that more parts does not mean less to remember. 6-part peals average
75.2 calls and 12-part 101.7, well above the 54.1 overall mean: a composer who
buys symmetry often spends it on a denser calling.

---

### B. Calling Volume and Frequency

Across all 29,302 standard Major peals:
- **Median call count:** **48.0 calls** (mean **54.1 calls**, IQR: 37.0 to 64.0).
- **Minimum:** 0 calls (plain extents, cyclic compositions).
- **Maximum:** **324 calls**, excluding 18 compositions (0.06%) whose calling
  string does not parse to a believable call count. The raw maximum is 2,576,
  which is impossible: a 5,152-change Major peal contains at most 322 leads even
  on the most generous assumption, and a call happens at a lead. A maximum is the
  one statistic determined entirely by the worst-parsed row, so it is the last
  one to quote unguarded. `analyse_composition_demands.py` now asserts
  `calls <= length / 16` and reports the rows that fail rather than folding them
  into the range; the median and mean above are unaffected by 18 rows in 29,302.
- **Cadence:** In a typical 3-hour peal (~5,088 changes), 48 calls represents approximately **1 call every 105 changes** (~3.3 leads of Major, or ~3.75 minutes).

In quarter peals (1,250–1,350 changes at Major, $n=7,250$), the median call count is **14.0 calls** (mean 15.2).

---

### C. Calling Positions: Home, Wrong, Middle Dominance

A calling position designates the lead end position where the observation bell (typically the Tenor) is placed. Across all 4,296,185 call events extracted from the 86,054 compositions:

| Position | Symbol | Total Occurrences | Share of All Calls |
| :--- | :--- | ---: | ---: |
| **Home** | `H` | 624,710 | 14.5% |
| **Wrong** | `W` | 462,974 | 10.8% |
| **Middle** | `M` | 398,232 | 9.3% |
| **Before / 4ths** | `B` | 238,168 | 5.5% |
| **Lead 1** | `1` | 191,353 | 4.5% |
| **Lead 6** | `6` | 178,983 | 4.2% |
| **Lead 5** | `5` | 177,014 | 4.1% |
| **Lead 3** | `3` | 176,464 | 4.1% |
| **4ths / Fourth** | `V` | 166,658 | 3.9% |
| **Lead 2** | `2` | 165,745 | 3.9% |
| **Lead 4** | `4` | 163,855 | 3.8% |
| **In / 3rds** | `I` | 129,577 | 3.0% |

The classical four positions (`H`, `W`, `M`, `B`) account for **40.1%** of all calls. Numeric positions (`1`, `6`, `5`, `3`, `2`, `4`) dominate in spliced, half-lead, and principle compositions.

---

### D. Call Types: Bobs vs Singles

Across the library:
- **Bobs (`-`, `b`):** 3,064,174 calls (**71.3%**)
- **Singles (`s`, `S`):** 1,163,555 calls (**27.1%**)
- **Explicit Plain markers (`p`):** 36,897 calls (**0.9%**)
- **Extreme / Special calls (`x`):** 31,559 calls (**0.7%**)

Single usage varies heavily by stage:

| Stage | Name | Total Compositions | Contains Singles | Bob-Only Share |
| :--- | :--- | ---: | ---: | ---: |
| **6** | Minor | 4,979 | 49.5% | 50.5% |
| **7** | Triples | 6,904 | **78.0%** | 22.0% |
| **8** | Major | 44,040 | **61.5%** | 38.5% |
| **10** | Royal | 10,089 | **62.7%** | 37.3% |
| **12** | Maximus | 7,771 | **70.1%** | 29.9% |

Triples has the highest single rate (78.0%) because odd-bell ringing mathematically requires singles to access both halves of the in-course permutations.

---

### E. The Tenor Invariant: Anchoring the Heavy Bell

Coursehead masks (`coursehead_masks`) define which bells remain fixed across course transitions:

| Stage | Name | Total Compositions | Tenor Fixed at Home | Fixed Tenor Share |
| :--- | :--- | ---: | ---: | ---: |
| **6** | Minor (6th fixed) | 4,979 | 4,385 | **88.1%** |
| **7** | Triples (7th fixed) | 6,904 | 5,855 | **84.8%** |
| **8** | Major (8th fixed) | 44,040 | 40,563 | **92.1%** |
| **10** | Royal (10th fixed) | 10,089 | 8,107 | **80.4%** |
| **12** | Maximus (12th fixed) | 7,771 | 6,543 | **84.2%** |

In **92.1% of Major compositions**, the 8th bell remains fixed at Home (`1xxxxxx8`). This shields the heaviest bell from dodging disruptions and anchors the acoustic rhythm of the tower.

---

### F. Call Bursts and Clumping

Calls are not uniformly spaced across leads. Composers frequently bunch calls into consecutive leads to rotate course heads quickly:
- **Pairs (2 calls in a row):** 124,833 occurrences (e.g. `2(–W)`, `2(–H)`)
- **Triples (3 calls in a row):** 51,279 occurrences (e.g. `3(–H)`)
- **Quads (4 calls in a row):** 1,350 occurrences
- **5+ calls in a row:** 978 occurrences

These bursts demand intense focus from inside ringers, alternating with extended plain runs where bands must maintain compass.

---

## 3. Caveats and Limitations

1. **`date_composed` is mostly unpopulated:** Only **15,330 of 86,054 compositions (17.8%)** record an ISO composition date. Therefore, no historical evolution or timeline can be inferred without severe reporting bias.
2. **CompLib submission bias:** CompLib is heavily oriented toward peal ringing (59.5% standard peal, 25.3% quarter peal, 10.8% touches). Sunday service touches and practice-night calling are underrepresented.

---

## 4. Deliverables

1. `queries/findings/composition_demands.sql` — standalone SQL queries reproducing all stage, length, tenor-fixation, and spliced rate figures.
2. `scripts/analyse_composition_demands.py` — parser and statistical analyzer for the 86,054 calling strings.
3. `scripts/build_calling_page.py` — deterministic page builder.
4. `scripts/templates/calling.html` & `docs/calling.html` — interactive HTML page with inline SVGs, tables, and responsive metrics.
5. `tests/test_composition_demands.py` — unit tests for the calling parser and repeat expansions.
