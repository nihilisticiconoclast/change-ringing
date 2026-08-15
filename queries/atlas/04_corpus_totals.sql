-- Atlas · the four headline figures
--
-- 51,523 bells attributed · 12,635 towers · 1290-2026 · 22,117 peals linked,
-- on the current snapshot. All four drift with Dove; the page computes them.
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
