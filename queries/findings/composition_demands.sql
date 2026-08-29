-- Change Ringing: What a Composition Demands (Roadmap Item R-40 / G-11)
--
-- Analyzes the 86,054 compositions in CompLib to measure:
-- 1. Stage breakdown and calling availability
-- 2. Length categories (peals, quarters, touches)
-- 3. Spliced vs single-method composition rates
-- 4. Tenor fixed course-head shares across stages
-- 5. Part-count distribution from parthead transposition markers

-- 1. Stage distribution & calling coverage
SELECT 
    stage,
    COUNT(*) AS total_compositions,
    COUNT(CASE WHEN calling IS NOT NULL AND calling != '' THEN 1 END) AS with_calling,
    ROUND(COUNT(CASE WHEN calling IS NOT NULL AND calling != '' THEN 1 END) * 100.0 / COUNT(*), 1) AS calling_pct,
    COUNT(CASE WHEN partheads IS NOT NULL AND partheads != '' THEN 1 END) AS with_partheads
FROM compositions
GROUP BY stage
ORDER BY total_compositions DESC;

-- 2. Length categories
SELECT 
    CASE 
        WHEN length < 1000 THEN 'touch (<1,000)'
        WHEN length BETWEEN 1000 AND 1999 THEN 'quarter peal (1,000-1,999)'
        WHEN length BETWEEN 2000 AND 4999 THEN 'half peal (2,000-4,999)'
        WHEN length BETWEEN 5000 AND 5400 THEN 'standard peal (5,000-5,400)'
        WHEN length BETWEEN 5401 AND 9999 THEN 'long peal (5,401-9,999)'
        ELSE 'record / long length (10,000+)'
    END AS length_category,
    COUNT(*) AS count,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM compositions WHERE length IS NOT NULL), 1) AS pct
FROM compositions
WHERE length IS NOT NULL
GROUP BY length_category
ORDER BY count DESC;

-- 3. Spliced vs Single-method rate by stage
SELECT 
    c.stage,
    COUNT(DISTINCT c.composition_id) AS total_compositions,
    COUNT(DISTINCT CASE WHEN cm_counts.num_methods > 1 THEN c.composition_id END) AS spliced_compositions,
    ROUND(COUNT(DISTINCT CASE WHEN cm_counts.num_methods > 1 THEN c.composition_id END) * 100.0 / COUNT(DISTINCT c.composition_id), 1) AS spliced_pct
FROM compositions c
JOIN (
    SELECT composition_id, COUNT(*) AS num_methods
    FROM composition_methods
    GROUP BY composition_id
) cm_counts ON cm_counts.composition_id = c.composition_id
WHERE c.stage IN (6, 7, 8, 10, 12)
GROUP BY c.stage
ORDER BY c.stage;

-- 4. Tenor fixed at Home by stage (coursehead masks)
SELECT
    stage,
    COUNT(*) AS total_compositions,
    COUNT(CASE 
        WHEN stage = 6 AND coursehead_masks NOT LIKE '%x' AND coursehead_masks LIKE '%6' THEN 1
        WHEN stage = 7 AND coursehead_masks NOT LIKE '%x' AND coursehead_masks LIKE '%7' THEN 1
        WHEN stage = 8 AND coursehead_masks NOT LIKE '%x' AND coursehead_masks LIKE '%8' THEN 1
        WHEN stage = 10 AND coursehead_masks NOT LIKE '%x' AND coursehead_masks LIKE '%0' THEN 1
        WHEN stage = 12 AND coursehead_masks NOT LIKE '%x' AND (coursehead_masks LIKE '%2' OR coursehead_masks LIKE '%T' OR coursehead_masks LIKE '%t') THEN 1
        ELSE NULL
    END) AS tenor_fixed_count,
    ROUND(COUNT(CASE 
        WHEN stage = 6 AND coursehead_masks NOT LIKE '%x' AND coursehead_masks LIKE '%6' THEN 1
        WHEN stage = 7 AND coursehead_masks NOT LIKE '%x' AND coursehead_masks LIKE '%7' THEN 1
        WHEN stage = 8 AND coursehead_masks NOT LIKE '%x' AND coursehead_masks LIKE '%8' THEN 1
        WHEN stage = 10 AND coursehead_masks NOT LIKE '%x' AND coursehead_masks LIKE '%0' THEN 1
        WHEN stage = 12 AND coursehead_masks NOT LIKE '%x' AND (coursehead_masks LIKE '%2' OR coursehead_masks LIKE '%T' OR coursehead_masks LIKE '%t') THEN 1
        ELSE NULL
    END) * 100.0 / COUNT(*), 1) AS tenor_fixed_pct
FROM compositions
WHERE stage IN (6, 7, 8, 10, 12)
GROUP BY stage
ORDER BY stage;
