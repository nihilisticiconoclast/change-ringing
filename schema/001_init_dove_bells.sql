-- Change Ringing project: initial schema
-- Source: Dove's Guide for Church Bell Ringers (CC BY-SA 4.0), https://dove.cccbr.org.uk
-- Generated from a working SQLite build on 2026-08-09; exported directly from
-- sqlite_master rather than retyped, so this is known to match what was tested.
--
-- Seven source tables from Dove's bulk CSV export:
--   dove      -- the actual change-ringing population: full-circle + lightweight rings only (canonical query target)
--   towers    -- full installation register, superset of dove (also chimes, carillons, clock chimes)
--   bells     -- individual bell records, joins to towers/dove on Tower_ID, to frames on Frame_ID
--   frames    -- bell-frame records, joins to towers/dove on Tower_ID
--   founders  -- bell-founder register, joins to bells on Founder = Name
--   changes   -- Dove's Guide's own edit log (NOT change-ringing performance data -- do not confuse the two)
--   regions   -- general administrative/ecclesiastical gazetteer (dioceses, historic counties, etc.)
--
-- Column names are sanitised from the original CSV headers (spaces/punctuation -> underscore),
-- e.g. "Weight (lbs)" -> "Weight__lbs", "Tower ID" -> "Tower_ID". Use these exact names in queries.

CREATE TABLE "bells" (
"Bell_ID" INTEGER,
  "Place" TEXT,
  "Dedication" TEXT,
  "Region" TEXT,
  "Tower_ID" INTEGER,
  "Grid_Ref" TEXT,
  "Latitude" REAL,
  "Longitude" REAL,
  "Ring_ID" INTEGER,
  "Collection_Type" TEXT,
  "Ring_Size" TEXT,
  "Bell_Role" TEXT,
  "Bell_Name" TEXT,
  "Weight__lbs" REAL,
  "Weight__approx" TEXT,
  "Nominal__Hz" REAL,
  "Note" TEXT,
  "Diameter__in" REAL,
  "Shape" TEXT,
  "Material" TEXT,
  "Cast_Date" TEXT,
  "Listed" TEXT,
  "Founder" TEXT,
  "Founder_Uncertain" TEXT,
  "Caster" TEXT,
  "Canons" TEXT,
  "Turnings" TEXT,
  "Cracked" TEXT,
  "Frame_ID" REAL,
  "In_Pit" TEXT,
  "Modification_Date" TEXT
);

CREATE TABLE "changes" (
"Date" TEXT,
  "TowerID" INTEGER,
  "Place" TEXT,
  "Region" TEXT,
  "Description_of_change" TEXT,
  "Source" TEXT,
  "Route" TEXT
);

CREATE TABLE "dove" (
"TowerID" INTEGER,
  "RingID" INTEGER,
  "RingType" TEXT,
  "Place" TEXT,
  "Place2" TEXT,
  "PlaceCL" TEXT,
  "Dedicn" TEXT,
  "TowerStatus" TEXT,
  "StatusFirst" TEXT,
  "BareDedicn" TEXT,
  "AltName" TEXT,
  "RingName" TEXT,
  "Region" TEXT,
  "County" TEXT,
  "Country" TEXT,
  "HistRegion" TEXT,
  "ISO3166code" TEXT,
  "Diocese" TEXT,
  "Lat" REAL,
  "Long" REAL,
  "Bells" INTEGER,
  "UR" TEXT,
  "Semitones" TEXT,
  "Wt" REAL,
  "App" TEXT,
  "Note" TEXT,
  "Hz" REAL,
  "Details" TEXT,
  "GF" TEXT,
  "Toilet" TEXT,
  "Simulator" TEXT,
  "ExtraInfo" TEXT,
  "WebPage" TEXT,
  "Affiliations" TEXT,
  "NG" TEXT,
  "Postcode" TEXT,
  "Practice" TEXT,
  "OvhaulYr" TEXT,
  "Contractor" TEXT,
  "TuneYr" REAL,
  "LGrade" TEXT,
  "BldgID" TEXT,
  "ChurchCare" REAL,
  "CHRAssetID" REAL,
  "TowerBase" INTEGER,
  "DoveID" TEXT,
  "SNLat" REAL,
  "SNLong" REAL
);

CREATE TABLE "founders" (
"ID" REAL,
  "Name" TEXT,
  "From" REAL,
  "To" REAL,
  "Group" TEXT,
  "Location" TEXT,
  "Bells" INTEGER,
  "Extant_From" REAL,
  "Extant_To" REAL,
  "Rings" INTEGER
);

CREATE TABLE "frames" (
"Frame_ID" INTEGER,
  "Place" TEXT,
  "Dedication" TEXT,
  "Region" TEXT,
  "Tower_ID" INTEGER,
  "Grid_Ref" TEXT,
  "Latitude" REAL,
  "Longitude" REAL,
  "Frame_Number" TEXT,
  "Frame_Date" TEXT,
  "Listed" TEXT,
  "Materials" TEXT,
  "Maker" TEXT,
  "Maker_Uncertain" TEXT,
  "Trusses" TEXT,
  "Layout" TEXT,
  "Resultant_Layout" TEXT,
  "Num_Extensions" REAL
);

CREATE TABLE "regions" (
"ID" INTEGER,
  "Name" TEXT,
  "Type" TEXT,
  "Category" TEXT,
  "ParentID" REAL
);

CREATE TABLE "towers" (
"TowerID" INTEGER,
  "RingID" INTEGER,
  "RingType" TEXT,
  "Place" TEXT,
  "Place2" TEXT,
  "PlaceCL" TEXT,
  "Dedicn" TEXT,
  "TowerStatus" TEXT,
  "StatusFirst" TEXT,
  "BareDedicn" TEXT,
  "AltName" TEXT,
  "RingName" TEXT,
  "Region" TEXT,
  "County" TEXT,
  "Country" TEXT,
  "HistRegion" TEXT,
  "ISO3166code" TEXT,
  "Diocese" TEXT,
  "Lat" REAL,
  "Long" REAL,
  "Bells" REAL,
  "UR" TEXT,
  "Semitones" TEXT,
  "Wt" REAL,
  "App" TEXT,
  "Note" TEXT,
  "Hz" REAL,
  "Details" TEXT,
  "GF" TEXT,
  "Toilet" TEXT,
  "Simulator" TEXT,
  "ExtraInfo" TEXT,
  "WebPage" TEXT,
  "Affiliations" TEXT,
  "NG" TEXT,
  "Postcode" TEXT,
  "Practice" TEXT,
  "OvhaulYr" TEXT,
  "Contractor" TEXT,
  "TuneYr" REAL,
  "LGrade" TEXT,
  "BldgID" TEXT,
  "ChurchCare" REAL,
  "CHRAssetID" REAL,
  "TowerBase" REAL,
  "DoveID" TEXT,
  "SNLat" REAL,
  "SNLong" REAL
);

CREATE INDEX idx_dove_towerid ON dove(TowerID);
CREATE INDEX idx_dove_doveid ON dove(DoveID);
CREATE INDEX idx_towers_towerid ON towers(TowerID);
CREATE INDEX idx_bells_towerid ON bells(Tower_ID);
CREATE INDEX idx_bells_frameid ON bells(Frame_ID);
CREATE INDEX idx_bells_founder ON bells(Founder);
CREATE INDEX idx_frames_towerid ON frames(Tower_ID);
CREATE INDEX idx_founders_name ON founders(Name);
CREATE INDEX idx_changes_towerid ON changes(TowerID);
CREATE INDEX idx_regions_name ON regions(Name);

-- Canonical query target: the actual change-ringing population (full-circle + lightweight
-- rings only), pre-filtered from dove so most queries don't need to touch the noisier
-- towers superset (which includes chimes, carillons, clock chimes).
CREATE VIEW v_ringing_towers AS
SELECT
    d.TowerID,
    d.RingID,
    d.DoveID,
    d.Place,
    d.County,
    d.Region,
    d.Country,
    d.RingType,
    d.Bells AS bell_count,
    d.Wt AS tenor_weight,
    d.Lat,
    d.Long,
    d.Practice,
    d.WebPage
FROM dove d;

-- Deduplicated tower projection from towers (superset, includes non-ringing)
CREATE VIEW v_towers_unique AS
SELECT "TowerID",
       MAX("Place")   AS "Place",
       MAX("Dedicn")  AS "Dedicn",
       MAX("County")  AS "County",
       MAX("Country") AS "Country",
       COUNT(*)       AS "installations"
FROM "towers" GROUP BY "TowerID";

-- Deduplicated tower projection from dove (ringing subset only)
CREATE VIEW v_dove_towers AS
SELECT "TowerID",
       MIN("RingID") AS "primary_ring_id",
       COUNT(*)      AS "rings",
       MAX("Place")  AS "Place",
       MAX("Dedicn") AS "Dedicn",
       MAX("County") AS "County"
FROM "dove" GROUP BY "TowerID";
