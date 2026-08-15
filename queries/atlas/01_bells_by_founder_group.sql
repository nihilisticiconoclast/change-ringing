-- Atlas · the main extract
--
-- Every surviving bell whose founder is known, with the coordinates of the
-- tower it hangs in and the foundry tradition its founder belongs to.
-- One row per bell: 51,523 of them across 12,635 towers on the current Dove
-- snapshot. It was 51,451 when this was written; Dove is refreshed on every
-- build, so the count drifts and the page now computes it rather than stating it.
--
-- Read by scripts/build_atlas.py, which aggregates these rows in Python into
-- per-tower points (dominant tradition, bell count, earliest casting year) and
-- the quarter-century timeline. The aggregation is not done here because the
-- casting year needs extracting from free text -- Cast_Date holds values like
-- "c1897", "(1834", "[1902" -- which is easier to do reliably outside SQL.
--
-- founders."Group" is what makes the atlas legible: it collapses successive
-- firms into a single foundry tradition, so thirteen Loughborough businesses
-- from 1786 onward count as one house rather than thirteen.
--
-- 97% of bells join to a founder record; 81% of those carry a Group; 98.5% of
-- bells carry their own coordinates. That intersection is what this returns.

SELECT
  b.Tower_ID,
  b.Latitude,
  b.Longitude,
  f."Group"   AS founder_group,
  b.Cast_Date
FROM bells b
JOIN founders f ON f.Name = b.Founder
WHERE f."Group" IS NOT NULL
  AND b.Latitude IS NOT NULL;
