# Licensing: the data is not under the repository's MIT licence

**This repository is dual-licensed. The code is MIT. The data is not.**

`LICENSE` at the repository root covers the code -- the schema files, the
loaders, the scripts. It does **not** cover `data/change-ringing.db` or the
derived CSVs alongside it.

## data/change-ringing.db

A built snapshot of the corpus, committed so the database can be queried
without running a build or holding Turso credentials. It contains:

- **Dove's Guide for Church Bell Ringers** -- towers, bells, frames, founders.
  https://dove.cccbr.org.uk -- **CC BY-SA 4.0**
- **CCCBR Methods Library** -- methods and first-performance records.
  https://methods.cccbr.org.uk -- © Central Council of Church Bell Ringers
- **BellBoard** — the 2012-2024 performance record, committed as CSVs under
  `data/bellboard/`.
  https://bb.ringingworld.co.uk -- © The Ringing World

Because Dove's data is CC BY-SA 4.0, **this database file and anything
substantially derived from it are subject to CC BY-SA 4.0, not MIT.** In
practice that means three obligations, and they travel with the file:

1. **Attribute** Dove's Guide, and link to it.
2. **Link the licence** -- https://creativecommons.org/licenses/by-sa/4.0/
3. **Share alike.** Publish a derivative database, or a substantial extract,
   under CC BY-SA 4.0 as well. You cannot relicense it to MIT by putting it in
   an MIT repository, and the presence of `LICENSE` at the root does not do so.

Changes have been made to the source data: column names sanitised, the seven
CSVs loaded into a relational schema, and 22,111 first-performance records
linked to Dove tower IDs by the adjudication recorded in
`method_location_adjudication.csv`. CC BY-SA requires that indication of
change, which this paragraph provides.

## The derived CSVs

`method_location_candidates.csv` and `method_location_adjudication.csv` contain
Dove place names and TowerIDs alongside CCCBR location text. They are
derivative of both sources and carry the same CC BY-SA 4.0 obligations.

## Why the snapshot is committed at all, and when not to

The considered default in this project is **not** to commit built data: it is
reproducible in about 90 seconds via `scripts/build_local_db.py`, and a 40 MB
binary that changes wholesale on each rebuild sits in git history forever.

It is committed here for a specific reason. The Turso database is frozen until
2026-09-01 after a row-read overrun, and analytical work should not stall for
three weeks waiting on it. The snapshot makes the corpus openable straight from
a clone, in any SQLite tool, by someone who does not want to run Python.

Two consequences worth keeping in view:

- **Do not re-commit it casually.** Each new version adds ~40 MB to history
  that cannot be removed without rewriting it. If the data starts changing
  often, move the snapshot to a GitHub Release asset, which is downloadable
  from the repository page without entering git history at all.
- **It goes stale.** Dove is a live source and drifts -- its edit log lost
  three rows in the space of two hours on the day this was built. Treat the
  snapshot as a dated copy, not the source of truth. Turso is the live
  database; `scripts/build_local_db.py` always rebuilds current.

Snapshot built 2026-08-09: 7,262 ringing towers, 63,894 bells, 25,055 methods,
30,734 first-performance records, 22,111 of them tower-linked.
