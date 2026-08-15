-- Every non-empty footnote, with the date and length of the performance it
-- belongs to. This is the whole input to the occasion classifier; the
-- categorisation itself happens in scripts/build_occasions_page.py, because it
-- is regex work that SQLite cannot express.
--
-- ONE ROW PER FOOTNOTE, NOT PER PERFORMANCE. 183,315 footnotes attach to 122,573
-- performances -- a mean of 1.5 each -- so every count derived from this query
-- is a count of footnotes. Calling them performances overstates by half, and
-- the page says "footnotes" everywhere for that reason.
SELECT
  p.perf_date  AS perf_date,
  p.changes    AS changes,
  f.footnote   AS footnote
FROM performance_footnotes f
JOIN performances p ON f.perf_id = p.perf_id
WHERE f.footnote IS NOT NULL AND f.footnote != '';

-- Denominators the page needs in order to state its own coverage honestly.
SELECT
  (SELECT COUNT(*) FROM performance_footnotes
     WHERE footnote IS NOT NULL AND footnote != '')                AS footnotes,
  (SELECT COUNT(DISTINCT perf_id) FROM performance_footnotes
     WHERE footnote IS NOT NULL AND footnote != '')                AS performances_with_a_footnote,
  (SELECT COUNT(*) FROM performances)                              AS performances_total;
