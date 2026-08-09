-- Atlas · the cross-corpus join
--
-- The question the whole project exists to answer: whose bells do ringers
-- choose when trying a method that has never been rung before?
--
-- Four hops across three separately maintained corpora --
--   CCCBR Methods Library  (method_performances, event_type firstTowerbellPeal)
--     -> Dove towers       (via the adjudicated dove_tower_id)
--     -> Dove bells        (via Tower_ID)
--     -> Dove founders     (via Founder = Name)
--
-- This only became answerable once method_performances.dove_tower_id was
-- populated; see scripts/apply_location_adjudication.py. 22,111 of 30,734
-- first-performance records carry a tower link, so this counts those.
--
-- A ring usually mixes founders -- augmented over centuries, bells recast --
-- so one peal can count towards more than one tradition. These are therefore
-- overlapping counts, not a partition, and must not be summed.

SELECT
  f."Group"                        AS founder_group,
  COUNT(DISTINCT mp.method_id)     AS methods_first_rung
FROM method_performances mp
JOIN dove     d ON d.TowerID  = mp.dove_tower_id
JOIN bells    b ON b.Tower_ID = d.TowerID
JOIN founders f ON f.Name     = b.Founder
WHERE mp.event_type = 'firstTowerbellPeal'
  AND f."Group" IS NOT NULL
GROUP BY f."Group"
ORDER BY methods_first_rung DESC;
