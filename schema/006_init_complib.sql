-- Change Ringing project: CompLib (Composition Library)
-- Source: Composition Library, https://complib.org
-- API: https://api.complib.org (OpenAPI spec at https://complib.org/complib.api.yml)
--
-- Shape of the source. CompLib is a public composition database. A
-- composition is a calling of one or more methods with calls, and the API
-- returns it as a JSON object with an integer id, a derived title, a stage,
-- composer details, the calling, and a methodDefinitions array. Each
-- methodDefinition carries a free-text method title (e.g. "Rutland Surprise
-- Major") and the place notation as published by the composer -- not a CCCBR
-- Methods Library identifier.
--
-- Two tables model this, mirroring the methods/method_performances split in
-- schema/003:
--   compositions         -- one row per CompLib composition (id is CompLib's)
--   composition_methods   -- one row per methodDefinition, ordered, with the
--                           free-text title and place notation
--
-- The linkage that matters. A composition is *of* a method, and the brief
-- asked whether CompLib carries a method identifier that matches the CCCBR
-- library. It does not carry one on the composition search payload. The
-- /composition/{id}/rows endpoint does return a `methodid` for single-method
-- (non-spliced) compositions, and empirically that integer corresponds to the
-- CCCBR method_id by the rule method_id = 'm' || methodid (11 of 12 sampled
-- resolved, the 12th being a constructed spliced title with no single CCCBR
-- method). That is recorded here as complib_method_id, and method_id is
-- populated only by that exact identifier lookup -- never by fuzzy title
-- matching, which is Gemini's and Claude Code's to adjudicate. method_id is a
-- soft reference to methods.method_id, not a declared foreign key, for the
-- same reason dove_tower_id is (see schema/002): CompLib may reference a
-- method newer than our snapshot, and a hard FK would reject those rows.
--
-- Fetching methodid costs one extra request per composition (the /rows
-- endpoint), so the loader fetches it only when --fetch-method-ids is given;
-- without it the column stays NULL and the free-text title is the only
-- linkage. Either way, re-runs converge: writes are INSERT OR REPLACE on
-- CompLib's composition id, and child rows are cleared before reinsert.

CREATE TABLE "compositions" (
  "composition_id"        INTEGER PRIMARY KEY,  -- CompLib's integer id
  "library"               TEXT,                 -- "Public" | "Private" | ...
  "derived_title"         TEXT,                 -- CompLib's rendered title incl. composer
  "title"                 TEXT,                 -- composer's short title
  "opus"                  TEXT,
  "stage"                 INTEGER,              -- number of bells
  "length"                INTEGER,              -- changes in the composition
  "date_composed"         TEXT,                  -- ISO date where supplied
  "extents"               INTEGER,
  "backstroke_start"      INTEGER,              -- boolean as 0/1
  "call_default_specifier" TEXT,                 -- e.g. "near"
  "calling"               TEXT,                  -- the call string, e.g. "6(-W -H ...)"
  "method_calling"        TEXT,                  -- per-lead calling expansion
  "method_details"        TEXT,                  -- human-readable method summary
  "partheads"             TEXT,                  -- JSON array, joined with '|'
  "coursehead_masks"      TEXT,                  -- JSON array, joined with '|'
  "notes"                 TEXT,
  "ingested_at"           TEXT                   -- ISO 8601 timestamp when written locally
);

CREATE TABLE "composition_methods" (
  "composition_id"    INTEGER NOT NULL,
  "position"          INTEGER NOT NULL,        -- 0-indexed order in methodDefinitions
  "name"              TEXT,                     -- short name, e.g. "Rutland" (may be "")
  "method_title"      TEXT,                     -- free-text title, e.g. "Rutland Surprise Major"
  "mnemonic"          TEXT,                     -- single-letter calling code, e.g. "R"
  "place_notation"    TEXT,                     -- as published by the composer
  "method_place_notation" TEXT,                 -- canonical method place notation
  "row_stage"         INTEGER,
  "method_stage"      INTEGER,
  "complib_method_id" INTEGER,                  -- CompLib's own method id (from /rows), if fetched
  "method_id"          TEXT,                    -- soft reference to methods.method_id ('m'+int)
  PRIMARY KEY ("composition_id", "position")
);

CREATE INDEX "idx_compositions_stage"        ON "compositions" ("stage");
CREATE INDEX "idx_compositions_library"       ON "compositions" ("library");
CREATE INDEX "idx_comp_methods_method_id"     ON "composition_methods" ("method_id");
CREATE INDEX "idx_comp_methods_complib_mid"   ON "composition_methods" ("complib_method_id");
CREATE INDEX "idx_comp_methods_composition"   ON "composition_methods" ("composition_id");

-- Compositions joined to the CCCBR methods they name, where the identifier
-- resolved. Inner join by design: this view is the linked subset, so spliced
-- compositions whose method_id is unresolved are excluded rather than carried
-- with NULLs. Query composition_methods directly for the unfiltered record.
CREATE VIEW "v_composition_methods" AS
SELECT
  c."composition_id",
  c."derived_title",
  c."stage",
  c."length",
  cm."position",
  cm."method_title",
  cm."mnemonic",
  cm."place_notation",
  cm."method_id",
  m."name"        AS "method_name",
  m."classification" AS "method_classification"
FROM "compositions" c
JOIN "composition_methods" cm ON cm."composition_id" = c."composition_id"
LEFT JOIN "methods" m ON m."method_id" = cm."method_id";
