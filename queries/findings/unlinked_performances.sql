-- What is deliberately NOT linked to a tower, and why.
--
-- 8,623 of 30,734 first-performance records carry no dove_tower_id. That is a
-- decision, not a gap: most name a private house where a handbell peal was
-- rung, which has no tower to link to. See docs/method_location_resolution.md
-- and data/method_location_adjudication.csv for the per-row reasoning.
--
-- Writing a wrong TowerID would be worse than leaving NULL: a NULL is visibly
-- unresolved, whereas a plausible-but-wrong ID silently corrupts every
-- downstream query.

SELECT
  CASE WHEN dove_tower_id IS NULL THEN 'unlinked' ELSE 'linked' END AS state,
  COUNT(*)                                                          AS records
FROM method_performances
GROUP BY state;

-- The most common unlinked places -- read this as a list of private houses and
-- virtual platforms, not as a to-do list.
SELECT building, town, county, COUNT(*) AS records
FROM method_performances
WHERE dove_tower_id IS NULL
GROUP BY building, town, county
ORDER BY records DESC
LIMIT 20;
