# scoreable_target_subset_oligo_first_phase_alias_v1

Purpose: spend the next five-candidate v2 attack budget on the locally
scoreable target subset, with exact protein-oligo jobs first and with
phase-alias stoichiometry fixed before prediction.

Base input:

- `strategies/yang_oligo_sequence_stoich_phase_alias_low_complexity_large_fallback_v1/casp16_server_protein_v2_aliasfix/inputs.json`

Generated artifacts:

- `casp16_server_protein_v2_aliasfix/inputs.json`
- `casp16_server_protein_v2_aliasfix/manifest.tsv`

Generation summary:

- original jobs: 165
- kept jobs: 74
- skipped jobs: 91
- prioritized exact oligo jobs: 50
- output SHA256:
  `b364e95132dbb96fa212f6afbc818cf0e4fb031bc64ac5491fa3c1e4f1f6336c`

MSA cache check:

- `./casp16 check-msa-cache --input-json strategies/scoreable_target_subset_oligo_first_phase_alias_v1/casp16_server_protein_v2_aliasfix/inputs.json --report-tsv diagnostics/msa_cache/scoreable_target_subset_oligo_first_phase_alias_v1.tsv --require-complete`
- result: 141/141 protein chains covered, 0 missing sources, 0 stale covered
  rows.

Queued run:

- `server_v2_attack_scoreable_oligo_first_phase_alias_msa_reuse_protenix5_seed101_105`

