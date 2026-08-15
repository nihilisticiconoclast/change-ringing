-- Re-run of the regional traditions query, but using our new normalised categories
-- instead of raw, fragmented strings.

-- Load the classified dataset into a temporary table to join against.
-- Note: In a production run, this would be imported into the SQLite DB.
-- Here we'll just read from the CSV and create an in-memory temp table 
-- before executing the query.

-- However, since this is a pure SQL file, we assume the host script has
-- created a `temp_classified` table, or we just instruct the user to run
-- it using a python wrapper.

-- But actually, we can import CSV natively in sqlite3 CLI using .import
-- However, for ease of use, I will provide a Python script to run this query.

WITH tp AS (
  SELECT p.perf_id, c.label AS method, t."County" AS county
  FROM performance_method_unresolved pmu
  JOIN performances p ON p.perf_id = pmu.perf_id
  JOIN v_towers_unique t ON t."TowerID" = p.dove_tower_id
  -- We'll just assume there's a table `regional_traditions_classified`
  JOIN regional_traditions_classified c ON c.perf_id = pmu.perf_id
  WHERE c.label != 'unclassified'
    AND c.label != 'multiple_methods' -- we are looking for non-method practices
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
       ROUND(100.0 * c.county_perfs / m.total_perfs, 1) AS concentration_pct
FROM county_totals c
JOIN method_totals m USING (method)
WHERE 100.0 * c.county_perfs / m.total_perfs > 5
ORDER BY method, concentration_pct DESC;
