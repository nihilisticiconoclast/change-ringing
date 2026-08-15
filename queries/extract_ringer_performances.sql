-- Every ringer appearance, with the performance context identity resolution needs.
--
-- READ BY scripts/resolve_ringer_identities.py at run time. This file is not a
-- copy of that query, it IS that query -- the script loads this file rather than
-- holding its own version, for the same reason queries/atlas/ and queries/rhythm/
-- are read rather than duplicated.
--
-- It did hold its own version until 2026-08-15, and the two had drifted: this
-- file selected six columns the script never asked for and imposed an ORDER BY
-- over 1,969,949 rows that the script did not want, while the script ran a
-- narrower query inline. The header here nonetheless said "Used by
-- scripts/resolve_ringer_identities.py", so anyone reading it to understand what
-- the resolver sees would have been reading the wrong statement. A repository
-- audit passed over this file and documented it as authoritative without
-- checking, which is the failure mode lesson 20 exists for.
--
-- No ORDER BY: the resolver groups into bands by perf_id in Python and does not
-- depend on row order, and sorting two million rows to no purpose is not free.

SELECT r.perf_id,
       r.position,
       TRIM(r.name) AS name,
       p.perf_date,
       p.association,
       p.dove_tower_id,
       p.place
FROM performance_ringers r
JOIN performances p ON p.perf_id = r.perf_id
WHERE r.name IS NOT NULL AND TRIM(r.name) != '';
