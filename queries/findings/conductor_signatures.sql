-- Query for analyzing conductor speeds and identifying "Fast Ships" vs "Slow Ships"
-- Depends on: performances, performance_ringers
-- Requires canonical identity resolution for conductors

WITH parsed_performances AS (
    SELECT 
        p.perf_id,
        pr.name AS raw_conductor,
        -- Extract hours and minutes from duration string (e.g. "2h 45")
        CAST(SUBSTR(p.duration, 1, INSTR(p.duration, 'h') - 1) AS INTEGER) * 60 +
        CASE 
            WHEN INSTR(p.duration, 'm') > 0 
            THEN CAST(SUBSTR(p.duration, INSTR(p.duration, 'h') + 1, INSTR(p.duration, 'm') - INSTR(p.duration, 'h') - 1) AS INTEGER)
            ELSE CAST(SUBSTR(p.duration, INSTR(p.duration, 'h') + 1) AS INTEGER)
        END AS duration_mins,
        p.changes,
        -- Extract cwt weight from tenor string (e.g. "12-1-14")
        CAST(SUBSTR(p.tenor, 1, INSTR(p.tenor, '-') - 1) AS FLOAT) +
        CAST(SUBSTR(p.tenor, INSTR(p.tenor, '-') + 1, INSTR(SUBSTR(p.tenor, INSTR(p.tenor, '-') + 1), '-') - 1) AS FLOAT) / 4 +
        CAST(SUBSTR(p.tenor, INSTR(p.tenor, '-') + INSTR(SUBSTR(p.tenor, INSTR(p.tenor, '-') + 1), '-')) AS FLOAT) / 112 AS tenor_cwt
    FROM performances p
    JOIN performance_ringers pr ON p.perf_id = pr.perf_id
    WHERE pr.conductor = 1 
      AND p.ring_type = 'tower'
      AND p.changes > 5000
      AND p.duration LIKE '%h%'
      AND p.tenor LIKE '%-%-%'
)
SELECT 
    raw_conductor,
    COUNT(*) AS peals_conducted,
    AVG(CAST(changes AS FLOAT) / duration_mins) AS avg_cpm,
    AVG(tenor_cwt) AS avg_tenor
FROM parsed_performances
WHERE tenor_cwt >= 10 AND tenor_cwt < 16  -- Control for bell weight
GROUP BY raw_conductor
HAVING COUNT(*) >= 20
ORDER BY avg_cpm DESC;
