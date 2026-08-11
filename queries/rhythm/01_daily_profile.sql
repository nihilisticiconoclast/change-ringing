-- One row per calendar day in the BellBoard window, with everything the
-- Rhythm page needs: volume, tower/handbell split, length class, and the two
-- acoustic markers -- tolling and muffled ringing.
--
-- Deliberately one query rather than five. The calendar, the weekday pulse,
-- the seasonal shape, the anomaly detection and the grammar scatter are all
-- derived from these ~1,460 rows, so every figure on the page is guaranteed to
-- be reading the same underlying counts.
--
-- 'Tolling' is not a method. It is a single bell struck slowly, and BellBoard
-- records it in the method field, so it can be counted the same way. See
-- docs/IDEAS.md option C for why any method-frequency chart must exclude it.
SELECT
  p.perf_date                                              AS d,
  COUNT(*)                                                 AS n,
  SUM(p.ring_type = 'tower')                               AS n_tower,
  SUM(p.ring_type = 'hand')                                AS n_hand,
  SUM(p.changes >= 5000)                                   AS n_peal,
  SUM(p.changes >= 1250 AND p.changes < 5000)              AS n_quarter,
  SUM(p.method LIKE '%Tolling%')                           AS n_toll,
  SUM(EXISTS (SELECT 1 FROM performance_footnotes f
              WHERE f.perf_id = p.perf_id
                AND LOWER(f.footnote) LIKE '%muffl%'))     AS n_muffled,
  COUNT(DISTINCT p.dove_tower_id)                          AS n_towers
FROM performances p
WHERE p.perf_date BETWEEN '2021-01-01' AND '2024-12-31'
GROUP BY p.perf_date
ORDER BY p.perf_date;
