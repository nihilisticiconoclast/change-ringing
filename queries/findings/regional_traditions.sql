-- The other half of method_regionalism.sql: what IS regional, once you stop
-- insisting it be a method.
--
-- The named repertoire turns out to be national -- exactly one library method
-- exceeds 50% concentration in a single county. So this query drops the
-- requirement that the title resolve to a method and asks the free-text
-- `performances.method` column what is regionally concentrated, which is the
-- question the data can actually answer.
--
-- Measured on the 2012-2024 corpus, >70% in one county with n >= 50:
--
--   Quick Tolling                     Lincolnshire      85/86    98.8%
--   Lismore Minimus                   New South Wales   53/55    96.4%
--   Fifth Hunt Doubles Call Changes   Cornwall          45/50    90.0%
--   Devon Call Changes                Devon             82/96    85.4%
--   Doubles (11v)                     Herefordshire     44/60    73.3%
--
-- Devon Call Changes at 85% in Devon is the one a ringer would predict, and it
-- is worth having measured rather than assumed. The others are not predictable
-- and are worth following up: Lincolnshire tolling, and a Cornish doubles
-- call-change form that appears essentially nowhere else.
--
-- CAVEAT, and it is not a small one. `performances.method` is free text, so
-- these rows are strings bands typed, not entities. "Devon Call Changes" and
-- "Devon call changes" are two rows here. The counts are therefore lower bounds
-- on each tradition, and a tradition recorded under several spellings could be
-- missing from this list entirely. Normalising that is the obvious next step and
-- has not been done.

WITH tp AS (
  SELECT p.perf_id, TRIM(p.method) AS method, t."County" AS county
  FROM performances p
  JOIN v_towers_unique t ON t."TowerID" = p.dove_tower_id
  WHERE p.method IS NOT NULL AND TRIM(p.method) != ''
    AND t."County" IS NOT NULL AND t."County" != ''
),
method_totals AS (
  SELECT method, COUNT(*) AS total_perfs FROM tp
  GROUP BY method HAVING COUNT(*) >= 50
),
county_totals AS (
  SELECT method, county, COUNT(*) AS county_perfs FROM tp GROUP BY method, county
)
SELECT c.method,
       c.county                                       AS dominant_county,
       c.county_perfs,
       m.total_perfs,
       ROUND(100.0 * c.county_perfs / m.total_perfs, 1) AS concentration_pct,
       CASE WHEN EXISTS (SELECT 1 FROM methods x WHERE x.title = c.method)
            THEN 'library method' ELSE 'not a library method' END AS kind
FROM county_totals c
JOIN method_totals m USING (method)
WHERE 100.0 * c.county_perfs / m.total_perfs > 70
ORDER BY concentration_pct DESC;
