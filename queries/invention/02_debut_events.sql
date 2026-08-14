-- Every dated first-performance record, one row each, with its place and band.
--
-- Returns method_id deliberately, and does the grouping in Python. The reason is
-- a counting trap: `method_performances` holds up to fifteen event types per
-- method -- first tower-bell peal, first handbell quarter, first inclusion in a
-- tower-bell peal, and so on -- each with its own date and place. Aggregating in
-- SQL and summing the group counts therefore counts a method once per event, and
-- "where methods come from" silently becomes "where first-performance events of
-- any kind happened", which is a different and much larger number.
--
-- scripts/build_invention_page.py keeps only the record whose date equals the
-- method's own earliest date, so each method is attributed to exactly one place.
-- Ties -- two event types on the same day at different towers -- are broken by
-- preferring the row that names a tower, then by event type, so the choice is
-- deterministic rather than dependent on row order.
SELECT
  mp.method_id      AS method_id,
  mp.perf_date      AS debut_date,
  mp.event_type     AS event_type,
  mp.building       AS building,
  mp.town           AS town,
  mp.county         AS county,
  mp.society        AS society,
  mp.dove_tower_id  AS dove_tower_id
FROM method_performances mp
WHERE mp.perf_date IS NOT NULL AND mp.perf_date <> ''
ORDER BY mp.method_id, mp.perf_date;

-- 1: the keyboard-ringing event types, which exist only because of the pandemic.
-- "Ringing Room" is a browser-based platform ringers moved to when towers closed
-- in March 2020; the CCCBR library grew four new first-performance categories to
-- record it. Every one of these events but a single 2014 outlier is 2020 or later.
--
-- The contrast with the debut count is the point. Ringing Room carries 1,142
-- first-performance events and only 115 method debuts: the platform was used
-- overwhelmingly to achieve a NEW KIND OF FIRST in methods that already existed,
-- not to bring new methods into being.
SELECT
  event_type                  AS event_type,
  SUBSTR(perf_date, 1, 4)     AS year,
  COUNT(*)                    AS events
FROM method_performances
WHERE event_type LIKE '%Keyboard%'
  AND perf_date IS NOT NULL AND perf_date <> ''
GROUP BY event_type, SUBSTR(perf_date, 1, 4)
ORDER BY year, events DESC;

-- 2: every first-performance event at a virtual venue, against the number of
-- those that are the method's own earliest date. 1,142 against 115.
SELECT
  COUNT(*)                                                             AS events,
  SUM(CASE WHEN mp.perf_date = (
        SELECT MIN(x.perf_date) FROM method_performances x
        WHERE x.method_id = mp.method_id
          AND x.perf_date IS NOT NULL AND x.perf_date <> ''
      ) THEN 1 ELSE 0 END)                                             AS debuts
FROM method_performances mp
WHERE mp.town LIKE '%ringing room%' OR mp.building LIKE '%ringing room%';
