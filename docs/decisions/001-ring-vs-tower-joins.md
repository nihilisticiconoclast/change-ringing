# Decision 001 — what a join to `dove` means: a tower, or a ring?

**Status:** **implemented** in `schema/007_init_tower_views.sql`, 2026-08-15
**Date:** 2026-08-09, with a correction and an addition on 2026-08-15

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

Of the first-performance records carrying a `dove_tower_id`, some **point at
TowerIDs present in `towers` but not in `dove`** — installations that are not
full-circle or lightweight rings, and so fall outside Dove's ringing subset. The
adjudication accepted them because they resolve against the wider register.

So joining to `dove` does two wrong things at once: it duplicates rows and
silently drops others. The second is the larger error, and no amount of
de-duplication fixes it.

> ### Correction, 2026-08-15: this section said 160, and it is 179
>
> The original text computed the orphans as 22,111 − 21,951 = 160. Those two
> numbers are not the same kind of thing. 22,111 counts **records**; 21,951 is
> the **row count the join returns**, which already contains 19 duplicates.
> Subtracting one from the other mixes units and undercounts the orphans by
> exactly those 19.
>
> Re-measured on the current snapshot, keeping records and rows apart:
>
> | | `method_performances` |
> | --- | ---: |
> | records carrying a `dove_tower_id` | 22,117 |
> | rows returned by joining `dove` on `TowerID` | 21,957 |
> | **records that join at all** | **21,938** |
> | inflation (rows − records) | 19 |
> | **orphan records** (22,117 − 21,938) | **179** |
>
> The totals have also drifted from the 2026-08-09 figures — 22,111 → 22,117 —
> because the replica is rebuilt against a live Dove snapshot. Any count in this
> document is true of a snapshot, not of the source.
>
> This is a mildly embarrassing error to find in a decision record whose whole
> subject is joins that quietly return the wrong number of rows, and it is left
> visible for that reason. The expected-count checks below use the corrected
> figures.

## A third finding, added 2026-08-15: BellBoard has the same problem

The record above concerns `method_performances`. `performances` — the BellBoard
corpus, 80,128 records carrying a `dove_tower_id` — behaves identically and had
not been measured:

| | `performances` |
| --- | ---: |
| records carrying a `dove_tower_id` | 80,128 |
| rows returned by joining `dove` on `TowerID` | 80,231 |
| records that join at all | 80,004 |
| **inflation** | **227** |
| **orphan records** | **124**, across 30 distinct TowerIDs |

The inflation is 227 rather than 19 simply because there are more records
passing through the same 13 two-ring towers. `v_tower_performances` is built on
this join and is therefore 227 rows too high today.

**The 124 orphans are not corruption, and should not be "cleaned".** Of the 30
distinct TowerIDs:

- **25 exist in `towers` but not in `dove`.** Most are chimes and tubular
  chimes — Melsonby S James Gt, Leighterton S Andrew, Haywards Heath S Wilfrid
  — which are outside Dove's full-circle/lightweight scope by definition. A few
  are recorded as full-circle rings (Southport Holy Trinity, S Margaret Pattens
  in the City of London, Sheviock, Shilbottle, Leusdon), which most likely means
  the ring has left Dove's ringable list since BellBoard recorded the
  performance.
- **5 exist in neither table**: 14615, 15542 (Aberavon, 23 performances), 25193,
  25225 (Leonard Stanley, 26), 25756 (Somerton, 18). These are the ones worth
  watching. 14615 carries performances filed under two different places —
  Steventon and North Collingham — which is either an upstream error or an ID
  reused after a deletion.

So the same conclusion holds for BellBoard as for the Methods Library: **join
the deduplicated projection of `towers`, not `dove`**.

> **Correction, 2026-08-15: "121 of the 124 resolve" was wrong — it is 54.**
>
> That sentence took 30 distinct TowerIDs minus the 5 absent ones and reported
> the answer as if it were a count of records. It is a count of *identifiers*.
> The 5 absent IDs carry 70 records between them — 14615×2, 15542×23, 25193×1,
> 25225×26, 25756×18 — so **54 of the 124 orphan records resolve via `towers`,
> and 70 do not.**
>
> This is the second unit error in this document, and it is the same one the
> document was written to correct. It surfaced only when `v_towers_unique`
> actually existed and could be joined: `performances` → `v_towers_unique`
> returns 80,058 against 80,128 linked records, short by exactly 70. Counting
> identifiers where records are meant is evidently easy to do twice on one page,
> which is an argument for naming the unit in the sentence every time.

The 70 stay unresolved and visible, which is the right outcome — see "What not to
change" below on why a hard foreign key would be wrong here.

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
returns exactly the number of records carrying a `dove_tower_id` — every linked
row, once each. Nothing dropped, nothing duplicated. That identity, rather than
any particular figure, is the acceptance test, because the figures move with the
snapshot.

1. **Add `v_towers_unique`** — one row per TowerID, drawn from `towers` so the
   non-ringing installations survive (179 in `method_performances`, 121 of the
   124 in `performances`):

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
   rather than eyeballed. Written as identities, not constants, because the
   snapshot moves:

   | Join | Must equal |
   | --- | --- |
   | `method_performances` → `v_towers_unique` | records with a `dove_tower_id` (22,117 today) |
   | `method_performances` → `v_dove_towers` | that, minus the orphans (21,938 today) |
   | `performances` → `v_towers_unique` | records with a `dove_tower_id` (80,128 today) |
   | `performances` → `v_dove_towers` | that, minus the orphans (80,004 today) |

  Measured after implementation: `method_performances` → `v_towers_unique`
  returns **22,117**, exactly the linked count. `performances` →
  `v_towers_unique` returns **80,058** against 80,128, short by the 70 records
  whose TowerIDs exist in neither table.

   A join cannot create or destroy a linked record, so any other number is wrong
   by construction.

## What to change

- `v_first_tower_peals` — currently joins `dove` on `TowerID`. Move it to
  `v_towers_unique`, which recovers the 160 dropped rows and removes the 19
  duplicates. Its count will change; that is the point. Record before and after.
- `v_tower_performances` — same join, same fix, and now measured: it returns
  **80,231** where the underlying records number **80,128**, so it is 227 rows
  too high and drops 124. Both errors go away with `v_towers_unique`.
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
accounted for exactly. For `v_first_tower_peals`: +179 recovered, −19
de-duplicated. For `v_tower_performances`: +121 recovered, −227 de-duplicated. A
change of any other size means something else moved and should be understood
before merging.

The single sharpest check, for either corpus: the record count after the join
must equal the count of rows carrying a `dove_tower_id`. Any other number is
wrong by construction — a join cannot legitimately create or destroy a linked
record. Compare records with records; the mistake corrected above happened
because a row count was subtracted from a record count.
