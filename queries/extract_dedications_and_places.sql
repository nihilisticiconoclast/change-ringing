-- Extract all church dedications, alternative names, and place names across the corpus
-- Used by scripts/build_name_lexicon.py to construct data/name_lexicon.csv

SELECT DISTINCT
    'dove' AS source_table,
    TowerID AS tower_id,
    Dedicn AS raw_dedication,
    BareDedicn AS raw_bare_dedication,
    Place AS raw_place,
    Place2 AS raw_place2,
    PlaceCL AS raw_place_cl,
    AltName AS raw_alt_name,
    County AS raw_county,
    Country AS raw_country
FROM dove
WHERE Dedicn IS NOT NULL OR Place IS NOT NULL

UNION ALL

SELECT DISTINCT
    'towers' AS source_table,
    TowerID AS tower_id,
    Dedicn AS raw_dedication,
    BareDedicn AS raw_bare_dedication,
    Place AS raw_place,
    Place2 AS raw_place2,
    PlaceCL AS raw_place_cl,
    AltName AS raw_alt_name,
    County AS raw_county,
    Country AS raw_country
FROM towers
WHERE Dedicn IS NOT NULL OR Place IS NOT NULL;
