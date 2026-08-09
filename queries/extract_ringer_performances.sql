-- Extract all ringer performance instances with geographic, association, and performance metadata
-- Used by scripts/resolve_ringer_identities.py for ringer identity resolution and co-occurrence clustering.

SELECT 
    r.perf_id,
    r.position AS bell_position,
    r.bell,
    TRIM(r.name) AS raw_name,
    r.conductor,
    p.perf_date,
    p.association,
    p.dove_tower_id,
    p.place,
    p.dedication,
    p.changes,
    p.method
FROM performance_ringers r
JOIN performances p ON p.perf_id = r.perf_id
WHERE r.name IS NOT NULL 
  AND TRIM(r.name) != ''
ORDER BY r.perf_id ASC, r.position ASC;
