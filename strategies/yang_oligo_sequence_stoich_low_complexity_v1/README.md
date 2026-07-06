# yang_oligo_sequence_stoich_low_complexity_v1

Purpose: test Yang-style construct cleanup after fixing protein-oligo sequence
recovery and token-safe stoichiometry on the alias-fixed server benchmark.

Base input:

- `strategies/yang_protein_oligo_sequence_stoich_token_safe_v1/casp16_server_protein_v2_aliasfix/inputs.json`

Rules:

1. Preserve the v2 alias-fixed target set.
2. Preserve protein-oligo sequence recovery for `H0220/H1220/H2220`-style
   targets and token-safe official `Oligo.State` recovery.
3. Apply only the existing sequence-derived low-complexity terminal cleanup.
4. Do not read native/reference structures, official scores, previous target
   scores, or confidence files during input generation.

Generated artifacts:

- `casp16_server_protein_v2_aliasfix/inputs.json`
- `casp16_server_protein_v2_aliasfix/manifest.tsv`

Generation summary:

- jobs: 165
- protein sequences audited: 280
- changed sequences: 27
- changed targets: 21
- output SHA256:
  `a9c6ab39024c483ec760122e47386f061503d4142320b0e0fa0f9df427d3f74b`

This is an intermediate artifact. Use
`yang_oligo_sequence_stoich_low_complexity_large_fallback_v1` for a
no-over-token full-benchmark run.
