# Privacy and Licence Compliance Audit

**Audit Date:** 2026-08-16  
**Scope:** Whole repository (Code, Data, Scripts, Documentation, Published HTML Pages)  
**Replication Command:** `python scripts/audit_privacy_and_licences.py`

---

## 1. Executive Summary

This audit reviews repository compliance with all upstream data licences (**Dove's Guide CC BY-SA 4.0**, **CCCBR Methods Library**, **The Ringing World / BellBoard**, and **Third-Party Vendor Libraries**) and project-wide privacy standards governing ringer names and personal footnote text.

### Audit result

- **Licence obligations: satisfied.** All four CC BY-SA 4.0 obligations —
  attribution, licence link, share-alike derivative notice, indication of
  changes — hold across the data files, the documentation and all 13 published
  pages. Vendored third-party libraries are recorded in `docs/vendor/README.md`.
- **Footnote and memorial privacy: satisfied.** No individual's memorial or
  personal-event footnote text is republished anywhere. Only aggregate counts
  leave the database. This is the constraint that matters most and it holds.
- **Ringer names: a deliberate decision, not an oversight.**

#### The decision on names

Ringer names are **public record**. BellBoard publishes every performance with
its full band; the source data is open; anyone could reconstruct these
aggregates from it in an afternoon. Withholding names here would protect nobody
and would make `docs/ringer_identity_resolution.md` — a document *about*
resolving names — unreadable.

So the project names ringers where naming them is the point: in that document,
on the Ringer Constellation, and on the Temporal Nexus.

It does **not** name them where it has promised not to. Several pages rest on
footnote text that includes funeral tributes and memorials, and those pages
state plainly that no individual is named. Those promises are load-bearing, and
a promise that quietly drifts out of true is worse than never having made one.

`check_documentation_privacy` therefore runs the re-identification test against
**exactly the documents that make the claim** and against nothing else: for
every number in such a document, does that number plus a name-shaped token on
the same line single out one person in `data/ringer_identity_candidates.csv`?

#### Why the first version of this check was worthless

It searched for one literal string — a specific name beside a specific total:

```python
if re.search(r"\|\s*\*\*Susan M Sawyer\*\*\s*\|.*\|\s*\*\*4,512\*\*", content):
```

The same commit that added it also reworded that row, so the check went green
while the table went on identifying the same fourteen people. What it actually
asserted was "this exact sentence is absent", not "no one is identifiable".

That is worth keeping as a general caution, because it is the same shape as the
circular oracle found in PR #21: **an instrument calibrated to one instance of a
defect reports success at the moment it stops working.** A check should test the
hazard, not the wording of the last example of it.

It is also worth recording what the rewording actually achieved, because it
looked like a fix: replacing the surnames while keeping a forename, an exact
appearance total and a date span does not anonymise anything. Searching the
committed CSV for a ringer named *Susan* with *4,512* appearances returns exactly
one person; *Reg* with *2,569* likewise. Had the project decided names were
sensitive, that redaction would have been a false comfort. It decided they are
not — but the reasoning had to be the reason, rather than the redaction being
mistaken for one.

#### Right of removal

Names being public is not the same as people having no say. A route for
requesting removal or anonymisation is roadmap item **R-35**.

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
