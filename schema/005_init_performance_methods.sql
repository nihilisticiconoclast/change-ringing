-- Performance -> Method linkage
--
-- The gap this fills. `performances.method` is free text: 293,471 rows, of which
-- 61.0% match a `methods.title` exactly and the rest do not. Until now there was
-- no link at all between the 293,471 performances and the 25,066-method library,
-- so no question could be asked that needed both -- which methods are actually
-- rung, how often a method is rung relative to its age, whether Surprise Major
-- dominates because there are more of them or because they are rung more.
--
-- Why a junction table rather than a `method_id` column on `performances`.
-- 15,497 performances name several methods at once: "Spliced Surprise Major
-- (8m)" is eight methods in one performance, and the constituents are listed in
-- `details` ("336 each of Tarrant, Kent, Oxford and Guilsfield"). A single
-- foreign key cannot hold that, and picking one of the eight would be worse than
-- holding none.
--
-- Why the unresolved rows get a table of their own. A plausible-but-wrong
-- identifier silently corrupts every downstream use; a missing one is visibly
-- unresolved and invites another pass. So nothing is guessed: a link is written
-- only when a check passes, and every failure is recorded with the numbers that
-- made it fail. `SELECT reason, COUNT(*) FROM performance_method_unresolved
-- GROUP BY 1` is the honest coverage statement for this table.

CREATE TABLE IF NOT EXISTS "performance_methods" (
  "perf_id"     INTEGER NOT NULL,
  "method_id"   TEXT    NOT NULL,   -- methods.method_id, e.g. 'm11349'
  "ord"         INTEGER NOT NULL,   -- position within this performance, 0-based
  "match_kind"  TEXT    NOT NULL,   -- exact_title | normalised_title | spliced_details
  "confidence"  TEXT    NOT NULL,   -- high | medium | low
  "matched_on"  TEXT,               -- the text that produced the match
  "resolved_at" TEXT    NOT NULL DEFAULT (datetime('now')),
  PRIMARY KEY ("perf_id", "method_id")
);

-- Every performance whose method text could NOT be linked, and why. Populated in
-- the same pass, so the two tables always agree and neither can be read without
-- the other being available.
CREATE TABLE IF NOT EXISTS "performance_method_unresolved" (
  "perf_id"       INTEGER NOT NULL PRIMARY KEY,
  "method_text"   TEXT    NOT NULL,
  "reason"        TEXT    NOT NULL,   -- see the resolver for the full list
  "expected_n"    INTEGER,            -- methods the text claims, e.g. 8 for "(8m)"
  "found_n"       INTEGER,            -- methods actually identified in `details`
  "candidates"    TEXT,               -- what was found, so a later pass can start here
  "resolved_at"   TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS "idx_pm_method"     ON "performance_methods" ("method_id");
CREATE INDEX IF NOT EXISTS "idx_pm_confidence" ON "performance_methods" ("confidence");
CREATE INDEX IF NOT EXISTS "idx_pmu_reason"    ON "performance_method_unresolved" ("reason");

-- One row per (performance, method) with the columns a question usually needs,
-- so the three-way join does not have to be rewritten each time.
--
-- Deliberately restricted to confidence <> 'low'. The low band exists and is
-- populated; it is excluded here so that the convenient view is the trustworthy
-- one and anyone who wants the doubtful rows has to ask for them by name.
DROP VIEW IF EXISTS "v_performance_methods";
CREATE VIEW "v_performance_methods" AS
SELECT
  pm."perf_id",
  pm."method_id",
  pm."confidence",
  pm."match_kind",
  p."perf_date",
  p."changes",
  p."ring_type",
  p."dove_tower_id",
  m."title"           AS method_title,
  m."name"            AS method_name,
  m."stage",
  m."classification",
  m."lead_head_code"
FROM "performance_methods" pm
JOIN "performances" p USING ("perf_id")
JOIN "methods"      m USING ("method_id")
WHERE pm."confidence" <> 'low';
