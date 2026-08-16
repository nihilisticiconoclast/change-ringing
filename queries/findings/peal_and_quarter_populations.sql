-- Are quarter-peal ringers and peal ringers two populations? No. Roadmap item 23.
--
-- The folk model says so: the Sunday band and the peal circuit are different
-- people who happen to share buildings. It is one of the things every ringer
-- believes and nobody has been able to check, because checking it needs a
-- decade of performances joined to resolved identities. The corpus now has both.
--
-- FIRST, WHAT THE CORPUS CANNOT SEE, because it changes the question. Of 293,471
-- performances, 198,715 are 1,000-1,399 changes and 33,288 of the Sunday ones are
-- exactly 1,260 -- these are quarter peals. **Ordinary Sunday service ringing --
-- rounds, call changes, half an hour before the service -- is essentially never
-- reported to BellBoard and is absent from this corpus.** So the answerable
-- question is not "service band vs peal circuit"; it is "quarter ringers vs peal
-- ringers", which is the same sociological question with an honest name.
--
-- THE ANSWER. Peal share per canonical ringer, ringers with >= 50 appearances:
--
--     0-9  % peals   3,979  ############################################
--    10-19 % peals     572  ######
--    20-29 % peals     306  ###
--    30-39 % peals     241  ##
--    40-49 % peals     176  ##
--    50-59 % peals     149  #
--    60-69 % peals     157  #
--    70-79 % peals     108  #
--    80-89 % peals     113  #
--    90-99 % peals      73  #
--    n = 5,934, median peal share 3.0%
--
-- A steep monotonic decay with **no second mode**. Two populations would show two
-- humps; there is one, and a long thin tail. Peal-exclusive ringers effectively
-- do not exist: 0.1% at this activity level.
--
-- Nor is it two kinds of TOWER. The same shape appears over 1,226 towers with 50+
-- performances -- 610 in the 0-9% band, decaying monotonically, median 10.0%.
--
-- Nor is it graduation. Mean peal share by years active is flat between 9.5% and
-- 14% from one year to eleven; it does not climb with experience. (The 12-year
-- bucket is the full width of the corpus and means "present throughout", so it is
-- confounded and excluded from that reading.)
--
-- So the strong folk model is wrong and a weaker one survives: **peal ringing is
-- an occasional activity spread thinly across one community, not a circuit with
-- its own membership.** About half of ringers with 50+ appearances have rung at
-- least one peal, which is far more inclusive than "a separate elite" implies,
-- and the median such ringer still spends 97% of their reported ringing on
-- quarters.
--
-- CAVEAT ON IDENTITY, AND WHY THIS QUERY IS THE WEAKER OF TWO VIEWS.
--
-- The figures quoted above use canonical identities from
-- data/ringer_identity_candidates.csv -- 56,340 entities, accuracy unmeasured.
-- That resolution lives in a CSV rather than a table, so THIS query cannot use
-- it: it groups raw names, and the two disagree in an instructive way.
--
--                      canonical ids        raw names
--     0-9  % peals          3,979             4,659
--     80-89% peals            113               196
--     90-99% peals             73               165
--
-- Raw names produce a visibly fatter RIGHT tail. Splitting one person into
-- variants gives each fragment fewer appearances drawn from a narrower slice of
-- their ringing, so a fragment can look 100% peal or 100% quarter when the
-- person is neither. Unresolved identity therefore manufactures apparent
-- specialists at BOTH ends -- it does not simply thicken the left bar, which is
-- what an earlier draft of this comment claimed.
--
-- That matters for the conclusion: the raw-name histogram is the one that looks
-- more like two populations, and it is the less trustworthy of the two. The
-- canonical version, with the cleaner monotonic decay, is the finding.
-- scripts/analyse_peal_populations.py computes it and is what the numbers above
-- come from; this query is kept because it needs nothing but the database, and
-- because the gap between the two is itself worth being able to see.

WITH per_ringer AS (
    SELECT TRIM(r.name) AS ringer,
           COUNT(*) AS appearances,
           SUM(CASE WHEN p.changes >= 5000 THEN 1 ELSE 0 END) AS peals
    FROM performance_ringers r
    JOIN performances p ON p.perf_id = r.perf_id
    WHERE r.name IS NOT NULL AND TRIM(r.name) != ''
      AND p.changes IS NOT NULL
    GROUP BY ringer
    HAVING COUNT(*) >= 50
)
-- MIN(..., 9) clamps the top band: a ringer who is 100% peals gives
-- CAST(10.0 * 1 AS INT) = 10 and lands in a nonexistent "100-109%" bucket, which
-- the first draft of this query duly reported for three ringers.
SELECT (10 * MIN(CAST(10.0 * peals / appearances AS INT), 9)) AS peal_share_band_pct,
       COUNT(*)                                       AS ringers,
       SUM(appearances)                               AS appearances_in_band
FROM per_ringer
GROUP BY peal_share_band_pct
ORDER BY peal_share_band_pct;
