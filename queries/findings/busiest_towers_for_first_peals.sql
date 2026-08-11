-- Which towers host the most method first-peals?
--
-- Quoted in the atlas: John Taylor & Co's own Bell Foundry Tower at
-- Loughborough tops it at 507 -- a foundry that keeps a ring on site gets to
-- host the experiments. Meldreth 415, Barrow Gurney 335, Sproxton 294.
--
-- Note the join caveat: dove.TowerID is NOT unique (7,262 rows, 7,249 distinct
-- IDs -- 13 towers hold more than one ring), so grouping by TowerID is right
-- here but joining dove to itself on TowerID would double-count those 13.

SELECT
  d.Place,
  d.Dedicn,
  COUNT(*) AS first_peals
FROM method_performances mp
JOIN v_towers_unique d ON d.TowerID = mp.dove_tower_id
WHERE mp.event_type = 'firstTowerbellPeal'
GROUP BY d.TowerID
ORDER BY first_peals DESC
LIMIT 20;
