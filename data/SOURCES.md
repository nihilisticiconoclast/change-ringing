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
- Completeness check: `export.php` carries no row count of its own, and a
  truncated response page is indistinguishable from a genuine last page.
  `search.php?from=...&to=...` renders an independent count ("Found N
  performances") in its HTML, which `scripts/backfill_bellboard.py` uses as
  a per-window expected count: a window fetched short of it is retried and
  failed rather than checkpointed.
- Counts measured 2026-08-09: 25,859 for 2023, 25,267 for 2024, 336,654 for
  2012-01-01 to 2026-08-09. Re-measured 2026-08-15: 2024 still 25,267, and the
  2012-onward range now reads **336,689**. The corpus grows retrospectively, so
  any figure here is true of a date, not of the source.
- **`search.php` and `export.php` agree exactly.** Measured 2026-08-15 across six
  week-long windows spread over 2021-2024, 2,588 performances in total: zero
  difference in every window. The gate's tolerance is therefore **0**, not the
  5% first proposed -- there is no discrepancy for a tolerance to absorb, and 5%
  of a 30-day window is around a hundred records. Transient shortfalls are the
  retry loop's job.

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
- API: https://api.complib.org, documented by an OpenAPI 3.0 spec at
  https://complib.org/complib.api.yml (rendered as Redoc at
  https://complib.org/api). The `/api` HTML page is a client-rendered shell
  with no docs in the HTML itself -- the spec is the file it loads.
- Ingested via `scripts/ingest_complib.py` into the tables defined in
  `schema/006_init_complib.sql` (`compositions`, `composition_methods`, and
  view `v_composition_methods`).
- Coverage: 86,039 compositions (measured 2026-08-15 via the search
  endpoint's `count`). The loader walks `/composition/search` page by page.
- Licence: none stated beyond site terms (`https://complib.org/terms`).
  CompLib is a community-maintained, freely-browsable public database; treat
  this corpus as public data with attribution to Composition Library if any
  derived output is published.
- Pagination: `/composition/search?page=N&perpage=N` returns `{count, page,
  perpage, compositions[]}`. The OpenAPI spec says `perpage` defaults to 25
  but does not state a maximum; the server enforces one -- `perpage > 25`
  returns HTTP 400 `"perpage maximum 25"`. So a full corpus walk is ~3,400+
  pages at 25/page. The loader caches each page to disk (`complib-cache/`)
  and rate-limits (0.5s/page by default) so re-runs do not re-hit the API.
- Method linkage: the brief asked whether CompLib carries a method
  identifier matching the CCCBR library. The search payload does not: each
  composition's `methodDefinitions[]` carries a free-text method `title`
  (e.g. "Rutland Surprise Major") and `placeNotation`, not a CCCBR id. The
  `/composition/{id}/rows` endpoint does return a `methodid` for
  single-method (non-spliced) compositions, and empirically that integer
  corresponds to the CCCBR `method_id` by the rule `method_id = 'm' ||
  methodid` (11 of 12 sampled resolved; the 12th was a constructed spliced
  title with no single CCCBR method). That is recorded as
  `complib_method_id`, and `composition_methods.method_id` is populated by
  that exact identifier lookup only -- never by fuzzy title matching, which
  is Gemini's to resolve and Claude Code's to adjudicate. Fetching the
  `methodid` costs one extra request per composition, so it is opt-in
  (`--fetch-method-ids`); without it, the free-text `method_title` is the
  only linkage.
- Be gentle with the API: it is Cloudflare-fronted, returns ~0.6s/page,
  and publishes no rate-limit headers. The loader assumes it throttles
  until shown otherwise, as the brief required.

### CompLib API, as measured 2026-08-15

- `GET https://api.complib.org/composition/search?page=N&perpage=25` returns
  `{count, page, perpage, compositions[]}`. **`count` was 86,039 when Vibe
  measured and 86,040 an hour later** -- the corpus grows, so treat any total
  here as true of a moment.
- **`perpage` is capped at 25 and the spec does not say so.** Anything larger
  returns HTTP 400 with the body `perpage maximum 25`. A full walk is therefore
  ~3,442 pages, not the handful a larger page size would allow.
- **Paging is 1-indexed.** `page=0` returns HTTP 500, not an empty result.
- `methodDefinitions[]` carries free-text method titles and place notation, **not**
  a CCCBR identifier. No fuzzy matching is attempted: the text is loaded and
  `method_id` left nullable, per the brief.
- `GET /composition/{id}/rows` returns a `methodid` for single-method
  compositions, and it maps to the CCCBR library by the exact rule
  **`method_id = 'm' || methodid`**. Verified independently on merge: eight
  resolved rows, eight exact title agreements with `methods.title`, zero broken
  foreign keys. This is an identifier join, like BellBoard's `dove-tower-id`, not
  a name match.

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
