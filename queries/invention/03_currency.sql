-- Which methods have been rung in the 2021-24 window, per the schema/005 linkage.
--
-- Two sets, deliberately. `asserted` is what the resolver was willing to claim.
-- `candidate` additionally includes methods that appear in the candidate lists of
-- spliced performances the oracle REFUSED -- rows where the wrong number of
-- methods was found, so nothing was asserted, but where the names found are still
-- evidence that a method was rung.
--
-- This matters because spliced peals are precisely where rare methods appear, so
-- the resolver's 72.2% coverage could manufacture the finding on this page all by
-- itself. Reporting both gives a lower and an upper bound instead of a point
-- estimate that cannot be checked. The bounds are 13.0% and 16.4% for the
-- 1975-99 vintage, so the conclusion survives either way.
SELECT DISTINCT method_id FROM performance_methods;

-- 1: the candidate name-keys from refused spliced rows. Mapped back to methods in
-- Python, using the same index the resolver builds, because the mapping needs the
-- stage-aware name index and JSON extraction that SQLite cannot do here.
SELECT candidates
FROM performance_method_unresolved
WHERE candidates IS NOT NULL AND reason = 'spliced_count_mismatch';
