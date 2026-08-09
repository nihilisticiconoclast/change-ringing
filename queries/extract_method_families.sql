-- Extract multi-stage method families, place notation, and metadata
-- Used by scripts/build_lineage_atlas.py to construct the interactive Method Lineage Atlas.

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
    m.extension_construction
FROM methods m
WHERE m.name IN (
    SELECT name 
    FROM methods 
    GROUP BY name 
    HAVING COUNT(DISTINCT stage) > 1
)
ORDER BY m.name ASC, m.stage ASC, m.method_id ASC;
