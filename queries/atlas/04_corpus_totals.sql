-- Atlas · the four headline figures
--
-- 51,451 bells attributed · 12,635 towers · 1290-2026 · 22,111 peals linked.
-- The first two come from 01_bells_by_founder_group.sql; these are the rest.

SELECT COUNT(*) AS methods FROM methods;

SELECT COUNT(*) AS tower_linked_first_performances
FROM method_performances
WHERE dove_tower_id IS NOT NULL;

-- The counterpart figure, quoted in the page footer: records deliberately left
-- unlinked. Mostly handbell peals rung in private houses, which have no tower.
SELECT COUNT(*) AS unlinked
FROM method_performances
WHERE dove_tower_id IS NULL;
