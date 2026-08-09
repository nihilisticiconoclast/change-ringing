# Task brief: CCCBR Methods Library ingestion (Mistral Vibe)

Dispatch this as a single bounded coding task, delivered as a pull request
against `main`. Do not push directly. Everything below is verified against
the live sources as of 2026-08-09; where a number is quoted, it was measured,
not estimated.

Paste from the horizontal rule onward.

---

You are working on `nihilisticiconoclast/change-ringing`, a queryable corpus
for English change ringing. It already holds Dove's Guide (towers, bells,
frames, founders) and BellBoard performances in a Turso (hosted libSQL,
SQLite-compatible) database. Your task is to add the CCCBR Methods Library as
a third source.

Read `README.md`, `docs/CONNECTING.md` and `data/SOURCES.md` first, and read
`schema/002_init_bellboard.sql` and `scripts/ingest_bellboard.py` closely --
your work should look like a sibling of those two files. Match their comment
style: state *why*, not just *what*.

## Deliverables

1. `schema/003_init_methods.sql` -- schema for the methods corpus.
2. `scripts/ingest_methods.py` -- downloads, parses and loads it.
3. A short section in `data/SOURCES.md` recording provenance and licence.
4. A row-count verification in the PR description.

## The source

`https://methods.cccbr.org.uk/xml/CCCBR_methods.xml.zip` -- a zip containing a
single `CCCBR_methods.xml` (~1.3 MB compressed). Per-classification files also
exist (`CCCBR_Surprise.xml.zip` and so on) but the combined file is the one to
use. Namespace: `http://www.cccbr.org.uk/methods/schemas/2007/05/methods`.

Structure: `<collection>` contains `<methodSet>` elements, each with a
`<properties>` block (`stage`, `classification`, `lengthOfLead`,
`numberOfHunts`, `huntbellPath`) shared by all `<method>` children. Each
`<method>` has `id`, `<title>`, `<name>`, `<notation>`, `<symmetry>`,
`<leadHead>`, and an optional `<performances>` block.

Measured totals in the current release: **25,055 methods**; classification
counts Surprise 10595, Bob 4963, Delight 3849, Alliance 1713, Treble Place
1405, Treble Bob 940, Hybrid 451, Place 427, and 712 methods in sets with no
`<classification>` element at all (mostly principles -- handle the absence,
do not invent a value).

The `<performances>` block records first performances. There are **30,732
`<location>` records** across 15 event types (`firstTowerbellPeal` 15813,
`firstInclusionInTowerbellPeal` 6401, `firstInclusionInHandbellPeal` 3216,
`firstHandbellPeal` 1310, and smaller keyboard/extent/quarter-peal variants).
Each carries `<date>`, an optional `<society>`, and a `<location>` with
`<building>`, `<town>`, `<county>` -- **as free text, with no Dove tower ID**,
and `<county>` is sometimes absent.

Model those first-performance events as their own table with the event type as
a column, rather than one column per event type -- there are 15 types and the
list will grow.

## Critical: do not repeat mistakes already made and fixed here

These cost real debugging time on the two existing loaders. They are not
hypothetical.

- **Never use `conn.executemany()` against Turso.** It issues a round trip per
  row: measured at **4.1 rows/s**, and it stalls outright on long runs. Build
  one multi-row `INSERT ... VALUES (...),(...),...` per batch instead --
  measured at **~1300 rows/s**, a 330x difference. Copy the `insert_many()`
  helper from `scripts/ingest_bellboard.py`.
- **Keep batches under SQLite's bind-parameter ceiling** (32766). Derive the
  batch size from a parameter budget as the existing scripts do; do not
  hardcode 500 rows for a wide table.
- **Do not split schema SQL on `;` by hand.** Use `conn.executescript()`. A
  semicolon inside a `--` comment silently produces invalid fragments.
- **If you use pandas, `df.where(pd.notna(df), None)` does not convert NaN to
  None on float columns** -- it coerces None straight back to NaN. Local
  SQLite hides this by storing NaN as NULL; Turso rejects it with a JSON type
  error. Use `df.astype(object).where(pd.notna(df), None)`. For this task
  `xml.etree.ElementTree` alone is probably sufficient and pandas unnecessary.
- **Be polite to the source.** BellBoard throttles sustained querying by
  silently truncating responses rather than returning an error status. This is
  a single zip download, so it is far less of a concern here -- but download
  once to a local path and parse from disk, do not re-fetch per method.

## Requirements

- **Idempotent.** Re-running must converge, not duplicate. Use
  `INSERT OR REPLACE` keyed on the CCCBR method `id`, and clear child rows for
  the affected methods before reinserting -- see `ingest_bellboard.py`, which
  solves exactly this.
- **A `--reset` flag** matching `scripts/migrate_csv_to_turso.py`: refuse to
  run against existing objects unless `--reset` is passed, and when dropping,
  drop only the objects your own schema file declares.
- **Do not commit the downloaded XML or zip.** `.gitignore` already excludes
  `dove-csvs/`; add an equivalent entry.
- **Do not commit credentials.** The loader reads `TURSO_DATABASE_URL` and
  `TURSO_AUTH_TOKEN` from the environment, exactly as the existing scripts do.

## Explicitly out of scope

Do not attempt to match `<location>` town/county text to Dove towers. That
entity resolution is a separate task already assigned elsewhere, and it will
collide with your work if you start it. Load the location fields as they
appear, leave a nullable `dove_tower_id` column unpopulated for that task to
fill later, and stop there.

Do not modify `schema/001_*`, `schema/002_*`, `scripts/migrate_csv_to_turso.py`
or `scripts/ingest_bellboard.py`. If you believe one of them is wrong, say so
in the PR description rather than changing it.

## Definition of done

A PR against `main` containing the four deliverables, whose description
reports actual row counts from a real run against Turso -- methods loaded,
first-performance events loaded, and a count of methods by classification
that reconciles with the figures above. State clearly if your counts differ:
the library is regenerated periodically, so a small drift is expected and
worth noting rather than hiding.
