-- Method first-peals by decade.
--
-- 1950s 450 · 1990s 3,095 · 2010s 3,646 · 2020s 1,686 so far. The post-war
-- growth in new methods is the shape here.
--
-- perf_date is ISO where it parses at all, but the corpus reaches back to
-- 1777, so the GLOB guard drops rows with partial or malformed dates rather
-- than letting substr() invent a decade from them.

SELECT
  substr(perf_date, 1, 3) || '0s' AS decade,
  COUNT(*)                        AS first_peals
FROM method_performances
WHERE event_type = 'firstTowerbellPeal'
  AND perf_date GLOB '[0-9][0-9][0-9][0-9]-*'
GROUP BY decade
ORDER BY decade;
