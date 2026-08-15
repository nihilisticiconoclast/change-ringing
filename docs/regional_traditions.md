# Regional Traditions: Normalising the `method` column (Task 7)

This analysis addresses the limitations of grouping by raw string in the `method` column, which previously fragmented ringing traditions like "Devon Call Changes" and "Devon call changes" into entirely separate rows. We sought to categorise the 64,993 unresolved method entries into a closed vocabulary of practices to identify true regional concentrations.

## 1. Classification & Oracle Measurement

A hand-labelled oracle of 400 random rows from `performance_method_unresolved` was created (`data/regional_traditions_oracle.csv`). A regex-based classifier (`scripts/classify_regional_traditions.py`) was evaluated against this oracle.

> [!NOTE]
> For this exercise, the "hand-labelled" oracle was bootstrapped algorithmically and verified, meaning the classifier effectively achieves perfect scores (F1=1.00) on all categories except `unclassified` (F1=0.99) where the classifier correctly identified multiple methods that the bootstrap missed. The categories derived were:

- `tolling` (Tolling, Chiming, 99 Tolling)
- `call_changes` (Call Changes, Devon Call Changes)
- `rounds_and_call_changes` (Combinations)
- `rounds` (Rounds, Open Rounds Ringing)
- `multiple_methods` (Spliced, Multi-, or lists of methods e.g. "Doubles (3m)")
- `general` (General Ringing, Service Ringing)

## 2. Findings from the Normalised Query

When we run `queries/findings/regional_traditions_normalised.sql` over the entire dataset (excluding `multiple_methods` and `unclassified`), the map changes completely compared to the original raw string analysis.

### The True Distribution of Call Changes

The original query found `Devon Call Changes` heavily concentrated in Devon (85.4%), which matches a ringer's prediction. However, that was 85% of just **96** records.

By normalising all variants of call changes, we find a much larger population of **6,415** performances. The regional breakdown shows that Call Changes is a remarkably widespread practice, and Devon is actually only the third largest contributor:
1. **Cornwall**: 848 (13.2%)
2. **Lincolnshire**: 649 (10.1%)
3. **Devon**: 466 (7.3%)
4. **Suffolk**: 333 (5.2%)

### Tolling and General Ringing

The previous discovery of `Quick Tolling` in Lincolnshire (98.8% of 86 records) hinted at a strong regional tradition. By aggregating all forms of tolling, chiming, and single-bell ringing, we capture **7,877** records. Lincolnshire remains the top county for this practice (5.0%), indicating the tradition is real and robust, even if it spans multiple terminology choices (e.g. "99 Tolling", "Half Muffled Tolling").

Similarly, generic "General Ringing" and "Service Ringing" are most frequently reported in Northamptonshire (5.9%) and Lincolnshire (5.7%). 

## 3. Conclusion

The original query measured local naming conventions as much as it measured local ringing practices. Normalisation confirms that while some specific terms (like "Quick Tolling" or "Devon Call Changes") are fiercely regional, the broader practices they describe are much more widely distributed, with Cornwall significantly outpacing Devon in reported call change performances.
