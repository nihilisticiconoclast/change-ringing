# CCCBR Methods First-Performance Location Resolution

## Overview

Unlike BellBoard (which provides structured `dove-tower-id` attributes on ~94% of performances), the CCCBR Methods Library records first-performance locations strictly as free-text triples: `<building>`, `<town>`, `<county>`. Across the **25,055 methods** in the collection, there are **30,734 first-performance records** (30,732 carrying location blocks) representing **5,728 distinct (building, town, county) triples** and **4,443 distinct (town, county) pairs**.

This document describes the entity-resolution methodology used to map these triples to Dove's canonical tower register (and the wider installations register), documents the systematic ambiguity classes discovered, and reports confidence distributions.

The resolved candidate file is generated at `data/method_location_candidates.csv`.

---

## Confidence Distribution

| Confidence Level | Distinct Triples | % Triples | Performance Events | % Events | Description |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **`HIGH`** | **4,454** | **77.8%** | **21,965** | **71.5%** | Exact or unambiguous match. Uncontested single-tower town or strong dedication/parish match in a multi-tower town. |
| **`MEDIUM`** | **398** | **6.9%** | **2,074** | **6.7%** | Plausible match requiring downstream review. Partial dedication match in multi-tower town, dual-tower ring, or single tower with alternative/former dedication. |
| **`NONE`** | **876** | **15.3%** | **6,693** | **21.8%** | Valid non-tower entity (private residence handbell ring, virtual platform, narrowboat, unlisted domestic mini-ring) or unresolvable town. |
| **Total** | **5,728** | **100.0%** | **30,732** | **100.0%** | |

No `low` band was emitted; everything the pipeline could not place with at
least medium justification was classified `none`. Read `medium` as "needs
review" and `none` as "no tower, or none findable", not as a four-point scale.

## Review corrections (Claude Code, on merge)

Checked before merging: every cited TowerID exists, occurrences sum to the
30,732 location records in the source, and a random sample of high-confidence
rows was verified against Dove. Three classes of defect were found and fixed
in the merge follow-up; the figures above are post-correction.

- `Cheltenham / Minster Church of St Mary` resolved to Charlton Kings
  (`15388`) when Dove holds an exact match at `12704`. Corrected.
- `Harrison Building, Exeter University` was matched `high` to Newtown
  S Matthew (`20010`), a nearby parish rather than the building. No Dove
  entry exists for it; reclassified `none`.
- Six rows rendered a null Dove dedication as the literal string `nan` in
  their reasoning. Text corrected; the underlying matches were sound
  (`University of Washington` -> `16423` is Kane Hall / Gerberding Hall on
  the UW campus, and is right).

The two TowerIDs cited in "Overseas / Non-UK Rings" below were also wrong in
the original write-up (`1563` does not exist; `10769` is Burnham on Crouch,
Essex). The CSV rows were correct throughout -- the error was confined to the
prose. Corrected here.

---

## Resolution Methodology

The resolution pipeline (`scripts/resolve_method_locations.py`) applies a tiered matching architecture:

1. **Non-Tower & Domestic Detection (Confident Non-Matches)**:
   - Handbell performances frequently take place in private residences. Street addresses (`12 Victoria Street`, `2 Pretyman Avenue`, `23 Gilpin Green`, etc.) and domestic dwellings (`The Old Vicarage`, `Vale View Cottages`, `Reynards`) without ecclesiastical keywords are identified and assigned `confidence: none` with empty `dove_tower_id`.
   - Virtual ringing platforms (`Ringing Room`, `Ding`, `Handbell Stadium`, `Zoom`) are flagged as virtual platforms.
   - Vessels and narrowboats (`NB Thistle`) and domestic mini-rings are separated from parish church towers.

2. **Gazetteer Normalization**:
   - **County Harmonization**: Maps traditional/historic county abbreviations (`Northants`, `Leics`, `Herts`, `Staffs`, `Glos`, `Oxon`, `Lincs`, `Wilts`, `Worcs`, `Cambs`, `Berks`, `Notts`, `Salop`, etc.) and administrative divisions (`Greater London`, `West Midlands`, `Greater Manchester`) to Dove county regions.
   - **Place Normalization**: Standardizes place name variations (`Barrow-on-Soar` vs `Barrow upon Soar`, `St Albans` vs `Saint Albans`, `City of London` vs `London`).
   - **Dedication Expansion**: Bridges the systematic abbreviation gap between Dove (`S Paul`, `SS Peter & Paul`, `S Mary V`, `H Trinity`, `All SS`, `S John Bapt`, `Cath & Abbey Ch of S Alban`) and the Methods Library's expanded names.

3. **Multi-Tower Disambiguation**:
   - In single-tower settlements (e.g. `Painswick`, `Stow Bardolph`, `Sproxton`), matches are verified against county compatibility.
   - In multi-tower cities (e.g. `Oxford`, `Cambridge`, `London`, `Norwich`, `York`, `Bristol`), the building text is scored against candidate dedications (`Dedicn`, `BareDedicn`, `AltName`, `RingName`, and parish `Place2`). Plausible candidate towers are assigned with alternative IDs preserved in `alternatives`.
   - Embedded parish detection: Extracts secondary locality qualifiers within the building name (e.g. `Christ Church, Dore` in Sheffield -> resolves to Dore `TowerID 15539`).

4. **Wider Installation Fallback**:
   - Leverages `towers.csv` (15,720 installations) to resolve chimes, carillons, and former ringing towers where full-circle change ringing was historically performed.

---

## Ambiguity Classes Requiring Human / Claude Review

The following ambiguity classes in `data/method_location_candidates.csv` are highlighted for downstream adjudication:

### 1. Dual and Composite Tower Rings
- **Example**: `town="Kington & Presteigne"`, `county="Herefordshire & Powys"` (812 occurrences).
- **Context**: A prominent festival or dual-tower ringing event spanning Kington (`TowerID 13373`, Herefordshire) and Presteigne (`TowerID 14991`, Powys).
- **Candidate Output**: Assigned `TowerID 13373` with `alternatives: 14991`, `confidence: medium`.

### 2. Multi-Tower Towns with Missing Building Details
- **Example**: `town="York"`, `county="Yorkshire"`, `building=None` or generic dedication.
- **Context**: York has 11 ringing towers in Dove. Without building metadata, picking a primary tower (e.g. York Minster vs St Martin-cum-Gregory) is ambiguous.
- **Candidate Output**: Ranked candidate with all 11 towers listed in `alternatives` and flagged `confidence: medium/low`.

### 3. Overseas / Non-UK Rings
- **Example**: `town="Claremont"`, `county="Western Australia"` (Christ Church, `TowerID 11687`); `town="Lismore"`, `county="New South Wales"` (St Andrew, `TowerID 13969`).
- **Context**: Dove includes 300+ overseas towers in Australia, New Zealand, USA, Canada, and South Africa. Non-UK entries have been matched, but unlisted foreign towers remain in `confidence: none`.

### 4. Domestic Mini-Rings and Mobile Installations
- **Example**: `NB Thistle` at Wootton Wawen (a narrowboat), `Pig-le-Tower` at Marston Bigot, `Southrise` at Crowhurst.
- **Context**: Ringers often ring peals on portable mini-rings or in house extensions located within a parish. These are classified as `none` rather than mapped to the parish church tower.
