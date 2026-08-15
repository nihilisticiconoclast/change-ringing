-- Deduplicated tower projections -- the fix specified in
-- docs/decisions/001-ring-vs-tower-joins.md.
--
-- Neither `dove` nor `towers` is a tower register. Both repeat TowerID, because
-- both are installation registers keyed on something finer than the tower: 13
-- towers hold two rings each in `dove`, and 306 towers appear once per
-- installation in `towers` (Brompton S Thomas has a full-circle ring AND a chime).
-- So joining either on TowerID alone fans out, and joining `dove` also silently
-- DROPS every installation outside its ringing subset.
--
-- Callers join these projections instead. Numbered 007 rather than 005: 005 is
-- schema/005_init_performance_methods.sql and 006 is claimed by CompLib
-- ingestion, which is in flight.
--
-- Originally written by Gemini inside schema/001_init_dove_bells.sql. Moved here
-- because 001 defines the Dove TABLES and a view over them is a separate concern
-- -- the same reason 004 holds indexes rather than scattering them.

DROP VIEW IF EXISTS "v_towers_unique";
CREATE VIEW "v_towers_unique" AS
SELECT "TowerID",
       MAX("Place")   AS "Place",
       MAX("Dedicn")  AS "Dedicn",
       MAX("County")  AS "County",
       MAX("Country") AS "Country",
       COUNT(*)       AS "installations"
FROM "towers" GROUP BY "TowerID";

DROP VIEW IF EXISTS "v_dove_towers";
CREATE VIEW "v_dove_towers" AS
SELECT "TowerID",
       MIN("RingID") AS "primary_ring_id",
       COUNT(*)      AS "rings",
       MAX("Place")  AS "Place",
       MAX("Dedicn") AS "Dedicn",
       MAX("County") AS "County"
FROM "dove" GROUP BY "TowerID";

-- MIN(RingID) is arbitrary but deterministic -- not a claim about which ring
-- matters, only a stable choice so repeated runs agree. MAX() over Place and
-- Dedicn is safe because they are per-tower attributes repeated across a tower's
-- rows, not per-ring ones; confirm that holds before extending the pattern.
--
-- MEASURED ON THIS SNAPSHOT, 2026-08-15:
--
--   join                                    records   result   verdict
--   method_performances -> v_towers_unique   22,117   22,117   exact
--   method_performances -> dove              22,117   21,957   +19 dup, -179 dropped
--   performances        -> v_towers_unique   80,128   80,058   -70, see below
--   performances        -> dove              80,128   80,231   +227 dup, -124 dropped
--
-- The 70 are not a defect in these views. They are records citing five TowerIDs
-- that exist in NEITHER `dove` nor `towers` -- 14615, 15542, 25193, 25225, 25756
-- -- so no projection of either table can resolve them. They stay unresolved and
-- visible, which is the right outcome: see "What not to change" in decision 001
-- on why a hard foreign key here would be wrong.
