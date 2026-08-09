# Decision 001 — what a join to `dove` means: a tower, or a ring?

**Status:** decided, not yet implemented (Vibe roadmap Task 4)
**Date:** 2026-08-09

## The problem

`dove.TowerID` is not a key. 7,262 rows carry 7,249 distinct TowerIDs, because
13 towers hold two rings each. Joining anything to `dove` on `TowerID` alone
therefore returns two rows where the caller expected one, and every count
downstream is quietly too high.

The 13, all with exactly two rings:

| TowerID | Place | Rings |
| --- | --- | --- |
| 15240 | Bampton, S Patrick | two full-circle |
| 12540 | Canewdon, S Nicholas | two full-circle |
| 11301 | Farnham, S Andrew | full-circle + lightweight |
| 14529 | Gorran, S Goranus | two full-circle |
| 11860 | Gresford, All Saints | two full-circle |
| 25670 | Horsted Keynes | two lightweight |
| 13250 | Liddington, All Saints | two full-circle |
| 12130 | Ovingham, S Mary V | two full-circle |
| 14482 | Rugby, S Andrew | two full-circle |
| 12022 | South Stoneham, S Mary | lightweight + full-circle |
| 16150 | St Pierre du Bois | two full-circle |
| 13764 | St Winnow | two full-circle |
| 16183 | Withycombe Raleigh, S John Ev | full-circle + lightweight |

Measured impact today: joining `method_performances` to `dove` on `TowerID`
returns **21,951** rows where a distinct tower list returns **21,932** — 19 rows
of pure inflation. Small, but it is silent, it scales with the corpus, and it
lands hardest on exactly the towers a ringer is most likely to ask about.

An earlier note in the README put this at 11 rows. That figure came from a
different query shape and is wrong; 19 is the measured number for this join.

## A second finding, which changes the fix

Of the 22,111 first-performance records carrying a `dove_tower_id`, only
**21,951 join to `dove` at all**. The other **160 point at TowerIDs present in
`towers` but not in `dove`** — installations that are not full-circle or
lightweight rings, and so fall outside Dove's ringing subset. The adjudication
accepted them because they resolve against the wider register.

So joining to `dove` does two wrong things at once: it duplicates 19 rows and
silently drops 160. The second is the larger error, and no amount of
de-duplication fixes it.

## Checking the obvious fix, which does not work

The tempting answer is "join `towers` instead, since it is the superset and it
is what `dove_tower_id` identifies". **That is worse.** `towers.TowerID` is not
unique either: 15,720 rows carry 15,402 distinct IDs, because 306 towers appear
once per installation — Brompton S Thomas has a full-circle ring *and* a chime;
Sewanee has a carillon *and* a full-circle ring.

Joining the 22,111 linked records to raw `towers` returns **23,550** — 1,439
rows of inflation, seventy times worse than the problem being fixed. Neither
table is a tower register. Both are installation registers keyed on something
finer than the tower.

## The decision

**Neither `dove` nor `towers` may be joined on `TowerID` directly. Both get a
deduplicated tower projection, and that projection is what callers join to.**

Verified: joining the linked records to `SELECT DISTINCT TowerID FROM towers`
returns exactly **22,111** — every linked row, once each. Nothing dropped,
nothing duplicated.

1. **Add `v_towers_unique`** — one row per TowerID, drawn from `towers` so the
   160 non-ringing installations survive:

   ```sql
   CREATE VIEW "v_towers_unique" AS
   SELECT "TowerID",
          MAX("Place")   AS "Place",
          MAX("Dedicn")  AS "Dedicn",
          MAX("County")  AS "County",
          MAX("Country") AS "Country",
          COUNT(*)       AS "installations"
   FROM "towers" GROUP BY "TowerID";
   ```

2. **Add `v_dove_towers`** — the same shape over `dove`, for questions that
   need Dove's ringing-specific attributes and accept its narrower scope:

   ```sql
   CREATE VIEW "v_dove_towers" AS
   SELECT "TowerID",
          MIN("RingID") AS "primary_ring_id",
          COUNT(*)      AS "rings",
          MAX("Place")  AS "Place",
          MAX("Dedicn") AS "Dedicn",
          MAX("County") AS "County"
   FROM "dove" GROUP BY "TowerID";
   ```

   `MIN(RingID)` is arbitrary but deterministic — not a claim about which ring
   matters, only a stable choice so repeated runs agree. `MAX()` over Place and
   Dedicn is safe because they are per-tower attributes repeated across a
   tower's rows, not per-ring ones; confirm that holds before extending this
   pattern to another column.

3. **Ring-level questions use `RingID` against raw `dove`.** BellBoard supplies
   `dove_ring_id` per performance, so its data can be ring-accurate. The
   Methods Library supplies no ring identifier, so first-performance records
   are tower-level and cannot be made otherwise — say so rather than inventing
   a ring.

4. **Expected counts after the change**, so the implementation can be checked
   rather than eyeballed: `method_performances` joined to `v_towers_unique`
   must be exactly 22,111. Against `v_dove_towers` it will be 21,932 — the
   ringing subset, correctly excluding the 160.

## What to change

- `v_first_tower_peals` — currently joins `dove` on `TowerID`. Move it to
  `v_towers_unique`, which recovers the 160 dropped rows and removes the 19
  duplicates. Its count will change; that is the point. Record before and after.
- `v_tower_performances` — same join, same fix. It reads 0 in the committed
  snapshot only because BellBoard is empty there; check it against a replica
  built with `--bellboard-since`.
- `queries/` — update anything joining `dove` on `TowerID`, and add a note to
  `queries/README.md`, which currently tells readers to use `RingID` without
  saying that `towers` is the better default.
- `scripts/build_atlas.py` — `queries/atlas/02` joins `dove`. The atlas
  first-peal figures will move slightly. Rebuild and republish.

## What not to change

Do not add a foreign key from `method_performances.dove_tower_id` to anything.
BellBoard and the Methods Library both track Dove live while this database
holds a periodic snapshot, so they can legitimately cite a tower newer than our
copy — 2 of 391 sampled BellBoard IDs already did. A hard FK would reject those
rows; a soft reference keeps them and lets the next refresh resolve them.

## How to verify the fix

`SELECT COUNT(*)` before and after on each view, and confirm the difference is
accounted for exactly: +160 recovered, −19 de-duplicated. A change of any other
size means something else moved and should be understood before merging.

The single sharpest check: `method_performances` joined to `v_towers_unique`
must return **22,111**, matching the count of rows carrying a `dove_tower_id`.
Any other number is wrong by construction — the join cannot legitimately
create or destroy a linked record.
