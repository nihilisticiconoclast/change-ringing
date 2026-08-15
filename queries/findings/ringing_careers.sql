-- A ringing career, from the bell people stand behind. Roadmap item 7.
--
-- performance_ringers.bell is populated on 1,969,949 rows (1,786,411 single
-- bells, 111,330 handbell pairs or runs, 72,208 NULL) and nothing in this
-- project had ever read it. This traces three things about a ringer's arc.
--
-- The progression every ringer knows -- treble, inside bells, tenor, then
-- conducting -- has not been watched at scale. The cohort below is ringers
-- with 50 or more tower-bell appearances spanning five or more years, the same
-- threshold the populations query uses. Raw names here, canonical identities
-- in the doc: see the caveat at the foot of this header.
--
-- Each row is one (metric, value) pair, so a single run prints every number
-- the finding rests on without a wide table whose columns mean different
-- things on different rows. Fractional results are scaled to integers because
-- the UNION returns one numeric column: the metric name says by how much
-- (x1000 = thousandths, x10000 = ten-thousandths of a bell position).
--
-- === Q1. How long is the apprenticeship? ===================================
-- Appearances before a first conducted peal. Of the cohort, the share who ever
-- conduct, and the distribution of how many appearances came first.
--
--     cohort (raw names)                 6,255
--     of whom ever conduct               4,643   (74.2%)
--     never conduct                      1,614
--     ringers in the distribution        8,346   (see note)
--     median appearances before first        8
--     mean                                  23
--     p25 3  p75 23  p90 55  p99 222  max 1,613
--
-- The distribution counts every cohort ringer who has ever conducted. 8,346 is
-- larger than the 4,643 above because a ringer enters the cohort on their
-- tower-bell appearances but may have conducted a handbell performance, which
-- sets their first-conducted date; their tower-bell appearances before it are
-- still counted. The median ringer rings eight performances before the first
-- one they conduct. The long right tail is real and matters -- a tenth pass
-- fifty-five appearances before conducting -- but the centre is early.
--
-- === Q2. Is the progression real, or do people find a bell and stay? =======
-- The folk model says ringers move toward the tenor as they gain experience.
-- This says otherwise. Bell position is normalised as bell_number / stage (the
-- highest bell rung in that performance), so it is comparable across towers:
-- the treble of a six is ~0.17, of a twelve ~0.08; the tenor is 1.0.
--
--     most-used bell is >= 50% of apps     521 / 6,255   (8.3%)
--     most-used bell is >= 70% of apps     107 / 6,255   (1.7%)
--     mean share of a ringer's most-used bell            0.316
--     drift, first-10 to last-10 apps (bell position)    -0.0032
--     moved toward the tenor                  3,023   (48.3%)
--     moved toward the treble                 3,192   (51.0%)
--     unchanged                                  40
--
-- Almost nobody settles on one bell. The drift from a ringer's first ten
-- appearances to their last ten is a wash: -0.0032 on a 0-1 scale, with as many
-- ringers drifting toward the treble as toward the tenor. If there were a
-- career-long march to the tenor this would be clearly positive; it is not.
-- Ringers range across the bells throughout.
--
-- === Q3. What does leaving look like? ======================================
-- Of ringers first seen in year Y, the share with no appearance after year Y+N.
-- An absence is an absence: it is not a death or a resignation. The corpus ends
-- in 2024 and cannot see someone who moved tower, changed name, or rings at a
-- tower that does not report, so this is a cohort attrition rate, never a
-- statement about an individual.
--
--     first seen   cohort   no app after +3y   no app after +5y
--         2012     18,607         30.0%              36.1%
--         2013      5,409         52.2%              60.6%
--         2014      3,855         57.4%              67.6%
--         2015      3,246         60.6%              67.9%
--         2016      2,972         63.9%              67.9%
--         2017      2,706         62.7%              73.6%
--         2018      6,777         67.2%              84.8%
--         2019      2,926         74.5%             100.0%
--
-- 2012 is large because the backfill starts then, so a one-year cohort from
-- 2012 partly contains ringers whose earlier appearances are out of frame and
-- therefore count as their first. Read 2013 onward. The +5y column for 2019 is
-- 100% by construction -- five years on from 2019 is 2024, the last year in the
-- corpus, so every 2019 ringer's last appearance is at or before it. The +3y
-- column is the honest one for recent cohorts.
--
-- The signal: roughly six in ten ringers first recorded in 2013-2017 have no
-- reported appearance five years later. Whether that is genuine attrition or
-- reporting drift cannot be told from this data alone; see the doc.
--
-- === CAVEAT ON IDENTITY ====================================================
-- These figures group raw performance_ringers.name. The canonical identity
-- resolution (data/ringer_identity_candidates.csv, 55,326 entities, accuracy
-- unmeasured) is a CSV, not a table, so it cannot be joined by a query that
-- must also prepare against an empty schema in CI. The doc,
-- docs/ringing_careers.md, gives the canonical-id figures and the gap between
-- the two: 99.8% of ringer rows resolve, so the two agree closely. Grouping
-- raw names can only fragment a ringer and so can only INFLATE the cohort and
-- UNDERSTATE per-ringer concentration -- it cannot manufacture the finding
-- that ringers do not settle on one bell, which is structural.
--
-- Handbell pairs ('1-2', runs up to '1-2-3-4-5-6-7-8-9-10-11-12-13-14') are a
-- different activity and are excluded throughout, as are rows with no bell
-- number. NULL-bell rows are excluded from bell questions but a ringer is
-- counted in the cohort on their tower-bell appearances, so a ringer who also
-- rings handbells is not lost.

WITH staged AS (
    SELECT r.perf_id,
           r.name,
           r.conductor,
           p.perf_date,
           CASE WHEN r.bell GLOB '[0-9]*' AND instr(r.bell, '-') = 0
                THEN CAST(r.bell AS INTEGER) END AS bell_num
    FROM performance_ringers r
    JOIN performances p ON p.perf_id = r.perf_id
    WHERE r.name IS NOT NULL AND TRIM(r.name) != ''
),
coh AS (
    SELECT name
    FROM staged
    WHERE bell_num IS NOT NULL
    GROUP BY name
    HAVING COUNT(*) >= 50
       AND CAST(substr(MAX(perf_date), 1, 4) AS INT)
         - CAST(substr(MIN(perf_date), 1, 4) AS INT) >= 5
),
-- The highest bell rung in a performance, as a proxy for the number of bells.
-- bell_num / stage is then a tower-independent position: treble ~0.08-0.17,
-- tenor 1.0. Computed once and reused by every Q2 metric.
stage AS (
    SELECT perf_id, MAX(bell_num) AS stage
    FROM staged WHERE bell_num IS NOT NULL GROUP BY perf_id
),
-- Each cohort ringer's first-10 and last-10 appearances, with bell position.
-- ROW_NUMBER ordered ascending and descending over the same ringer's rows.
ranked AS (
    SELECT s.name,
           s.bell_num,
           CAST(s.bell_num AS REAL) / st.stage AS bell_pos,
           ROW_NUMBER() OVER (PARTITION BY s.name ORDER BY s.perf_date, s.perf_id)      AS rn_first,
           ROW_NUMBER() OVER (PARTITION BY s.name ORDER BY s.perf_date DESC, s.perf_id DESC) AS rn_last
    FROM staged s
    JOIN coh  c  ON c.name  = s.name
    JOIN stage st ON st.perf_id = s.perf_id
    WHERE s.bell_num IS NOT NULL
),
early AS (SELECT name, AVG(bell_pos) AS bp FROM ranked WHERE rn_first <= 10 GROUP BY name),
late  AS (SELECT name, AVG(bell_pos) AS bp FROM ranked WHERE rn_last  <= 10 GROUP BY name),
drift AS (SELECT e.bp AS early_bp, l.bp AS late_bp FROM early e JOIN late l ON l.name = e.name),
-- Apprenticeship: appearances dated strictly before a ringer's first conducted one.
first_cond AS (
    SELECT name, MIN(perf_date) AS fc
    FROM staged WHERE conductor = 1 GROUP BY name
),
apps_before AS (
    SELECT s.name, COUNT(*) AS n
    FROM staged s
    JOIN first_cond fc ON fc.name = s.name
    WHERE s.perf_date < fc.fc
    GROUP BY s.name
),
apps_before_pct AS (
    SELECT n, NTILE(100) OVER (ORDER BY n) AS p FROM apps_before
),
-- Q2 modal-bell concentration: share of a ringer's apps on their most-used bell.
per_bell AS (
    SELECT s.name, s.bell_num, COUNT(*) AS n
    FROM staged s JOIN coh c ON c.name = s.name
    WHERE s.bell_num IS NOT NULL
    GROUP BY s.name, s.bell_num
),
modal AS (
    SELECT name, 1.0 * MAX(n) / SUM(n) AS modal_share
    FROM per_bell GROUP BY name
)

SELECT 'Q1 cohort size'                       AS metric, COUNT(*)            AS value FROM coh
UNION ALL SELECT 'Q1 ever conducted',          COUNT(*) FROM coh WHERE name IN (SELECT name FROM first_cond)
UNION ALL SELECT 'Q1 never conducted',
    (SELECT COUNT(*) FROM coh) - (SELECT COUNT(*) FROM coh WHERE name IN (SELECT name FROM first_cond))
UNION ALL SELECT 'Q1 min apps before first',   MIN(n) FROM apps_before
UNION ALL SELECT 'Q1 p25 apps before first',   MAX(n) FROM apps_before_pct WHERE p <= 25
UNION ALL SELECT 'Q1 p50 apps before first',   MAX(n) FROM apps_before_pct WHERE p <= 50
UNION ALL SELECT 'Q1 p75 apps before first',   MAX(n) FROM apps_before_pct WHERE p <= 75
UNION ALL SELECT 'Q1 p90 apps before first',   MAX(n) FROM apps_before_pct WHERE p <= 90
UNION ALL SELECT 'Q1 p99 apps before first',   MAX(n) FROM apps_before_pct WHERE p <= 99
UNION ALL SELECT 'Q1 mean apps before first',  CAST(AVG(n) AS INT) FROM apps_before
UNION ALL SELECT 'Q2 modal bell >=50% apps',   SUM(CASE WHEN modal_share >= 0.5 THEN 1 ELSE 0 END) FROM modal
UNION ALL SELECT 'Q2 modal bell >=70% apps',   SUM(CASE WHEN modal_share >= 0.7 THEN 1 ELSE 0 END) FROM modal
UNION ALL SELECT 'Q2 mean modal share (x1000)',CAST(AVG(modal_share) * 1000 AS INT) FROM modal
UNION ALL SELECT 'Q2 drift first10-last10 (x10000)', CAST(AVG(late_bp - early_bp) * 10000 AS INT) FROM drift
UNION ALL SELECT 'Q2 moved toward tenor',      SUM(CASE WHEN late_bp >  early_bp THEN 1 ELSE 0 END) FROM drift
UNION ALL SELECT 'Q2 moved toward treble',     SUM(CASE WHEN late_bp <  early_bp THEN 1 ELSE 0 END) FROM drift
UNION ALL SELECT 'Q2 unchanged',                SUM(CASE WHEN late_bp =  early_bp THEN 1 ELSE 0 END) FROM drift
UNION ALL SELECT 'Q3 ' || first_year || ' cohort',
    COUNT(*)
FROM (SELECT f.name, f.first_year
      FROM (SELECT name, CAST(substr(MIN(perf_date),1,4) AS INT) AS first_year
            FROM staged WHERE bell_num IS NOT NULL GROUP BY name) f
      JOIN (SELECT name, CAST(substr(MAX(perf_date),1,4) AS INT) AS max_year
            FROM staged WHERE bell_num IS NOT NULL GROUP BY name) m ON m.name = f.name
      WHERE f.first_year BETWEEN 2012 AND 2019)
GROUP BY first_year
UNION ALL SELECT 'Q3 ' || first_year || ' no app after +3y',
    SUM(CASE WHEN max_year <= first_year + 3 THEN 1 ELSE 0 END)
FROM (SELECT f.name, f.first_year, m.max_year
      FROM (SELECT name, CAST(substr(MIN(perf_date),1,4) AS INT) AS first_year
            FROM staged WHERE bell_num IS NOT NULL GROUP BY name) f
      JOIN (SELECT name, CAST(substr(MAX(perf_date),1,4) AS INT) AS max_year
            FROM staged WHERE bell_num IS NOT NULL GROUP BY name) m ON m.name = f.name
      WHERE f.first_year BETWEEN 2012 AND 2019)
GROUP BY first_year
UNION ALL SELECT 'Q3 ' || first_year || ' no app after +5y',
    SUM(CASE WHEN max_year <= first_year + 5 THEN 1 ELSE 0 END)
FROM (SELECT f.name, f.first_year, m.max_year
      FROM (SELECT name, CAST(substr(MIN(perf_date),1,4) AS INT) AS first_year
            FROM staged WHERE bell_num IS NOT NULL GROUP BY name) f
      JOIN (SELECT name, CAST(substr(MAX(perf_date),1,4) AS INT) AS max_year
            FROM staged WHERE bell_num IS NOT NULL GROUP BY name) m ON m.name = f.name
      WHERE f.first_year BETWEEN 2012 AND 2019)
GROUP BY first_year
ORDER BY metric;
