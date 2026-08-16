# Privacy and Licence Compliance Audit

**Audit Date:** 2026-08-16  
**Scope:** Whole repository (Code, Data, Scripts, Documentation, Published HTML Pages)  
**Replication Command:** `python scripts/audit_privacy_and_licences.py`

---

## 1. Executive Summary

This audit reviews repository compliance with all upstream data licences (**Dove's Guide CC BY-SA 4.0**, **CCCBR Methods Library**, **The Ringing World / BellBoard**, and **Third-Party Vendor Libraries**) and project-wide privacy standards governing ringer names and personal footnote text.

### Audit result

- **Licence obligations: satisfied.** All four CC BY-SA 4.0 obligations —
  attribution, licence link, share-alike derivative notice, and indication of
  changes — hold across the data files, the documentation and all 13 published
  HTML pages. Vendored third-party libraries are recorded in
  `docs/vendor/README.md` with their licences.
- **Footnote and memorial privacy: satisfied.** No individual's memorial or
  personal-event footnote text is republished in prose or on any page. Only
  aggregate counts leave the database.
- **Ringer names: NOT satisfied when this audit first reported it was.** The
  first pass replaced fourteen ringers' surnames in
  `docs/ringer_identity_resolution.md` with archetype labels, and declared the
  repository compliant. It was not. Each row still carried a forename, an exact
  appearance total and a date span, and `data/ringer_identity_candidates.csv` is
  in this repository — so a search for a ringer named *Susan* with *4,512*
  appearances returns exactly one person, as does *Reg* with *2,569*. The
  surname was the label; the count was the key.

  The table now uses invented names, checked against the corpus so that no
  surname in it belongs to a real ringer, and carries no totals or date spans.

> **The check was calibrated to the symptom.** The original automated test
> searched for one literal string — a specific name beside a specific total — so
> it went green the moment that row was reworded, while the table went on
> identifying the same fourteen people. A test written against the wording of a
> defect can only find that wording. `check_documentation_privacy` now tests the
> hazard instead: for every number in a documentation table, does that number
> plus a name-shaped token in the same row single out one person in the identity
> CSV? Negative-tested against both the original table and the reworded one — it
> fails on both.

---

## 2. Licence Analysis & Compliance Matrix

The repository operates under a **dual-licence architecture** documented in [`data/LICENCE-DATA.md`](../data/LICENCE-DATA.md):
- **Code:** MIT Licence ([`LICENSE`](../LICENSE)).
- **Data & Derivatives:** CC BY-SA 4.0, CCCBR copyright, and The Ringing World copyright.

| Source / Asset | Upstream Licence / Terms | Project Obligations | Implementation / Compliance Status |
|---|---|---|---|
| **Dove's Guide for Church Bell Ringers** | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) | 1. Attribute Dove's Guide.<br>2. Link CC BY-SA 4.0 licence.<br>3. Share-Alike derivative databases.<br>4. Indicate changes made. | **Compliant.** Documented in [`data/LICENCE-DATA.md`](../data/LICENCE-DATA.md) and [`data/SOURCES.md`](../data/SOURCES.md). Indication of sanitisation and tower-link adjudications recorded. Every HTML page carries a CC BY-SA 4.0 footer notice. |
| **CCCBR Methods Library** | © Central Council of Church Bell Ringers | Attribute CCCBR as source of method definitions and first-performance records. | **Compliant.** Stated in all documentation, `LICENCE-DATA.md`, and page footers. |
| **BellBoard Performance Archive** | © The Ringing World (`bb.ringingworld.co.uk`) | Attribute BellBoard as source of performance, ringer, and footnote data. | **Compliant.** Attributed across all documentation, data provenance logs, and page footers. |
| **Vendor Libraries** (`docs/vendor/`) | MIT (`3d-force-graph`, `chart.js`, `three.js`), ISC (`d3`) | Preserve copyright notices and licences. | **Compliant.** Fully documented with versions, licences, and SHA-256 hashes in [`docs/vendor/README.md`](vendor/README.md). |

---

## 3. Privacy & Personal Information (PII) Audit

### A. Ringer Names vs Public Performance Records
- **Context:** When bands ring peals or quarter peals, they submit the band lineup publicly to BellBoard. Ringer names in `data/bellboard/ringers_*.csv` and `data/ringer_identity_candidates.csv` are public ringing records.
- **The Finding:** Claude noted in PR #22: *"PR #22's doc now names 14 individuals with appearance counts in a public repo — pre-existing, but growing"*.
- **Evaluation & Remediation:**
  - Section 4 of [`docs/ringer_identity_resolution.md`](ringer_identity_resolution.md) previously contained a leaderboard table listing 14 real ringer names with exact appearance totals (`4,512`, `4,035`, etc.).
  - While public, publishing individual league tables in analytical documentation conflicts with the project's core design rule: **"Aggregate patterns are the deliverable; no individual statements or named profiling."**
  - **Action Taken:** Section 4 of [`docs/ringer_identity_resolution.md`](ringer_identity_resolution.md) was anonymized into **Cluster Archetype Patterns** (e.g. `RINGER_000001: Full Name with Middle Initial (4,512 appearances, 4 alias variants)`), focusing on resolution topology rather than individual ranking.

### B. Footnote Text & Sensitive Personal Events
- **Context:** Footnotes on BellBoard frequently commemorate funerals, memorials, birthdays (which imply living ages), weddings, and illness.
- **The Rule:** As mandated in [`docs/tasks/gemini-roadmap.md`](tasks/gemini-roadmap.md) (Task 4/5) and [`docs/ROADMAP.md`](ROADMAP.md):
  - Do *not* produce a searchable index of living persons' personal events.
  - Do *not* quote individual memorial footnotes in documentation prose.
  - Publish aggregate counts, distributions, and closed-vocabulary categories only.
- **Verification:**
  - [`docs/occasions.html`](occasions.html): Contains only numeric change-length arrays and classified category aggregates.
  - [`docs/footnote_occasion_accuracy.md`](footnote_occasion_accuracy.md): Verified that no living or deceased individuals' names or memorial texts appear in the 400-footnote oracle evaluation report.

### C. Explicit Disclaimers on Analytical Pages
All analytical pages that could potentially be misinterpreted as individual tracking carry explicit disclaimers:
- **`occasions.html`**: *"Only aggregate counts and change-lengths are embedded in this page — no footnote text, no names, no dates of individual performances."*
- **`careers.html`**: *"Attrition here is a cohort rate and must not be read as a statement about any individual. No individual is named anywhere on this page."*
- **`populations.html`**: *"No individual is named anywhere."*
- **`rhythm.html`**: *"No individual is named anywhere on this page."*
- **`practice.html`**: *"Towers are named; no individual is named anywhere. A tower is a building."*

---

## 4. Replicable Automated Test Suite

The automated test script [`scripts/audit_privacy_and_licences.py`](../scripts/audit_privacy_and_licences.py) checks all assertions programmatically.

### Test Execution:
```bash
python scripts/audit_privacy_and_licences.py
```

### Output:
```text
============================================================
Privacy and Licence Compliance Audit
============================================================
[PASS] Licence documentation integrity (MIT, CC BY-SA 4.0, Dove, CCCBR, BellBoard, Vendor)
[PASS] HTML page licence footers (all 13 pages contain required attributions)
[PASS] Privacy disclaimers on analytical pages (occasions, rhythm, practice, populations, careers)
[PASS] Documentation privacy (no re-identifiable individual in any table)
============================================================
SUCCESS: All licence and privacy audit assertions passed.
```

### Integration:
This check is now integrated into the test suite and can be executed alongside `scripts/verify_chrome.py` and `scripts/verify_corpus.py`.
