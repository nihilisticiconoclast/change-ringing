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
- API: https://api.complib.org
- Ingested via `scripts/ingest_complib.py` into the tables defined in `schema/005_init_complib.sql` (`compositions`, `composition_composers`, `composition_methods`).
- Coverage: Full search index (approx 85,000+ compositions).
- Location/Method linkage: Methods are supplied via free-text titles without CCCBR identifiers. The `method_id` column in `composition_methods` is a soft nullable reference designed for future resolution against the `methods` corpus.

## regions.csv scope note

`regions.csv` is a general administrative/ecclesiastical gazetteer bundled
with the Dove download (dioceses, historic counties, and non-UK divisions
such as Spanish autonomous communities and Swiss cantons) -- not specific
to bells. `dove.County` matches it at 100%; `dove.Region` at ~94%.
