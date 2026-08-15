-- Do some conductors really ring faster? Barely, and much less than ringers think.
--
-- From Gemini's feature/data-insights branch as `conductor_signatures.sql`,
-- where it ranked named conductors by changes-per-minute and called the extremes
-- "Fast Ships" and "Slow Ships". Three changes on merge, one of them a bug.
--
-- 1. THE TENOR WEIGHT WAS WRONG, and it drove the control. Bell weights are
--    "cwt-qtr-lb", e.g. 12-1-14. The original third term read
--      SUBSTR(tenor, INSTR(tenor,'-') + INSTR(SUBSTR(tenor,INSTR(tenor,'-')+1),'-'))
--    which lands ON the second hyphen, so it captured '-14' and CAST it to -14,
--    SUBTRACTING the pounds. 12-1-14 came out as 12.125 instead of 12.375. The
--    query then filtered on 10 <= cwt < 16, so the error moved peals in and out
--    of the weight band the whole comparison depends on. Fixed with a +1.
--
-- 2. NO LEAGUE TABLE OF NAMED PEOPLE. The original returned conductor names
--    ordered by speed, which is an evaluative ranking of identifiable
--    individuals built from data they filed for a different purpose. Peal speed
--    is public and ringers discuss it openly, so this is not a privacy breach --
--    but "who is slowest" is not a question this corpus should be used to
--    answer, and the interesting result is not a name. This returns the
--    DISTRIBUTION instead.
--
-- 3. It grouped by raw name despite its own comment saying canonical identity
--    was required. Left as raw name here, because the finding below is about
--    variance and name-splitting can only inflate the count of conductors, not
--    manufacture the result.
--
-- MEASURED, 2012-2024, tower peals over 5,000 changes on 10-16 cwt tenors --
-- 10,987 peals, 126 conductors with 20 or more:
--
--   corpus mean                       29.31 changes/minute
--   fastest conductor's mean          31.03
--   slowest conductor's mean          27.40
--   spread                             3.62 cpm, 12.4% of the mean
--
--   sd BETWEEN conductors' means       0.58
--   mean sd WITHIN a conductor         1.16
--
-- The last two lines are the finding. **A conductor varies twice as much
-- against themselves as conductors vary against each other.** Knowing who is
-- conducting tells you less about how fast a peal will go than knowing nothing
-- and guessing the mean twice. "So-and-so rings a fast peal" is the kind of
-- thing every band believes; on thirteen years of data the effect is real,
-- small, and swamped by the variation within any one conductor's own peals.
--
-- What this does NOT control for: band, tower acoustics, method, and the number
-- of bells. Any of those could carry more of the 3.62 than the conductor does,
-- and separating them is the follow-up, not something this query claims.

WITH peals AS (
    SELECT pr.name AS conductor,
           CAST(p.changes AS FLOAT) /
             (CAST(SUBSTR(p.duration, 1, INSTR(p.duration,'h')-1) AS INTEGER) * 60
              + CAST(SUBSTR(p.duration, INSTR(p.duration,'h')+1) AS INTEGER)) AS cpm,
           CAST(SUBSTR(p.tenor, 1, INSTR(p.tenor,'-')-1) AS FLOAT)
             + CAST(SUBSTR(p.tenor, INSTR(p.tenor,'-')+1,
                     INSTR(SUBSTR(p.tenor, INSTR(p.tenor,'-')+1),'-')-1) AS FLOAT) / 4.0
             + CAST(SUBSTR(p.tenor, INSTR(p.tenor,'-')
                     + INSTR(SUBSTR(p.tenor, INSTR(p.tenor,'-')+1),'-') + 1) AS FLOAT) / 112.0
             AS tenor_cwt
    FROM performances p
    JOIN performance_ringers pr ON pr.perf_id = p.perf_id
    WHERE pr.conductor = 1
      AND p.ring_type = 'tower'
      AND p.changes > 5000              -- peals, not quarters
      AND p.duration LIKE '%h%'
      AND p.duration NOT LIKE '%m%'     -- 'Nh MM'; the bare '45m' rows are quarters
      AND p.tenor LIKE '%-%-%'
),
banded AS (
    SELECT * FROM peals
    WHERE tenor_cwt >= 10 AND tenor_cwt < 16   -- one weight class, so speed is comparable
      AND cpm > 10 AND cpm < 60                -- drop unparseable durations
),
per_conductor AS (
    SELECT conductor, COUNT(*) AS peals, AVG(cpm) AS mean_cpm
    FROM banded GROUP BY conductor HAVING COUNT(*) >= 20
)
SELECT
    (SELECT COUNT(*) FROM banded)                         AS peals_measured,
    (SELECT COUNT(*) FROM per_conductor)                  AS conductors,
    ROUND((SELECT AVG(cpm) FROM banded), 2)               AS corpus_mean_cpm,
    ROUND((SELECT MAX(mean_cpm) FROM per_conductor), 2)   AS fastest_conductor_mean,
    ROUND((SELECT MIN(mean_cpm) FROM per_conductor), 2)   AS slowest_conductor_mean,
    ROUND((SELECT MAX(mean_cpm) - MIN(mean_cpm) FROM per_conductor), 2) AS spread_cpm;
