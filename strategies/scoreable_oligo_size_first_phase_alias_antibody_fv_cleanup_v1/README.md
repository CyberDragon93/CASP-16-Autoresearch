# scoreable_oligo_size_first_phase_alias_antibody_fv_cleanup_v1

Purpose: apply the existing sequence-only antibody Fv constant-region cleanup
to the size-first phase-alias scoreable attack input.

Base input:

- `strategies/scoreable_target_subset_oligo_size_first_phase_alias_v1/casp16_server_protein_v2_aliasfix/inputs.json`

Rules:

1. Preserve the 74 locally scoreable jobs and fixed 175-target scoring
   denominator.
2. Preserve phase-alias `A1B4` stoichiometry for `H0220/H1220/H2220`.
3. Trim only antibody heavy/light chains with recognized variable-domain motifs
   and at least 50 C-terminal residues removed.
4. Do not read native/reference structures, official scores, previous target
   scores, or confidence files during input generation.

Generated artifacts:

- `casp16_server_protein_v2_aliasfix/inputs.json`
- `casp16_server_protein_v2_aliasfix/manifest.tsv`

Generation summary:

- jobs: 74
- changed targets: 12
- changed sequences: 24
- protein sequences audited: 141
- output SHA256:
  `5f57eb3da345d09072d1f178a706d4595537999a4c6281019c69ae3e84ca74b8`

This is an intermediate artifact. Use
`scoreable_antibody_fv_oligo_size_first_phase_alias_v1` for the final
size-sorted run input after antibody chains have been shortened.

