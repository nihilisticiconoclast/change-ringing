-- CHECKS: the coverage and confidence claims made for schema/005.
--
-- Run this before trusting any figure derived from performance_methods. The
-- unresolved table is not an appendix -- it is half the result, and a coverage
-- claim that cites only the linked side is not a coverage claim.
SELECT
  (SELECT COUNT(*) FROM performances)                                  AS performances,
  (SELECT COUNT(DISTINCT perf_id) FROM performance_methods)            AS with_a_method_link,
  (SELECT COUNT(*) FROM performance_methods)                           AS method_links,
  (SELECT COUNT(*) FROM performance_method_unresolved)                 AS unresolved;

-- Confidence distribution. A band with zero rows is a finding in itself: a scale
-- that never emits its bottom band is not a scale, it is a label.
SELECT confidence, COUNT(*) AS links, COUNT(DISTINCT perf_id) AS performances
FROM performance_methods
GROUP BY confidence
ORDER BY links DESC;

-- Why the rest failed. `not_a_method` is not a failure: tolling, general ringing,
-- call changes and rounds are bells being rung without a method being rung, and
-- they should never acquire a method_id.
SELECT reason, COUNT(*) AS performances
FROM performance_method_unresolved
GROUP BY reason
ORDER BY performances DESC;

-- How far off the spliced oracle was when it failed, which is what makes the
-- failures actionable rather than merely counted. The -1 group is dominated by
-- abbreviations the resolver deliberately does not expand ("Rev Court" for
-- "Reverse Court", "Cambridge SM" for "Cambridge Surprise Minor").
SELECT found_n - expected_n AS methods_off, COUNT(*) AS performances
FROM performance_method_unresolved
WHERE reason = 'spliced_count_mismatch' AND expected_n IS NOT NULL
GROUP BY 1
ORDER BY performances DESC;
