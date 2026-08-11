-- Change Ringing project: Composition Library (CompLib)
-- Source: Composition Library (CompLib), https://complib.org
-- API: https://api.complib.org
--
-- Shape of the source. A CompLib composition is returned as a JSON object
-- containing metadata about the composition, the composer(s), and the methods
-- used within it. We map this into three tables:
--   compositions         -- core composition metadata
--   composition_composers-- composers linked to a composition
--   composition_methods  -- methods used in a composition
--
-- Linkage notes:
-- The API does NOT return CCCBR method IDs (e.g. "m41230"). Instead, it returns
-- the free-text method title (e.g. "Yorkshire Surprise Major") in the methodDefinitions array.
-- Therefore, we store this title as `method_title` and leave a nullable `method_id`
-- column in `composition_methods` for future resolution via exact matching or Gemini adjudication.

CREATE TABLE "compositions" (
  "comp_id"         INTEGER PRIMARY KEY,  -- Source ID from CompLib
  "library"         TEXT,                 -- e.g. "Public"
  "title"           TEXT,                 -- e.g. "2020 2-Spliced Surprise Major"
  "derived_title"   TEXT,
  "opus"            TEXT,
  "method_details"  TEXT,                 -- e.g. "Contains 1376 Yorkshire; 1024 Rutland"
  "date_composed"   TEXT,
  "stage"           INTEGER,
  "length"          INTEGER,
  "calling"         TEXT,
  "method_calling"  TEXT,
  "notes"           TEXT,
  "ingested_at"     TEXT                  -- ISO 8601 timestamp when written locally
);

CREATE TABLE "composition_composers" (
  "comp_id"    INTEGER NOT NULL,
  "position"   INTEGER NOT NULL,
  "role"       TEXT,
  "name"       TEXT,
  PRIMARY KEY ("comp_id", "position")
);

CREATE TABLE "composition_methods" (
  "comp_id"         INTEGER NOT NULL,
  "position"        INTEGER NOT NULL,
  "method_title"    TEXT NOT NULL,
  "method_id"       TEXT,                 -- Nullable, for future resolution against methods.method_id
  PRIMARY KEY ("comp_id", "position")
);

CREATE INDEX "idx_compositions_stage"       ON "compositions" ("stage");
CREATE INDEX "idx_compositions_length"      ON "compositions" ("length");
CREATE INDEX "idx_comp_composers_name"      ON "composition_composers" ("name");
CREATE INDEX "idx_comp_methods_title"       ON "composition_methods" ("method_title");
CREATE INDEX "idx_comp_methods_method_id"   ON "composition_methods" ("method_id");
