-- CHECKS: the number in "99 Tolling" is the age of the person who died.
--
-- 99 peaks on 2021-04-10, the day after the Duke of Edinburgh died aged 99.
-- 96 peaks on 2022-09-09, the day after Queen Elizabeth II died aged 96.
-- 100 peaks on 2021-02-27, Captain Tom Moore's funeral; he was 100.
-- 80 falls entirely on 2024-06-06, D-Day's eightieth anniversary, and 70 on the
-- Platinum Jubilee -- so the number is not always an age, but it is always the
-- count of whatever is being marked. 365 was rung on 2021-03-23, one year after
-- the first lockdown: one stroke per day.
--
-- No age or date-of-birth column exists in any table of any of the four corpora.
-- This is the only place in the data where a person's age appears at all.
SELECT
  p.method,
  p.perf_date,
  COUNT(*) AS n
FROM performances p
-- GLOB, not LIKE: SQLite's LIKE has no character classes, and a chain of
-- LIKE '9%' OR LIKE '1%' ... is both unreadable and wrong at the edges.
WHERE p.method GLOB '[0-9]*'
  AND p.method LIKE '%Tolling%'
GROUP BY p.method, p.perf_date
HAVING COUNT(*) >= 3
ORDER BY COUNT(*) DESC;
