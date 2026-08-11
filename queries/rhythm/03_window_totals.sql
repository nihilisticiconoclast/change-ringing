-- Headline figures for the page, kept here so each can be re-run on its own.

-- 0: performances, distinct days, distinct rings reached, in the window
SELECT COUNT(*), COUNT(DISTINCT perf_date), COUNT(DISTINCT dove_ring_id)
FROM performances
WHERE perf_date BETWEEN '2021-01-01' AND '2024-12-31';

-- 1: the baseline rate of muffled ringing across the whole window, which is
-- what makes Remembrance Sunday's 73% remarkable rather than merely high
SELECT COUNT(DISTINCT p.perf_id) * 1.0 / (SELECT COUNT(*) FROM performances)
FROM performances p
JOIN performance_footnotes f USING (perf_id)
WHERE LOWER(f.footnote) LIKE '%muffl%';
