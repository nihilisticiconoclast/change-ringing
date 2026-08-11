-- CHECKS: "September is the busiest ringing month (12,067 performances) and
-- nobody knows why" -- recorded in docs/IDEAS.md and the README, and wrong.
--
-- The count is right. The interpretation is not: half of September's total is
-- the eleven days between the death of Elizabeth II and her funeral. Run this
-- and the month explains itself.
SELECT
  perf_date,
  COUNT(*)                                        AS performances,
  SUM(method LIKE '%Tolling%')                     AS tolling,
  COUNT(DISTINCT dove_tower_id)                    AS rings
FROM performances
WHERE perf_date LIKE '2022-09%'
GROUP BY perf_date
ORDER BY COUNT(*) DESC
LIMIT 8;

-- The whole month, all four years, against the month minus those eleven days:
--   12,067 -> 5,561, so 54% of every September performance in the corpus falls
--   inside one fortnight of 2022. Removing the full set of 24 nationally
--   anomalous days -- a slightly wider net, defined by rule in
--   scripts/build_rhythm_page.py -- gives 6,130, which moves September from 1st
--   of twelve months to 7th. See docs/rhythm.html, section seven.
SELECT
  SUM(1)                                                       AS all_september,
  SUM(CASE WHEN perf_date NOT BETWEEN '2022-09-08' AND '2022-09-19'
           THEN 1 ELSE 0 END)                                  AS excluding_that_week
FROM performances
WHERE strftime('%m', perf_date) = '09';
