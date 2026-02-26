# Merging Module

Fuzzy entity merging and co-occurrence relationship generation.

## Files

- `fuzzy_merger.py` - FuzzyEntityMerger that clusters similar entities using rapidfuzz token_sort_ratio
- `cooccurrence.py` - `create_cooccurrence_relationships()` that generates RELATED_TO edges from chunk co-occurrence

## Conventions

- Only merge entities of the same EntityType
- Greedy clustering: first unassigned entity becomes seed, absorbs all similar unassigned entities
- Primary entity = highest confidence in cluster
- Merged entity names tracked in `metadata["merged_names"]`
- Co-occurrence pairs normalized as `(min(id), max(id))` to deduplicate
- Weight = number of chunks the pair co-occurs in
- `rapidfuzz` is lazy-imported (optional dependency under `fuzzy` extra)
