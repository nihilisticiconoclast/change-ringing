-- Founder reach: methods first rung, and how many towers that spans.
--
-- The individual-firm view of 02_first_peals_by_foundry.sql. Shows why the
-- Group column matters: "John Taylor & Co" (6,933 methods) and "John Taylor
-- Bellfounders Ltd" (2,012) are the same house under different names, and
-- only collapse into one number once grouped.

SELECT
  b.Founder,
  COUNT(DISTINCT mp.method_id) AS methods_first_rung,
  COUNT(DISTINCT d.TowerID)    AS towers
FROM method_performances mp
JOIN dove  d ON d.TowerID  = mp.dove_tower_id
JOIN bells b ON b.Tower_ID = d.TowerID
WHERE mp.event_type = 'firstTowerbellPeal'
  AND b.Founder IS NOT NULL
GROUP BY b.Founder
ORDER BY methods_first_rung DESC
LIMIT 20;
