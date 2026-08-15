-- Query: Practice night agreement between Dove's stated night and BellBoard performances
-- Compares Dove's stated Practice night against empirical non-Sunday short performance distribution
-- Depends on: dove, v_tower_performances
-- Excludes Sunday ringing (which dominates short performances across almost all towers)

WITH deduplicated_dove AS (
    SELECT 
        TowerID,
        MAX(Place) AS Place,
        MAX(Dedicn) AS Dedicn,
        MAX(County) AS County,
        MAX(Practice) AS Practice,
        CASE 
            WHEN MAX(Practice) LIKE 'Mon%' AND MAX(Practice) NOT LIKE '%alt%' AND MAX(Practice) NOT LIKE '%arrangement%' THEN 1
            WHEN MAX(Practice) LIKE 'Tue%' AND MAX(Practice) NOT LIKE '%alt%' AND MAX(Practice) NOT LIKE '%arrangement%' THEN 2
            WHEN MAX(Practice) LIKE 'Wed%' AND MAX(Practice) NOT LIKE '%alt%' AND MAX(Practice) NOT LIKE '%arrangement%' THEN 3
            WHEN MAX(Practice) LIKE 'Thu%' AND MAX(Practice) NOT LIKE '%alt%' AND MAX(Practice) NOT LIKE '%arrangement%' THEN 4
            WHEN MAX(Practice) LIKE 'Fri%' AND MAX(Practice) NOT LIKE '%alt%' AND MAX(Practice) NOT LIKE '%arrangement%' THEN 5
            WHEN MAX(Practice) LIKE 'Sat%' AND MAX(Practice) NOT LIKE '%alt%' AND MAX(Practice) NOT LIKE '%arrangement%' THEN 6
            ELSE NULL 
        END AS stated_dow
    FROM dove
    WHERE Practice IS NOT NULL AND Practice != ''
    GROUP BY TowerID
),
non_sun_perfs AS (
    SELECT 
        p.dove_tower_id,
        CAST(strftime('%w', p.perf_date) AS INTEGER) AS dow,
        COUNT(p.perf_id) AS perf_count
    FROM v_tower_performances p
    WHERE p.perf_date IS NOT NULL 
      AND strftime('%w', p.perf_date) != '0' -- Exclude Sunday (dow 0)
      AND (p.changes IS NULL OR p.changes < 5000) -- Short performances (quarter peals / touches)
    GROUP BY p.dove_tower_id, CAST(strftime('%w', p.perf_date) AS INTEGER)
),
tower_totals AS (
    SELECT 
        dove_tower_id,
        SUM(perf_count) AS total_non_sun_perfs,
        MAX(perf_count) AS max_day_perfs
    FROM non_sun_perfs
    GROUP BY dove_tower_id
    HAVING SUM(perf_count) >= 20 -- Minimum activity threshold
),
busiest_days AS (
    SELECT 
        n.dove_tower_id,
        MIN(n.dow) AS busiest_dow -- MIN to break ties deterministically
    FROM non_sun_perfs n
    JOIN tower_totals t ON n.dove_tower_id = t.dove_tower_id AND n.perf_count = t.max_day_perfs
    GROUP BY n.dove_tower_id
),
stated_day_counts AS (
    SELECT 
        d.TowerID,
        COALESCE(n.perf_count, 0) AS stated_day_perfs
    FROM deduplicated_dove d
    LEFT JOIN non_sun_perfs n ON d.TowerID = n.dove_tower_id AND d.stated_dow = n.dow
)
SELECT 
    d.TowerID,
    d.Place,
    d.Dedicn,
    d.County,
    d.Practice,
    d.stated_dow,
    b.busiest_dow,
    t.total_non_sun_perfs,
    s.stated_day_perfs,
    ROUND(CAST(s.stated_day_perfs AS FLOAT) / t.total_non_sun_perfs * 100, 1) AS stated_night_pct,
    CASE WHEN d.stated_dow = b.busiest_dow THEN 1 ELSE 0 END AS is_busiest
FROM deduplicated_dove d
JOIN tower_totals t ON d.TowerID = t.dove_tower_id
JOIN busiest_days b ON d.TowerID = b.dove_tower_id
JOIN stated_day_counts s ON d.TowerID = s.TowerID
WHERE d.stated_dow IS NOT NULL
ORDER BY t.total_non_sun_perfs DESC;
