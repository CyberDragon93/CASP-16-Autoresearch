# scoreable_antibody_fv_oligo_size_first_phase_alias_v1

Purpose: create a queued scoreable attack successor that combines the current
phase-alias input fixes with the antibody Fv target-lab signal, then re-sorts
exact protein-oligo jobs by token count after antibody chains are shortened.

Base input:

- `strategies/scoreable_oligo_size_first_phase_alias_antibody_fv_cleanup_v1/casp16_server_protein_v2_aliasfix/inputs.json`

Rules:

1. Keep only locally scoreable jobs while preserving the fixed benchmark
   scoring denominator.
2. Keep `H0220/H1220/H2220` as recovered protein `A1B4`.
3. Apply only sequence-derived antibody Fv constant-region cleanup.
4. Put exact protein-oligo jobs first, sorted by total protein tokens after
   cleanup.
5. Keep confidence and DockQ as diagnostics only; ranked quality remains
   benchmark scoring.

Generated artifacts:

- `casp16_server_protein_v2_aliasfix/inputs.json`
- `casp16_server_protein_v2_aliasfix/manifest.tsv`

Generation summary:

- jobs: 74
- kept jobs: 74
- prioritized exact oligo jobs: 50
- skipped jobs: 0
- output SHA256:
  `285c9e088c0d91bb7dd80920637519a2e3fe103ab28c190a452ee6eb9492bd4c`

MSA cache check:

- `./casp16 check-msa-cache --input-json strategies/scoreable_antibody_fv_oligo_size_first_phase_alias_v1/casp16_server_protein_v2_aliasfix/inputs.json --report-tsv diagnostics/msa_cache/scoreable_antibody_fv_oligo_size_first_phase_alias_v1.tsv --source-run-id targetlab_protenix_yang_antibody_fv_seed101 --require-complete`
- result: 141/141 protein chains covered, 0 missing sources, 0 stale covered
  rows.

Changed antibody targets:

- `H0222/H1222/H2222`
- `H0223/H1223/H2223`
- `H0225/H1225/H2225`
- `H0233/H1233/H2233`

