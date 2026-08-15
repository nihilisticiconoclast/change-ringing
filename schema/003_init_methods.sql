-- Change Ringing project: CCCBR Methods Library
-- Source: Central Council of Church Bell Ringers (CCCBR), https://methods.cccbr.org.uk
-- XML Specification: Method XML 1.0 (http://www.cccbr.org.uk/methods/schemas/2007/05/methods)
--
-- Shape of the source. The CCCBR Methods Library publishes all recognized
-- methods in a single XML collection. Methods are grouped into <methodSet>
-- elements that share common structural properties (stage, classification,
-- lengthOfLead, numberOfHunts, huntbellPath), and each <method> contains
-- an identifier, name, title, place notation, symmetry, lead head, and an
-- optional <performances> block.
--
-- Two tables model this corpus:
--   methods              -- the core method definition (25,000+ methods)
--   method_performances  -- historical first-performance events (peals, quarter peals,
--                           extents across towerbell, handbell, keyboard, and mixed styles)
--
-- Classification. <classification> is optional in the source; sets without it
-- (mostly principles, e.g. Plain Bob Minimus or Grandsire) carry NULL. Boolean
-- modifier flags (plain, little, differential, trebleDodging) are extracted into
-- dedicated columns (cls_plain, cls_little, cls_differential, cls_treble_dodging).
--
-- First-performance locations. Each performance event records free-text location
-- details (<building>, <town>, <county>, etc.) with NO foreign key or tower ID.
-- The dove_tower_id column is a nullable soft reference populated by the downstream
-- entity-resolution process (see docs/tasks/gemini-location-resolution.md).

CREATE TABLE "methods" (
  "method_id"               TEXT PRIMARY KEY,  -- e.g. "m41230"
  "title"                   TEXT NOT NULL,     -- full rendered title, e.g. "Bristol Surprise Major"
  "name"                    TEXT,              -- method name without stage/class, e.g. "Bristol"
  "stage"                   INTEGER NOT NULL,  -- number of bells: 4=Minimus, 6=Minor, 8=Major, etc.
  "classification"          TEXT,              -- "Surprise" | "Bob" | "Delight" | "Alliance" | "Treble Place" | "Treble Bob" | "Hybrid" | "Place" | NULL
  "cls_plain"               INTEGER NOT NULL DEFAULT 0,
  "cls_little"              INTEGER NOT NULL DEFAULT 0,
  "cls_differential"        INTEGER NOT NULL DEFAULT 0,
  "cls_treble_dodging"      INTEGER NOT NULL DEFAULT 0,
  "length_of_lead"          INTEGER,
  "number_of_hunts"         INTEGER,
  "huntbell_path"           TEXT,
  "notation"                TEXT,              -- place notation, e.g. "-58-14.58-58.36.14-14.58-14-18,18"
  "symmetry"                TEXT,              -- e.g. "palindromic double rotational"
  "lead_head"               TEXT,              -- row order at lead head, e.g. "14263857"
  "lead_head_code"          TEXT,              -- e.g. "a", "b", "c"
  "fch_groups"              TEXT,              -- false course head groups, e.g. "C", "a", "D"
  "rw_ref"                  TEXT,              -- Ringing World reference, e.g. "1992/874"
  "extension_construction"  TEXT,              -- e.g. "EP1-1"
  "notes"                   TEXT,
  "ingested_at"             TEXT               -- ISO 8601 timestamp when written locally
);

CREATE TABLE "method_performances" (
  "method_id"      TEXT NOT NULL,
  "position"       INTEGER NOT NULL,        -- 0-indexed position within the method's <performances> list
  "event_type"     TEXT NOT NULL,           -- e.g. "firstTowerbellPeal", "firstInclusionInTowerbellPeal", "firstHandbellPeal"
  "perf_date"      TEXT,                    -- YYYY-MM-DD
  "society"        TEXT,                    -- ringing guild / society, e.g. "Ancient Society of College Youths"
  "building"       TEXT,                    -- church / building dedication, e.g. "St Andrew"
  "town"           TEXT,                    -- town or parish, e.g. "Lismore"
  "county"         TEXT,                    -- historic/ceremonial county or state, e.g. "New South Wales"
  "address"        TEXT,
  "region"         TEXT,
  "country"        TEXT,
  "room"           TEXT,
  "dove_tower_id"  INTEGER,                 -- soft reference to dove.TowerID / towers.TowerID
  PRIMARY KEY ("method_id", "position")
);

CREATE INDEX "idx_methods_title"          ON "methods" ("title");
CREATE INDEX "idx_methods_classification" ON "methods" ("classification");
CREATE INDEX "idx_methods_stage"          ON "methods" ("stage");
CREATE INDEX "idx_methods_name"           ON "methods" ("name");
CREATE INDEX "idx_method_perfs_method"    ON "method_performances" ("method_id");
CREATE INDEX "idx_method_perfs_event"     ON "method_performances" ("event_type");
CREATE INDEX "idx_method_perfs_tower"     ON "method_performances" ("dove_tower_id");

-- Canonical first-towerbell-peal view: methods paired with their inaugural towerbell peal
-- and linked Dove tower metadata when resolved.
CREATE VIEW "v_first_tower_peals" AS
SELECT
  m."method_id",
  m."title",
  m."stage",
  m."classification",
  mp."perf_date",
  mp."society",
  mp."building",
  mp."town",
  mp."county",
  mp."dove_tower_id",
  d."Place"     AS "dove_place",
  d."Dedicn"    AS "dove_dedication",
  d."County"    AS "dove_county"
FROM "methods" m
LEFT JOIN "method_performances" mp
  ON mp."method_id" = m."method_id"
  AND mp."event_type" = 'firstTowerbellPeal'
LEFT JOIN "v_towers_unique" d
  ON d."TowerID" = mp."dove_tower_id";
-- v_towers_unique (schema/007), not "dove", per decision 001. Because this is a
-- LEFT JOIN driven off "methods" and filtered to one event type, the effect is
-- not the one decision 001 predicted for method_performances as a whole -- see
-- the measured correction in that document. Measured 2026-08-15: 25,351 rows
-- -> 25,340, eleven duplicates removed, and 38 rows that previously carried a
-- NULL tower now carry the tower they always referenced.
