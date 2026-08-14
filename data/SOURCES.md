# Data sources

> **Licensing:** this repository is dual-licensed. The root `LICENSE` (MIT)
> covers code only. `change-ringing.db` and the derived CSVs in this directory
> are CC BY-SA 4.0, inherited from Dove's Guide. See `LICENCE-DATA.md` --
> putting the data in an MIT repository does not relicense it.

Raw CSVs are not committed to this repository -- they live in Turso (see
`docs/CONNECTING.md`). This file documents where they came from and what
attribution is owed if any output of this project is published.

## Dove's Guide for Church Bell Ringers

- URL: https://dove.cccbr.org.uk/downloads
- Licence: CC BY-SA 4.0
- Files used: `bells.csv`, `changes.csv`, `dove.csv`, `founders.csv`,
  `frames.csv`, `regions.csv`, `towers.csv`
- Note: `changes.csv` is Dove's Guide's own edit log (record changes to the
  database itself), not change-ringing performance data. Do not confuse the
  two -- performance data comes from BellBoard, below.
- Attribution required under CC BY-SA 4.0: credit Dove's Guide, link to the
  licence, indicate if changes were made, and share derivative databases
  under the same licence.

## BellBoard (Ringing World)

- URL: https://bb.ringingworld.co.uk
- API docs: https://bb.ringingworld.co.uk/help/api.php
- Coverage: near-complete since 2012; earlier records exist but are
  incomplete
- Ingested via `scripts/ingest_bellboard.py` into the tables defined in
  `schema/002_init_bellboard.sql`
- Each `<performance>` carries `dove-tower-id` and `dove-ring-id` on its
  `<place>`, which resolve directly against `dove.TowerID` / `dove.RingID`.
  This is the linkage between the two corpora and it is supplied at source,
  not inferred.
- Deletions are not tracked: BellBoard does not record deletion dates, so a
  performance removed upstream persists locally until a full reload.

## CCCBR Methods Library

- URL: https://methods.cccbr.org.uk
- XML export: `https://methods.cccbr.org.uk/xml/CCCBR_methods.xml.zip`
- Format: XML (Method XML 1.0 specification, namespace `http://www.cccbr.org.uk/methods/schemas/2007/05/methods`)
- Ingested via `scripts/ingest_methods.py` into the tables defined in
  `schema/003_init_methods.sql` (`methods`, `method_performances`, and view `v_first_tower_peals`)
- Coverage: 25,055 methods and 30,734 first-performance event records across 15 event types
- Location linkage: Unlike BellBoard, first-performance `<location>` records are free text
  (`<building>`, `<town>`, `<county>`) without Dove IDs. The `dove_tower_id` column is a
  soft reference resolved via the cross-referencing task in `docs/tasks/gemini-location-resolution.md`.

## CompLib (Composition Library)

- URL: https://complib.org
- Not yet ingested
- **Correction (2026-08-14):** this file previously said "API: documented".
  `https://complib.org/api` returns 571 bytes -- a client-rendered application
  shell with no documentation in the HTML. There may well be an API, but its
  existence has not been established from that page, and Vibe's Task 2 brief was
  written on the earlier assumption. Establish what the API actually offers
  before designing around it, which is what the brief itself says to do.

## Felstead (CCCBR peal records)

- URL: https://felstead.cccbr.org.uk (redirects from felstead.org.uk)
- **Not ingested, and not to be ingested without permission.** See
  `docs/felstead-enquiry.md`.
- Coverage: states "over 360,000 towerbell peals". The tower sampled
  (TowerBase 2606, Huntsham) begins Tue 2 Feb 1875. Peals only -- no quarter
  peals, no service ringing, no tolling, so it is not a substitute for the
  BellBoard backfill.
- Licence: **none stated.** Not on the index, `intro.html` or `other.php`. There
  is no robots.txt either (404). Dove, from the same body, is CC BY-SA 4.0, but
  that is not evidence about this.
- Provenance: Canon K W H Felstead's handwritten card index, bequeathed to the
  Central Council, transcribed by roughly 100 volunteers over several thousand
  hours. Maintained by the ICT and Peal Records Committees.
- Linkage: `tbid.php?tid=<TowerBase ID>` -- the identifier BellBoard publishes as
  `towerbase-id`, present on 79,918 of our 96,067 performances across 5,600
  distinct towers. It is a **different identifier space from Dove's `TowerID`**:
  zero of our 5,600 values resolve against `dove.TowerID`, which is why the
  column had been sitting unused. Twelve sampled identifiers were probed
  manually and all twelve resolved, returning 41-783 peals each. `rpp=1000`
  returns a tower's whole history in one request.
- Fields per peal: peal number, PB-ID, status, full date rung, method, and a
  bibliographic citation (`CB v.127; BL 13.ii.75`, `RW 5009.0421`) -- *Church
  Bells*, *Bell News* and *The Ringing World*.
- Known discrepancy to report if permission is granted: BellBoard records
  TowerBase 7924 for Crowhurst, The Forewood Ring, East Sussex; Felstead's place
  search returns 7898 for "Crowhurst, Forewood Ring, Suffolk".

## regions.csv scope note

`regions.csv` is a general administrative/ecclesiastical gazetteer bundled
with the Dove download (dioceses, historic counties, and non-UK divisions
such as Spanish autonomous communities and Swiss cantons) -- not specific
to bells. `dove.County` matches it at 100%; `dove.Region` at ~94%.
