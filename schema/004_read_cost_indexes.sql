-- Change Ringing project: indexes added to control row-read cost
--
-- Turso meters rows read, not query time, and the two are not proportional.
-- This migration exists because the database billed 591 million row reads in a
-- single day while holding roughly 130,000 rows. Two statements caused nearly
-- all of it, and both looked ordinary.
--
-- 1. v_first_tower_peals joins methods to method_performances on
--    (method_id, event_type). With separate single-column indexes the planner
--    drove the inner lookup off event_type, whose 'firstTowerbellPeal' range
--    holds 15,813 rows, and walked that range once per method:
--    25,055 x 15,813 = 396 million rows read for one SELECT COUNT(*).
--    The composite index below lets it seek on both columns at once.
--
-- 2. The location adjudication matched on (building, town, county) with
--    COALESCE on both sides, which no index can serve. That is fixed in
--    scripts/apply_location_adjudication.py by joining on a single computed
--    key rather than by adding an index here -- the columns are only ever
--    matched as a complete triple, so a persistent three-column index would
--    cost write time on every ingest for one batch job's benefit.
--
-- The lesson worth keeping: batching a slow loop into one statement fixes
-- wall-clock time and can leave read cost completely unchanged. The slow and
-- fast versions of the adjudication write read exactly the same 139 million
-- rows. On a metered database, latency and read cost are separate problems,
-- and only one of them announces itself.

CREATE INDEX IF NOT EXISTS "idx_method_perfs_method_event"
  ON "method_performances" ("method_id", "event_type");

-- Same shape of risk on the BellBoard side: performances are routinely
-- filtered by tower and by date together (an atlas query, a tower's history),
-- and dove_tower_id alone leaves the date filter to a scan.
CREATE INDEX IF NOT EXISTS "idx_perf_tower_date"
  ON "performances" ("dove_tower_id", "perf_date");

-- Ringer lookups join name to performance. idx_ringer_name alone means the
-- per-performance step is a scan once a name is common.
CREATE INDEX IF NOT EXISTS "idx_ringer_name_perf"
  ON "performance_ringers" ("name", "perf_id");
