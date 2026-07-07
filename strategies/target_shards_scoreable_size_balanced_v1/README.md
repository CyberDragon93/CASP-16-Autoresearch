# target_shards_scoreable_size_balanced_v1

Purpose: split scoreable-subset Protenix attack inputs into target-disjoint
GH200 shards with roughly balanced token totals. Shards are execution units
only; they are merged back into a single benchmark run before scoring.

Rules:

1. Keep the benchmark scoring denominator fixed.
2. Keep shard runs rank-ineligible.
3. Use `merge-shards --allow-target-shards` with the full merged input JSON
   before scoring.
4. Do not submit a successor shard set until the previous attack row has been
   merged and scored.

Current artifacts:

- `casp16_server_protein_v2_aliasfix/`: live P14 v2 scoreable attack shards,
  74 jobs, seeds `101..105`.
- `casp16_server_protein_v4_refmap/`: prepared P15 v4 refmap successor shards,
  76 jobs, seeds `101..105`, deferred until P14 scoring.

The v4 shards add `T1278` and `T2278` through the accepted v4 reference map
while preserving the same Protenix budget and confidence-based model selector.
