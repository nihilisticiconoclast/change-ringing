-- 008_init_semantic_views.sql -- the definitions, as SQL (R-53)
--
-- GENERATED from scripts/semantics.py by scripts/build_semantic_views.py.
-- Do NOT edit by hand. The point of this schema is that the rule lives in one
-- place; a hand-edit here recreates exactly the divergence it exists to end.
-- `scripts/build_semantic_views.py --check` fails the build if you do.
--
-- Recorded queries under queries/ cannot import Python, so they read these views
-- and get is_peal, is_quarter and length_class without restating a threshold.
-- tests/test_semantics.py asserts the view and the Python predicates agree on
-- every row of the corpus.
--
-- In force: a peal is 5000 changes on 7 or more bells and
-- 5040 below that; a quarter is 1250.
--
-- All three derived columns are NULL where the answer is genuinely unknown --
-- 22,623 performances, 7.7% -- and NOT false. 21,788 have no length at all; 835
-- sit in [5000, 5040) with no resolved stage, where the answer
-- depends on a stage nobody knows. Treating those as false is the live bug this
-- replaces: SUM(changes >= 5000) drops them from a numerator while COUNT(*)
-- keeps them in the denominator, worth 1.43 points on the headline peal share.
-- See docs/definitions_measured.md.

DROP VIEW IF EXISTS "v_performance_facts";
DROP VIEW IF EXISTS "v_performance_length";

-- Layer one: the peal rule, computed once.
CREATE VIEW "v_performance_length" AS
SELECT
    p.perf_id,
    p.perf_date,
    p.changes,
    m.stage,
    CASE WHEN p.changes IS NULL THEN NULL WHEN p.changes >= 5040 THEN 1 WHEN p.changes < 5000 THEN 0 WHEN m.stage IS NULL THEN NULL ELSE (m.stage >= 7) END AS is_peal
FROM performances p
LEFT JOIN performance_methods pm ON pm.perf_id = p.perf_id AND pm.ord = 0
LEFT JOIN methods m ON m.method_id = pm.method_id;

-- Layer two: everything that derives from it. Split in two because inlining the
-- peal CASE into the quarter and class expressions expands it to six nested
-- copies -- correct, and unreviewable.
CREATE VIEW "v_performance_facts" AS
SELECT
    l.perf_id,
    l.perf_date,
    l.changes,
    l.stage,
    l.is_peal,
    CASE WHEN l.is_peal IS NULL THEN NULL WHEN l.is_peal = 1 THEN 0 ELSE (l.changes >= 1250) END AS is_quarter,
    CASE WHEN l.is_peal IS NULL THEN NULL WHEN l.is_peal = 1 THEN 'peal' WHEN l.changes >= 1250 THEN 'quarter' ELSE 'short' END AS length_class,
    p.ring_type,
    (p.ring_type = 'tower') AS is_tower,
    p.dove_tower_id,
    p.dove_ring_id,
    p.composer
FROM v_performance_length l
JOIN performances p ON p.perf_id = l.perf_id;
