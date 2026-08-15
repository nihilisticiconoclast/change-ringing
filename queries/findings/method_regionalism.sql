-- Query for identifying hyper-regional methods
-- Depends on: v_tower_performances (which includes dove_county)

WITH method_totals AS (
    SELECT method, COUNT(perf_id) AS total_perfs
    FROM v_tower_performances
    WHERE method IS NOT NULL AND method != '' AND dove_county IS NOT NULL
    GROUP BY method
    HAVING COUNT(perf_id) >= 50
),
county_totals AS (
    SELECT method, dove_county, COUNT(perf_id) AS county_perfs
    FROM v_tower_performances
    WHERE method IS NOT NULL AND method != '' AND dove_county IS NOT NULL
    GROUP BY method, dove_county
)
SELECT 
    c.method,
    c.dove_county AS dominant_county,
    c.county_perfs,
    m.total_perfs,
    ROUND(CAST(c.county_perfs AS FLOAT) / m.total_perfs * 100, 2) AS concentration_pct
FROM county_totals c
JOIN method_totals m ON c.method = m.method
WHERE ROUND(CAST(c.county_perfs AS FLOAT) / m.total_perfs * 100, 2) > 70
ORDER BY concentration_pct DESC;
