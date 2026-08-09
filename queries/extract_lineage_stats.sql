-- Extract overall method corpus summary statistics and stage distributions
-- Used by scripts/build_lineage_atlas.py for top-level figures.

SELECT 
    COUNT(*) AS total_methods,
    COUNT(DISTINCT name) AS distinct_names,
    COUNT(DISTINCT CASE WHEN extension_construction IS NOT NULL AND extension_construction != '' THEN method_id END) AS labeled_methods,
    COUNT(DISTINCT CASE WHEN stage % 2 = 0 THEN method_id END) AS even_stage_methods,
    COUNT(DISTINCT CASE WHEN stage % 2 = 1 THEN method_id END) AS odd_stage_methods,
    MIN(stage) AS min_stage,
    MAX(stage) AS max_stage
FROM methods;
