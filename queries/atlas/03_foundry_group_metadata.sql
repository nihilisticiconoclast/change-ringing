-- Atlas · the foundry cards
--
-- Working life, constituent firms and total output for one tradition.
-- Parameterised: bind the group name once (scripts/build_atlas.py runs it per
-- tradition rather than grouping, so the home-location subquery stays simple).
--
-- "From"/"To" are per-firm, so MIN/MAX across the group gives the tradition's
-- span: Whitechapel 1570-2017, Loughborough 1786-2009.

SELECT
  MIN(f."From")  AS first_year,
  MAX(f."To")    AS last_year,
  COUNT(*)       AS firms,
  SUM(f.Bells)   AS bells_attributed
FROM founders f
WHERE f."Group" = :group_name;

-- The home town, taken as the location most of the group's firms worked from.
SELECT f.Location
FROM founders f
WHERE f."Group" = :group_name
  AND f.Location IS NOT NULL
GROUP BY f.Location
ORDER BY COUNT(*) DESC
LIMIT 1;
