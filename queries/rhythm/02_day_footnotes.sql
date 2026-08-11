-- The most repeated footnote on each day, so an unusual day can be identified
-- from the corpus rather than from the author's memory of the news.
--
-- This matters methodologically. The page flags anomalous days by a purely
-- statistical rule -- volume against the median of the same weekday nearby --
-- and then reads the reason off this query. Nothing about which days count as
-- events is hand-entered.
--
-- Restricted to footnotes repeated at least three times on the day: a national
-- occasion produces hundreds of bands independently writing near-identical
-- text, whereas "First quarter in the method" is noise at any volume.
SELECT
  p.perf_date       AS d,
  f.footnote        AS footnote,
  COUNT(*)          AS n
FROM performance_footnotes f
JOIN performances p USING (perf_id)
WHERE p.perf_date BETWEEN '2021-01-01' AND '2024-12-31'
GROUP BY p.perf_date, f.footnote
HAVING COUNT(*) >= 3
ORDER BY p.perf_date, COUNT(*) DESC;
