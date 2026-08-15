-- Are there regional methods? Almost none -- and that is the finding.
--
-- From Gemini's feature/data-insights branch, where it was written to find
-- "hyper-regional methods". It found five things concentrated in one county,
-- and NONE OF THE FIVE IS A METHOD: Quick Tolling, Devon Call Changes, Fifth
-- Hunt Doubles Call Changes, Doubles (11v), Lismore Minimus -- zero rows in the
-- `methods` table between them. The original grouped on the free-text
-- `performances.method` column, which holds anything a band typed.
--
-- Rewritten to ask the question properly, joining `performance_methods` so that
-- "method" means a method the CCCBR library actually holds. The answer:
--
--   Library methods with >50% of their performances in one county, n >= 50:
--     Single Court Place Minimus   Lincolnshire   322/559   57.6%
--
--   ONE. Out of 25,066 methods.
--
-- Against a baseline where the busiest county in the country, Somerset, holds
-- just 6.6% of all tower-linked ringing, so there is no national concentration
-- for a method to inherit. The named repertoire is effectively uniform across
-- England.
--
-- Regional distinctiveness is real, and it lives entirely in what the Methods
-- Library does not index -- call changes, tolling, local doubles variants. Every
-- ringer knows Devon call-change ringing is its own world; what this shows is
-- the complement, that the *method* repertoire has almost no regional structure
-- at all. Run queries/findings/regional_traditions.sql for the other half.
--
-- Counties come from v_towers_unique, not `dove` -- see decision 001.

WITH mp AS (
  SELECT pm.method_id, m.title, t."County" AS county
  FROM performance_methods pm
  JOIN performances p      ON p.perf_id  = pm.perf_id
  JOIN v_towers_unique t   ON t."TowerID" = p.dove_tower_id
  JOIN methods m           ON m.method_id = pm.method_id
  WHERE t."County" IS NOT NULL AND t."County" != ''
),
method_totals AS (
  SELECT method_id, title, COUNT(*) AS total_perfs
  FROM mp GROUP BY method_id, title
  HAVING COUNT(*) >= 50          -- below this, one enthusiastic band is the whole story
),
county_totals AS (
  SELECT method_id, county, COUNT(*) AS county_perfs
  FROM mp GROUP BY method_id, county
)
SELECT t.title                                        AS method,
       c.county                                       AS dominant_county,
       c.county_perfs,
       t.total_perfs,
       ROUND(100.0 * c.county_perfs / t.total_perfs, 1) AS concentration_pct
FROM county_totals c
JOIN method_totals t USING (method_id)
WHERE 100.0 * c.county_perfs / t.total_perfs > 50
ORDER BY concentration_pct DESC;
