-- Does a tower ring on the night Dove says it does? Roadmap item 21 / Gemini Task 6.
--
-- Dove records a practice night for 3,513 towers. BellBoard records 293,471 dated
-- performances. Neither corpus can be checked against itself; together they can,
-- and until now nobody had put them side by side.
--
-- STATEMENT 1 (below) is the Mon-Sat comparison. STATEMENT 2 repeats it excluding
-- Saturday, which is where the finding actually is -- see the bottom of this file.
--
-- MEASURED 2026-08-15, from THIS query:
--
--   Mon-Sat, towers with >=20 non-Sunday short performances
--     1,569 towers; the stated night is the busiest for 428 (27.3%), against
--     16.7% by chance. Mean share of non-Sunday ringing on the stated night 22.0%.
--
--   Mon-Fri, Saturday excluded
--     1,054 towers; the stated night is the busiest for 463 (43.9%), against
--     20.0% by chance. Mean share of weekday ringing on the stated night 31.0%.
--
-- **Excluding Saturday is what makes the signal visible**: agreement more than
-- doubles chance. Saturday is outing and peal-attempt day, and it competes with a
-- weekday practice in a way the other days do not.
--
-- TWO CONFOUNDS, BOTH LOAD-BEARING.
--
-- 1. Sunday service ringing dominates reported short performances at nearly every
--    tower, so an outright "busiest day of the week" comparison returns Sunday
--    almost everywhere and measures nothing. A first cut that did not exclude it
--    scored 15.9% and looked like a scandal about Dove's data quality. It was not.
--
-- 2. **BellBoard records REPORTED performances -- overwhelmingly quarter peals.**
--    Ordinary practice-night ringing is almost never reported. So this measures
--    where reported quarters cluster, which is a proxy for practice night and not
--    the thing itself. 27.3% and 43.9% are LOWER BOUNDS on agreement, **not**
--    estimates of how many Dove entries are stale. A tower that practises on
--    Tuesday and rings its quarters on Saturday scores zero here while Dove is
--    perfectly correct.
--
-- TIE-BREAK: MIN(dow) picks the earliest day when two days tie on the maximum,
-- which is arbitrary but deterministic. It can only ever lower the agreement rate
-- for towers whose stated night is late in the week, so the figures above are
-- conservative in that direction too.
--
-- Dove is deduplicated inline rather than through v_towers_unique because the
-- Practice column is not carried by that view. Same GROUP BY, same effect; see
-- docs/decisions/001 for why the raw table must never be joined directly.


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


-- ---------------------------------------------------------------------------
-- STATEMENT 2: the same comparison, Saturday excluded. This is the one that
-- carries the finding -- 43.9% against a 20.0% chance baseline.
-- ---------------------------------------------------------------------------
WITH deduplicated_dove AS (
    SELECT TowerID, MAX(Place) AS Place, MAX(County) AS County, MAX(Practice) AS Practice,
        CASE
            WHEN MAX(Practice) LIKE 'Mon%' THEN 1 WHEN MAX(Practice) LIKE 'Tue%' THEN 2
            WHEN MAX(Practice) LIKE 'Wed%' THEN 3 WHEN MAX(Practice) LIKE 'Thu%' THEN 4
            WHEN MAX(Practice) LIKE 'Fri%' THEN 5 ELSE NULL
        END AS stated_dow
    FROM dove
    WHERE Practice IS NOT NULL AND Practice != ''
      AND Practice NOT LIKE '%alt%' AND Practice NOT LIKE '%arrangement%'
    GROUP BY TowerID
),
weekday_perfs AS (
    SELECT p.dove_tower_id,
           CAST(strftime('%w', p.perf_date) AS INTEGER) AS dow,
           COUNT(*) AS perf_count
    FROM performances p
    WHERE p.dove_tower_id IS NOT NULL AND p.perf_date IS NOT NULL
      AND CAST(strftime('%w', p.perf_date) AS INTEGER) BETWEEN 1 AND 5
      AND (p.changes IS NULL OR p.changes < 5000)
    GROUP BY 1, 2
),
tower_totals AS (
    SELECT dove_tower_id, SUM(perf_count) AS total_weekday, MAX(perf_count) AS max_day
    FROM weekday_perfs GROUP BY dove_tower_id HAVING SUM(perf_count) >= 20
),
busiest AS (
    SELECT w.dove_tower_id, MIN(w.dow) AS busiest_dow
    FROM weekday_perfs w
    JOIN tower_totals t ON t.dove_tower_id = w.dove_tower_id AND w.perf_count = t.max_day
    GROUP BY w.dove_tower_id
)
SELECT d.TowerID, d.Place, d.County, d.Practice, d.stated_dow, b.busiest_dow,
       t.total_weekday,
       COALESCE(s.perf_count, 0) AS stated_night_perfs,
       ROUND(100.0 * COALESCE(s.perf_count, 0) / t.total_weekday, 1) AS stated_night_pct,
       CASE WHEN d.stated_dow = b.busiest_dow THEN 1 ELSE 0 END AS is_busiest
FROM deduplicated_dove d
JOIN tower_totals t ON t.dove_tower_id = d.TowerID
JOIN busiest b       ON b.dove_tower_id = d.TowerID
LEFT JOIN weekday_perfs s ON s.dove_tower_id = d.TowerID AND s.dow = d.stated_dow
WHERE d.stated_dow IS NOT NULL
ORDER BY t.total_weekday DESC;
