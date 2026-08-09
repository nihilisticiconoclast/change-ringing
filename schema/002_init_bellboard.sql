-- Change Ringing project: BellBoard performance data
-- Source: BellBoard (The Ringing World), https://bb.ringingworld.co.uk
-- API: https://bb.ringingworld.co.uk/help/api.php
--
-- Shape of the source. A BellBoard performance is one XML <performance>
-- record: a ring at a place on a date, with an ordered list of ringers and
-- zero or more footnotes and flags. Four tables rather than one, because
-- ringers, footnotes and flags are all genuinely one-to-many (footnotes run
-- to 11 on a single performance in a 500-record sample) and flattening them
-- would either lose data or force repeated parsing of delimited text.
--
-- The tower link is the important part. BellBoard supplies dove-tower-id and
-- dove-ring-id attributes directly on <place>, so linking a performance to a
-- Dove tower is a join on an integer, not a fuzzy name match. Measured on a
-- 500-performance sample: 88.8% of performances carry dove-tower-id, and
-- 99.5% of those IDs resolve against the Dove snapshot in this database.
-- Nearly all of the remainder are handbell performances rung in private
-- houses ("33 St Malo Road", "Laurel House"), which have no Dove tower
-- because they are not towers -- they are not a resolution failure, and
-- should not be forced into one.
--
-- dove_tower_id is deliberately NOT a declared foreign key. BellBoard tracks
-- Dove's live data while this database holds a periodic snapshot, so BB can
-- legitimately reference a tower newer than our copy (2 of 391 distinct IDs
-- in the sample). A hard FK would reject those rows; a soft reference keeps
-- them and lets the next Dove refresh resolve them.

CREATE TABLE "performances" (
  "perf_id"        INTEGER PRIMARY KEY,  -- numeric part of BellBoard's id="P1208892"
  "bb_id"          TEXT NOT NULL,        -- the full "P1208892" form, as published
  "association"    TEXT,
  "place"          TEXT,                 -- <place-name type="place">
  "dedication"     TEXT,                 -- <place-name type="dedication">
  "county"         TEXT,                 -- <place-name type="county">
  "towerbase-id"   INTEGER,
  "dove_tower_id"  INTEGER,              -- soft reference to dove.TowerID / towers.TowerID
  "dove_ring_id"   INTEGER,              -- soft reference to dove.RingID
  "ring_type"      TEXT,                 -- "tower" | "hand"
  "tenor"          TEXT,                 -- e.g. "12-2-13"; hundredweight-qtr-lb, not numeric
  "portable"       TEXT,
  "dumb_bells"     TEXT,
  "perf_date"      TEXT,                 -- YYYY-MM-DD ("date" is awkward to quote everywhere)
  "duration"       TEXT,                 -- e.g. "5h 21"
  "changes"        INTEGER,              -- absent on ~6% of records
  "method"         TEXT,
  "title"          TEXT,                 -- full rendered title, e.g. "1260 Plain Bob Triples"
  "details"        TEXT,
  "composer"       TEXT,
  "composition"    TEXT,
  "bb_timestamp"   TEXT,                 -- BellBoard's own last-modified, ISO 8601
  "ingested_at"    TEXT                  -- when this row was last written locally
);

-- Ordered: position preserves the order ringers appear in the record, which
-- is the ringing order. bell is TEXT, not INTEGER -- handbell records use
-- "1-2" for a pair, and one sample row carries "1-2-3-4-5-6-7-8-9-10".
CREATE TABLE "performance_ringers" (
  "perf_id"    INTEGER NOT NULL,
  "position"   INTEGER NOT NULL,
  "bell"       TEXT,
  "name"       TEXT,
  "conductor"  INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY ("perf_id", "position")
);

CREATE TABLE "performance_footnotes" (
  "perf_id"   INTEGER NOT NULL,
  "position"  INTEGER NOT NULL,
  "footnote"  TEXT,
  PRIMARY KEY ("perf_id", "position")
);

-- <flag type="..." bell="..."> marks simulator/virtual-belfry rings and
-- similar. Worth keeping separate: any analysis of "real" ringing needs to
-- be able to exclude Abel, Wheatley and Virtual Belfry performances.
CREATE TABLE "performance_flags" (
  "perf_id"    INTEGER NOT NULL,
  "position"   INTEGER NOT NULL,
  "flag_type"  TEXT,
  "bell"       TEXT,
  "flag_text"  TEXT,
  PRIMARY KEY ("perf_id", "position")
);

CREATE INDEX "idx_perf_dove_tower" ON "performances" ("dove_tower_id");
CREATE INDEX "idx_perf_date"       ON "performances" ("perf_date");
CREATE INDEX "idx_perf_method"     ON "performances" ("method");
CREATE INDEX "idx_perf_timestamp"  ON "performances" ("bb_timestamp");
CREATE INDEX "idx_ringer_name"     ON "performance_ringers" ("name");
CREATE INDEX "idx_ringer_perf"     ON "performance_ringers" ("perf_id");

-- Performances joined to their Dove tower. Inner join by design: this view is
-- the tower-linked subset, and handbell-in-a-front-room records are excluded
-- rather than carried with NULL towers. Query "performances" directly for the
-- unfiltered record.
CREATE VIEW "v_tower_performances" AS
SELECT
  p."perf_id",
  p."bb_id",
  p."perf_date",
  p."title",
  p."method",
  p."changes",
  p."association",
  d."TowerID"   AS "dove_tower_id",
  d."Place"     AS "dove_place",
  d."Dedicn"    AS "dove_dedication",
  d."County"    AS "dove_county",
  d."RingType"  AS "dove_ring_type"
FROM "performances" p
JOIN "dove" d ON d."TowerID" = p."dove_tower_id";
