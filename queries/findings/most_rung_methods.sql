-- CHECKS: which methods are actually rung, as opposed to registered.
--
-- Not answerable before schema/005: `performances.method` is free text and had no
-- link to the 25,066-method library, so "there are 9,680 Major methods" and "how
-- often is each of them rung" were separate universes.
--
-- Uses v_performance_methods, which excludes the `low` confidence band. Swap it
-- for `performance_methods` if you want those too, and expect the ordering of the
-- long tail to move.
SELECT
  method_title,
  stage,
  classification,
  COUNT(*)                                     AS performances,
  SUM(changes >= 5000)                         AS peals,
  MIN(perf_date)                               AS first_seen,
  COUNT(DISTINCT dove_tower_id)                AS rings
FROM v_performance_methods
GROUP BY method_id
ORDER BY performances DESC
LIMIT 25;

-- The counterpart, and the more interesting half: how much of the library is
-- never rung at all. 2021-24 only, so this is "not rung in four years", not
-- "never rung" -- the survival question needs the backfill (roadmap 8b).
SELECT
  m.stage,
  COUNT(*)                                                       AS methods_in_library,
  SUM(CASE WHEN pm.method_id IS NULL THEN 1 ELSE 0 END)           AS never_rung_in_window,
  ROUND(100.0 * SUM(CASE WHEN pm.method_id IS NULL THEN 1 ELSE 0 END)
        / COUNT(*), 1)                                           AS pct_unrung
FROM methods m
LEFT JOIN (SELECT DISTINCT method_id FROM performance_methods) pm
       ON pm.method_id = m.method_id
WHERE m.stage BETWEEN 4 AND 12
GROUP BY m.stage
ORDER BY m.stage;
