-- CHECKS: the proportion of Remembrance Sunday performances rung half-muffled
-- is 73%, 74%, 72%, 74% in 2021-24, against a 5.7% background rate.
--
-- The dates are the second Sunday in November, computed rather than looked up
-- (see remembrance_sunday() in scripts/build_rhythm_page.py) and hard-coded here
-- so this file can be run on its own.
SELECT
  p.perf_date,
  COUNT(DISTINCT p.perf_id)                                        AS performances,
  COUNT(DISTINCT CASE WHEN LOWER(f.footnote) LIKE '%muffl%'
                      THEN p.perf_id END)                          AS muffled,
  ROUND(100.0 * COUNT(DISTINCT CASE WHEN LOWER(f.footnote) LIKE '%muffl%'
                      THEN p.perf_id END) / COUNT(DISTINCT p.perf_id), 1) AS pct
FROM performances p
LEFT JOIN performance_footnotes f USING (perf_id)
WHERE p.perf_date IN ('2021-11-14','2022-11-13','2023-11-12','2024-11-10')
GROUP BY p.perf_date
ORDER BY p.perf_date;

-- The background rate the 73% is remarkable against.
SELECT ROUND(100.0 * COUNT(DISTINCT p.perf_id) /
             (SELECT COUNT(*) FROM performances), 2) AS pct_muffled_overall
FROM performances p
JOIN performance_footnotes f USING (perf_id)
WHERE LOWER(f.footnote) LIKE '%muffl%';
