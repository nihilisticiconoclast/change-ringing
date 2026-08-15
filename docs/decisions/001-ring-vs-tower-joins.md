# Decision 001 — what a join to `dove` means: a tower, or a ring?

**Status:** **implemented and adopted.** The projections landed in
`schema/007_init_tower_views.sql` on 2026-08-15; on the same day
`v_tower_performances` (`schema/002`), `v_first_tower_peals` (`schema/003`) and
four queries were moved onto them, and `scripts/verify_corpus.py` began asserting
the join identity on every run.
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
   non-ringing installations survive (179 records in `method_performances`, and
   54 of the 124 in `performances` — see the correction above; the other 70 cite
   TowerIDs absent from both tables):

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

## What to change — done 2026-08-15, and the prediction was wrong

Both views and all four affected queries now join `v_towers_unique`. The before
and after were measured on the same snapshot rather than predicted:

| View | Before (`dove`) | After (`v_towers_unique`) | Change |
| --- | ---: | ---: | ---: |
| `v_tower_performances` | 80,231 | **80,058** | −173 |
| `v_first_tower_peals` | 25,351 | **25,340** | −11 |

`v_tower_performances` behaves exactly as this document said it would: −227
duplicate rows, +54 records recovered, net −173. The result, 80,058, is the join
identity holding — 80,128 linked records minus the 70 that cite TowerIDs present
in neither table.

> ### Correction, 2026-08-15: the `v_first_tower_peals` prediction was wrong
>
> "How to verify the fix" below said to expect **+179 recovered, −19
> de-duplicated** for `v_first_tower_peals`. Measured, it is **−11 rows, and +38
> rows that gained a tower they had always referenced** (rows with a non-NULL
> `dove_place`: 14,512 → 14,550).
>
> Neither predicted number was close, and the reason is structural rather than
> arithmetic. 179 and 19 are properties of `method_performances` **as a whole**.
> `v_first_tower_peals` is a `LEFT JOIN` driven off `methods` and filtered to
> `event_type = 'firstTowerbellPeal'`, so it sees a subset — only 11 of the 13
> two-ring towers appear in it at all — and because the join is `LEFT`, a
> recovered record does not add a row. It fills in three columns on a row that
> was already there.
>
> This is the third correction on this page, and unlike the first two it is not a
> unit error: it is the more ordinary mistake of quoting a figure measured on a
> table as though it described a view over that table. The lesson is the same
> one, though — **measure the object you are actually changing.** The row counts
> above were taken by building both versions of each view on a copy of the
> snapshot and counting, which took about a minute and would have caught this
> before it was written down.

- `queries/` — `atlas/02_first_peals_by_foundry`,
  `findings/busiest_towers_for_first_peals`, `findings/founder_reach_by_methods`
  and `findings/rudhall_territory` all moved to `v_towers_unique`.
  `queries/README.md` now names `v_towers_unique` as the default join target
  rather than pointing readers at `RingID`.
- `v_tower_performances` **loses `dove_ring_type`.** `RingType` describes a ring,
  and `v_towers_unique` is one row per tower, so there is no single correct value
  to carry; `MAX()` would have kept the column and made it arbitrary. Nothing
  outside `schema/002` read it.
- `scripts/build_atlas.py` — the atlas first-peal figures move with
  `queries/atlas/02`. Rebuild and republish.

## What not to change

Do not add a foreign key from `method_performances.dove_tower_id` to anything.
BellBoard and the Methods Library both track Dove live while this database
holds a periodic snapshot, so they can legitimately cite a tower newer than our
copy — 2 of 391 sampled BellBoard IDs already did. A hard FK would reject those
rows; a soft reference keeps them and lets the next refresh resolve them.

## How to verify the fix

`SELECT COUNT(*)` before and after on each view, and confirm the difference is
accounted for exactly. **The figures once given here — "+179 recovered, −19
de-duplicated" for `v_first_tower_peals`, "+121 recovered" for
`v_tower_performances` — were both wrong**; the measured values are in "What to
change" above. A change of any other size means something else moved and should
be understood before merging.

`scripts/verify_corpus.py` now checks the identity below on every run, so this
is a gate rather than a habit.

The single sharpest check, for either corpus: the record count after the join
must equal the count of rows carrying a `dove_tower_id`. Any other number is
wrong by construction — a join cannot legitimately create or destroy a linked
record. Compare records with records; the mistake corrected above happened
because a row count was subtracted from a record count.
