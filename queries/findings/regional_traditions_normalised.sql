-- Regional traditions, over NORMALISED practice categories rather than raw strings.
-- Roadmap item 25. Supersedes the raw-string version in regional_traditions.sql.
--
-- Requires the table `regional_traditions_classified` (perf_id, method_text, label).
-- `scripts/classify_regional_traditions.py --query` creates it as a TEMP table from
-- data/regional_traditions_classified.csv and runs this file, so what is recorded
-- here is what actually executes. The first version of this query joined a table
-- that existed nowhere, with a comment saying "we'll just assume there's a table" --
-- it could not be run at all as committed.
--
-- WHAT THE DENOMINATOR HAS TO BE, AND WHY THE FIRST VERSION GOT IT WRONG
--
-- The obvious query divides a county's count by the NATIONAL total for the
-- practice. That does not measure tradition, it measures how much a county
-- reports overall: a county that reports a lot of everything places high in every
-- category. Under it, call changes ranked Cornwall 13.2%, Lincolnshire 10.1%,
-- Devon 7.3% -- and tolling ranked Lincolnshire top, which is the reading that
-- was published.
--
-- The question "is this a regional tradition?" is: OF WHAT THIS COUNTY REPORTS,
-- how much is this practice? Dividing by the county's own total reported
-- performances instead:
--
--     call changes   Cornwall 25.45%, Lincolnshire 7.62%, Staffordshire 5.44%,
--                    Devon 5.37%
--     tolling        Northamptonshire 6.72%, Bedfordshire 6.24%, Merseyside 5.38%
--                    -- Lincolnshire is not in the top five
--
-- Both conclusions move. Cornwall is not merely first at call changes, it is a
-- 3.3x outlier: a QUARTER of everything Cornwall reports is call changes. And
-- Devon -- whose name is on the practice everywhere in ringing -- is fourth and
-- unremarkable. The received wisdom has the right practice and the wrong county.
--
-- Both denominators are emitted below so the difference can be seen rather than
-- taken on trust.
--
-- CLASSIFIER ACCURACY: 98.5% against 200 rows hand-labelled independently
-- (data/regional_traditions_oracle.csv). All three disagreements are the
-- classifier declining to classify something it could have -- never a wrong
-- category -- so every count here is a LOWER BOUND. See docs/regional_traditions.md.

WITH tp AS (
  SELECT p.perf_id,
         c.label            AS practice,
         t."County"         AS county
  FROM performance_method_unresolved pmu
  JOIN performances p        ON p.perf_id  = pmu.perf_id
  JOIN v_towers_unique t     ON t."TowerID" = p.dove_tower_id
  JOIN regional_traditions_classified c ON c.perf_id = pmu.perf_id
  -- 'unclassified' is a named method we could not resolve; 'multiple_methods' is
  -- spliced or a list. Neither is a practice, so neither belongs in this question.
  WHERE c.label NOT IN ('unclassified', 'multiple_methods')
    AND t."County" IS NOT NULL AND t."County" <> ''
),
-- Everything the county reports, not just the unresolved rows: the denominator
-- has to be the county's whole reported output or the share means nothing.
county_all AS (
  SELECT t."County" AS county, COUNT(*) AS county_total
  FROM performances p
  JOIN v_towers_unique t ON t."TowerID" = p.dove_tower_id
  WHERE t."County" IS NOT NULL AND t."County" <> ''
  GROUP BY 1
),
practice_totals AS (
  SELECT practice, COUNT(*) AS national_total
  FROM tp GROUP BY 1 HAVING COUNT(*) >= 50
),
county_practice AS (
  SELECT practice, county, COUNT(*) AS n FROM tp GROUP BY 1, 2
)
SELECT cp.practice,
       cp.county,
       cp.n                                                  AS performances,
       a.county_total,
       ROUND(100.0 * cp.n / a.county_total, 2)               AS pct_of_county,
       pt.national_total,
       ROUND(100.0 * cp.n / pt.national_total, 2)            AS pct_of_national
FROM county_practice cp
JOIN practice_totals pt USING (practice)
JOIN county_all a       USING (county)
-- A county needs enough reported ringing for a share to mean anything; 500 is the
-- floor used elsewhere in this repository for county-level claims.
WHERE a.county_total >= 500
ORDER BY cp.practice, pct_of_county DESC;
