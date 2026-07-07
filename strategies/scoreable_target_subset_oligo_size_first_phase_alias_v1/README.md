# scoreable_target_subset_oligo_size_first_phase_alias_v1

Purpose: keep the phase-alias-corrected scoreable target subset, but schedule
exact protein-oligo jobs by token count from small to large. This avoids
starting a retry run with 2515-2535 token blockers such as `H0220` or `H0258`
before many smaller QSglob-informative targets have produced artifacts.

Base input:

- `strategies/yang_oligo_sequence_stoich_phase_alias_low_complexity_large_fallback_v1/casp16_server_protein_v2_aliasfix/inputs.json`

Rules:

1. Keep only jobs with at least one locally available reference alias.
2. Preserve the fixed 175-target benchmark scoring denominator.
3. Put exact protein-oligo jobs first.
4. Within exact protein-oligo jobs, sort by total protein tokens ascending.
5. Do not change budget, model selection, scoring, references, or target
   eligibility.

Generated artifacts:

- `casp16_server_protein_v2_aliasfix/inputs.json`
- `casp16_server_protein_v2_aliasfix/manifest.tsv`
- `casp16_server_protein_v4_refmap/inputs.json`
- `casp16_server_protein_v4_refmap/manifest.tsv`

Generation summary:

- original jobs: 165
- kept jobs: 74
- skipped jobs: 91
- prioritized exact oligo jobs: 50
- output SHA256:
  `8e501031ba57191c52cafbee689907e786f1f7a5d98d4b6023d369a1ee671ae1`

MSA cache check:

- `./casp16 check-msa-cache --input-json strategies/scoreable_target_subset_oligo_size_first_phase_alias_v1/casp16_server_protein_v2_aliasfix/inputs.json --report-tsv diagnostics/msa_cache/scoreable_target_subset_oligo_size_first_phase_alias_v1.tsv --require-complete`
- result: 141/141 protein chains covered, 0 missing sources, 0 stale covered
  rows.

First exact-oligo blockers after sorting:

- `H0220/H1220/H2220`: recovered protein `A1B4`, total length 2515, moved
  behind smaller exact-oligo jobs.
- `H0258/H1258/H2258`: total length 2535, moved to the end of the exact-oligo
  block.

## v4 Refmap Successor

After accepting `T1278/T2278 -> 9hav` in
`casp16_server_protein_v4_refmap`, the same scoreable size-first recipe keeps
76 jobs instead of the v2 74-job subset. The two extra jobs are `T1278` and
`T2278`, both scoreable through the accepted refmap rows and both kept after
the exact-oligo priority block.

Generation summary:

- benchmark: `casp16_server_protein_v4_refmap`
- base input:
  `strategies/yang_oligo_sequence_stoich_phase_alias_low_complexity_large_fallback_v1/casp16_server_protein_v4_refmap/inputs.json`
- original jobs: 165
- kept jobs: 76
- skipped jobs: 89
- prioritized exact oligo jobs: 50
- output SHA256:
  `589c9df298c9c8b70084b08b140989a38b6760250d54cb5100da7b972df68150`

MSA cache check:

- report:
  `diagnostics/msa_cache/scoreable_target_subset_oligo_size_first_phase_alias_v1_v4.tsv`
- result: 143/143 protein chains covered, 0 missing sources, 0 stale covered
  rows.

Use this as the next scoreable-subset attack input after the running v2 P14
row is scored; do not compare it directly against v2 without noting the larger
81-reference v4 scoring registry.
