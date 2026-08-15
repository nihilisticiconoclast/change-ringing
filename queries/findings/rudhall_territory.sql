-- Rudhall of Gloucester: the regional foundry.
--
-- The atlas's central claim is that foundries had catchment areas, and Rudhall
-- is the clearest case -- 2,745 surviving bells cast 1679-1835, clustered on
-- the Severn valley and the Welsh marches, with almost nothing beyond.
--
-- This is the numeric form of what the map shows when you select Rudhall.
-- Compare it against Loughborough, which is national.

SELECT
  d.County,
  COUNT(*) AS bells
FROM bells b
JOIN founders f ON f.Name     = b.Founder
JOIN v_towers_unique d ON d.TowerID  = b.Tower_ID
WHERE f."Group" = 'Rudhall'
GROUP BY d.County
ORDER BY bells DESC
LIMIT 15;
