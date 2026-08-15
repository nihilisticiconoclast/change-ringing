-- A ringing career, from the bell people stand behind. Mistral Vibe Task 7.
--
-- `performance_ringers.bell` is populated on 1,897,741 rows and nothing in this
-- project has ever read it. Every ringer knows the supposed progression: you
-- learn on the treble, move to the inside bells, and the tenor or the conducting
-- comes later. Nobody has watched it happen to real people at scale.
--
-- This is the DATABASE-ONLY view, which groups raw names. The numbers in
-- docs/ringing_careers.md come from scripts/analyse_ringing_careers.py instead,
-- because canonical identity lives in data/ringer_identity_candidates.csv (a
-- candidate dataset, accuracy unmeasured) and is not in a table. The two
-- disagree in an instructive way -- raw names split one person into fragments,
-- each with a narrower slice of their ringing, which inflates apparent
-- specialists and shortens apparent careers -- so this query is kept because it
-- needs nothing but the database and the gap is worth seeing. The same split
-- between canonical and raw-name is documented in
-- peal_and_quarter_populations.sql.
--
-- MEASURED, 2012-2024, tower performances with a single bell rung (handbell
-- pairs like '1-2' are a different activity and excluded), ringers with 50+
-- appearances spanning 5+ years. The headline is Q2.
--
--   1. APPRENTICESHIP. 72% of the cohort ever conduct a peal; among those who
--      do, the median ringer waits 11 appearances before the first. The mean
--      is far higher (the distribution is long-tailed).
--   2. PROGRESSION. The folk model -- treble to inside to tenor -- is wrong in
--      both directions. Mean normalised bell position (bell / ring size) is
--      ~0.55 in the first tenth of a career and ~0.55 in the last: no upward
--      drift. Yet ringers do not settle either -- the median ringer rings
--      across nearly the whole ring over a career. They move around without
--      moving up. The three-way split (up / down / same) is roughly even.
--   3. ATTRITION. Of ringers first seen in 2013, ~60% have no appearance after
--      2020; for the active 50+ cohort it is ~9%. The 2020 line crosses the
--      COVID discontinuity, so the 2013-2020 cohorts are partly a pandemic
--      effect, and cohorts first seen after 2020 cannot by construction have
--      left before 2020.
--
-- This query answers Q2, the headline. Q1 and Q3 are computed by the script
-- because they need a per-ringer chronological ordering and a cohort table
-- respectively that are cleaner in Python than in a portable SQLite query.
--
-- Ring size per performance: the number of single bells rung. A tower peal on
-- eight has eight ringers each on one bell, so the count is eight and the
-- tenor is bell 8 of 8 -- the normaliser that makes bell position comparable
-- across towers (the tenor of a six is the 6, of a twelve the 12).

WITH ring_size AS (
    SELECT perf_id, COUNT(*) AS n_bells
    FROM performance_ringers
    WHERE bell IS NOT NULL AND TRIM(bell) != '' AND bell NOT LIKE '%-%'
    GROUP BY perf_id
),
appearances AS (
    SELECT TRIM(r.name) AS ringer,
           p.perf_date AS perf_date,
           CAST(r.bell AS REAL) / rs.n_bells AS norm_pos
    FROM performance_ringers r
    JOIN performances p ON p.perf_id = r.perf_id
    JOIN ring_size rs ON rs.perf_id = r.perf_id
    WHERE r.name IS NOT NULL AND TRIM(r.name) != ''
      AND p.perf_date GLOB '[0-9][0-9][0-9][0-9]*'
      AND p.ring_type = 'tower'
      AND r.bell IS NOT NULL AND TRIM(r.bell) != '' AND r.bell NOT LIKE '%-%'
      AND CAST(r.bell AS INTEGER) BETWEEN 1 AND rs.n_bells
),
per_ringer AS (
    SELECT ringer,
           COUNT(*) AS appearances,
           MIN(SUBSTR(perf_date, 1, 4)) AS first_year,
           MAX(SUBSTR(perf_date, 1, 4)) AS last_year
    FROM appearances
    GROUP BY ringer
),
-- rank each appearance within a ringer's chronology to take the first/last tenth
ranked AS (
    SELECT a.ringer,
           a.norm_pos,
           ROW_NUMBER() OVER (PARTITION BY a.ringer ORDER BY a.perf_date) AS rn,
           pr.appearances AS n
    FROM appearances a JOIN per_ringer pr ON pr.ringer = a.ringer
    WHERE pr.appearances >= 50
      AND CAST(pr.last_year AS INTEGER) - CAST(pr.first_year AS INTEGER) >= 5
),
buckets AS (
    SELECT ringer,
           AVG(CASE WHEN rn <= n / 10 THEN norm_pos END) AS early_pos,
           AVG(CASE WHEN rn > n - n / 10 THEN norm_pos END) AS late_pos,
           MAX(norm_pos) - MIN(norm_pos) AS within_range
    FROM ranked
    GROUP BY ringer
)
SELECT COUNT(*) AS cohort_ringers,
       ROUND(AVG(early_pos), 3) AS mean_early_position,
       ROUND(AVG(late_pos), 3) AS mean_late_position,
       ROUND(AVG(late_pos) - AVG(early_pos), 3) AS mean_drift,
       SUM(CASE WHEN late_pos - early_pos > 0.05 THEN 1 ELSE 0 END) AS moved_up,
       SUM(CASE WHEN late_pos - early_pos < -0.05 THEN 1 ELSE 0 END) AS moved_down,
       SUM(CASE WHEN ABS(late_pos - early_pos) <= 0.05 THEN 1 ELSE 0 END) AS stayed,
       ROUND(AVG(within_range), 3) AS mean_within_ringer_range
FROM buckets;
