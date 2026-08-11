-- Tolling performances where the method field carries a number: "99 Tolling",
-- "365 Tolling", "96 Half Muffled Tolling".
--
-- The number is not a method and not a change count. It is the number of times
-- the bell was struck, and it encodes what is being marked -- most often the age
-- of the person who has died, sometimes an anniversary, once a number of days.
-- That makes an age a machine-readable field in a corpus that has no age column,
-- which is the kind of thing free text does and a normalised schema does not.
--
-- SQLite has no regular expressions, so this query returns the candidate rows
-- and scripts/build_rhythm_page.py extracts the leading integer with an anchored
-- pattern. Doing it here with LIKE and SUBSTR would be unreadable and would
-- still miss "Tolling The Nine Tailors and 99 Years", which this deliberately
-- does not try to catch: the strict form is countable, the prose form is not.
SELECT
  p.method     AS method,
  p.perf_date  AS d,
  COUNT(*)     AS n
FROM performances p
WHERE p.method LIKE '%Tolling%'
  AND p.perf_date BETWEEN '2021-01-01' AND '2024-12-31'
GROUP BY p.method, p.perf_date
ORDER BY COUNT(*) DESC;
