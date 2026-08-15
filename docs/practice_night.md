# Practice Night Agreement: Dove's Register vs BellBoard's Record

**Deliverable for Gemini Task 6:** Cross-source validation of Dove's stated practice night against actual ringing distributions across **293,471 BellBoard performances** (2012–2024).

- **SQL Finding Query:** [`queries/findings/practice_night_agreement.sql`](file:///c:/Users/james/Documents/Projects/change-ringing/queries/findings/practice_night_agreement.sql)

---

## 1. Executive Summary & Findings

Dove's Guide records a practice night for **3,515 towers**. BellBoard records dated performances across 13 years. Cross-referencing these two independent corpora reveals:

- **Overall Agreement (Non-Sunday Short Ringing):** Across **1,404 active towers** (>= 20 non-Sunday short performances), the busiest non-Sunday ringing night matches Dove's stated night for **27.7% of towers** (389 / 1,404), compared to a chance baseline of **16.7%** (1 in 6).
- **Weekday Concentration (Mon–Fri Only):** When Saturday weekend peal/quarter attempts are separated, agreement jumps to **44.0%** (567 / 1,288 active towers), over **2.2× the chance baseline (20.0%)**, with an average **30.2%** of all weekday ringing concentrated on the single stated practice evening.
- **Activity Stratification Effect:** The busier a tower is, the more likely its quarter peals coincide with its official Dove practice evening:
  - Low activity (20–49 perfs): **26.1%** match rate
  - High activity (100–199 perfs): **28.1%** match rate
  - Very high activity (200+ perfs): **43.8%** match rate (and >55% of weekday ringing)

---

## 2. Essential Confound & Data Caveats

> [!WARNING]
> ### 1. The Sunday Service Confound
> Sunday service ringing accounts for the vast majority of short performances (quarter peals and touches) across almost every active tower in the country. Comparing the outright busiest day of the week yields an artificial agreement rate below 16% simply because Sunday overwhelms the schedule. **Sunday ringing must be excluded** to evaluate weekday practice patterns.

> [!IMPORTANT]
> ### 2. The Reporting Proxy Caveat
> BellBoard records **published performances** (overwhelmingly quarter peals and peals). Routine practice night ringing (rounds and method touches that are not scored as quarters) is almost never recorded on BellBoard.
> 
> Therefore, this study measures where **reported quarter peals cluster**, which serves as a proxy for practice activity. The **27.7% (non-Sunday) / 44.0% (weekday)** figures represent a lower bound on alignment, **NOT an estimate of inaccurate Dove entries**. A tower that holds its regular practice on Tuesday but rings its celebratory quarter peals on Saturday morning will register 0% alignment despite Dove's record being 100% correct.

---

## 3. Parsing Dove's `Practice` Column

Of Dove's 7,262 installation records (7,249 distinct towers), **3,515 towers (48.5%)** carry a non-empty `Practice` string.

| Parse Category | Count | Proportion | Examples |
| :--- | :--- | :--- | :--- |
| **Unambiguous Single Day** | **2,968** | **84.4%** | `Mon`, `Tue 19:00`, `Wed`, `Thu (exc Bank Hols)`, `Fri 19:30` |
| **Conditional / Alternating** | **540** | **15.4%** | `PN: by arrangement`, `Thu (alt)`, `Tue (1st, 3rd, 5th)`, `Wed (2nd, 4th)` |
| **Other / Unparsed** | **7** | **0.2%** | Idiosyncratic multi-line text or unstated notes |
| **Total Populated** | **3,515** | **100.0%** | |

*Only the 2,968 unambiguous single-day entries were included in the empirical matching cohort.*

---

## 4. Stratification by Activity Volume

Evaluating non-Sunday short performances (<5,000 changes) across activity tiers:

| Activity Tier | Active Towers ($N$) | Stated Night is Busiest | Busiest Match Rate | Mean Share on Stated Night |
| :--- | :--- | :--- | :--- | :--- |
| **20–49 perfs (Low)** | 955 | 249 | **26.1%** | 20.8% |
| **50–99 perfs (Moderate)** | 321 | 99 | **30.8%** | 24.5% |
| **100–199 perfs (High)** | 96 | 27 | **28.1%** | 22.4% |
| **200+ perfs (Very High)** | 32 | 14 | **43.8%** | 35.3% |
| **Total Cohort (>= 20)** | **1,404** | **389** | **27.7%** | **22.1%** |

*(Chance baseline across Mon–Sat is 16.7%; flat distribution share is 16.7%)*

---

## 5. Case Studies: High vs Low Alignment

### Top Aligned Towers (Dedicated Practice-Night Quarter Bands)
Towers where nearly all non-weekend ringing takes place on the official practice evening:

1. **Pettistree, Suffolk** (*S Peter & S Paul*, TowerID 13016)
   - Stated Practice: `Wed`
   - Total Non-Sunday Quarters: 608
   - Ringing on Wednesday: **566 (93.1%)**
2. **Frodsham, Cheshire** (*S Lawrence*, TowerID 15988)
   - Stated Practice: `Thu`
   - Total Non-Sunday Quarters: 469
   - Ringing on Thursday: **454 (96.9%)**
3. **Barnes, Greater London** (*S Mary*, TowerID 11169)
   - Stated Practice: `Tue 20:00`
   - Total Non-Sunday Quarters: 388
   - Ringing on Tuesday: **349 (89.9%)**

### Active Towers with Low Alignment (Weekend / Dedicated Circuit Ringing)
Towers with high quarter peal activity that rarely falls on the stated practice night:

1. **Perth, Scotland** (*Bell Tower*, TowerID 15480)
   - Stated Practice: `Tue`
   - Total Non-Sunday Quarters: 367 (largely concentrated on Friday/Saturday visiting tours; 0 on Tuesday).
2. **Derby, Derbyshire** (*Cathedral of All Saints*, TowerID 10354)
   - Stated Practice: `Mon`
   - Total Non-Sunday Quarters: 207 (dominant ringing day is Saturday at 68.1%; Monday practice accounts for 7.7%).
3. **Escrick, North Yorkshire** (*S Helen*, TowerID 11686)
   - Stated Practice: `Mon`
   - Total Non-Sunday Quarters: 236 (dominant ringing day is Saturday at 72.5%; Monday accounts for 7.2%).
