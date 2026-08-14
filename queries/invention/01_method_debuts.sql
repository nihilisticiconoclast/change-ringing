-- One row per method that has ever been rung, with the date it first was.
--
-- "Invention" is not a field anywhere in the corpus, and nothing records who
-- devised a method. What the CCCBR library records is the first PERFORMANCE, and
-- in change ringing that is close to the same thing: a method enters the
-- collection by being rung and named. So this is a debut date, and the page says
-- "first rung" rather than "invented" throughout -- a method can be worked out on
-- paper years before a band attempts it, and the gap is invisible here.
--
-- min(perf_date) across all 15 event types, not just firstTowerbellPeal. A method
-- whose debut was a handbell quarter peal debuted then; restricting to tower-bell
-- peals would date it to whenever tower ringers got round to it, or drop it.
SELECT
  m.method_id                AS method_id,
  m.title                    AS title,
  m.name                     AS name,
  m.stage                    AS stage,
  m.classification           AS classification,
  m.cls_little               AS little,
  MIN(mp.perf_date)          AS debut
FROM methods m
JOIN method_performances mp USING (method_id)
WHERE mp.perf_date IS NOT NULL AND mp.perf_date <> ''
GROUP BY m.method_id;

-- 1: methods with no first-performance record at all. Not a defect to fix -- the
-- library holds methods that are registered but have no dated performance -- but
-- the denominator for everything on the page, so it is stated.
SELECT
  (SELECT COUNT(*) FROM methods)                                        AS methods_total,
  (SELECT COUNT(DISTINCT method_id) FROM method_performances
     WHERE perf_date IS NOT NULL AND perf_date <> '')                   AS with_a_debut_date;
