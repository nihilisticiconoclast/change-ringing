-- Extract multi-stage method families with historical first-peal dates and place notation
-- Used by scripts/build_lineage_atlas.py to construct the interactive Method Lineage Tree.

SELECT 
    m.method_id,
    m.name,
    m.title,
    m.stage,
    COALESCE(m.classification, 'Principle') AS classification,
    m.notation,
    m.symmetry,
    m.lead_head,
    m.lead_head_code,
    m.length_of_lead,
    m.number_of_hunts,
    m.huntbell_path,
    m.extension_construction,
    mp.perf_date AS first_perf_date,
    mp.town AS first_perf_town,
    mp.building AS first_perf_building,
    mp.society AS first_perf_society,
    mp.dove_tower_id AS first_perf_tower_id
FROM methods m
LEFT JOIN (
    -- Take the earliest inaugural performance per method
    SELECT method_id, MIN(perf_date) AS perf_date, town, building, society, dove_tower_id
    FROM method_performances
    WHERE event_type IN ('firstTowerbellPeal', 'firstInclusionInTowerbellPeal', 'firstPerformance', 'firstHandbellPeal')
      AND perf_date IS NOT NULL
    GROUP BY method_id
) mp ON mp.method_id = m.method_id
WHERE m.name IN (
    SELECT name 
    FROM methods 
    GROUP BY name 
    HAVING COUNT(DISTINCT stage) > 1
)
ORDER BY m.name ASC, m.stage ASC, m.method_id ASC;
