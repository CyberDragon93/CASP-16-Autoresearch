# yang_oligo_sequence_stoich_low_complexity_large_fallback_v1

Purpose: create the current strongest v2 no-over-token Protenix input stack:
protein-oligo sequence recovery, token-safe official stoichiometry, terminal
low-complexity cleanup, and target-agnostic large-target fallback.

Base input:

- `strategies/yang_oligo_sequence_stoich_low_complexity_v1/casp16_server_protein_v2_aliasfix/inputs.json`

Rules:

1. Preserve the v2 alias-fixed target set.
2. Keep recovered protein oligo targets such as `H0220`, `H1213`, `H1220`,
   `H2213`, and `H2220` as proteinChain inputs.
3. Keep token-safe exact stoichiometry where possible, including
   `H1220/H2220` as recovered protein `A1B4` jobs.
4. Apply the existing target-agnostic large-target fallback to jobs still above
   the Protenix 2560-token limit.
5. Do not read native/reference structures, official scores, previous target
   scores, or confidence files during input generation.

Generated artifacts:

- `casp16_server_protein_v2_aliasfix/inputs.json`
- `casp16_server_protein_v2_aliasfix/manifest.tsv`

Generation summary:

- jobs: 165
- changed targets in final fallback phase: 11
- max optimized job length: 2535 tokens
- jobs above 2560 tokens: 0
- output SHA256:
  `9ea5de4ffa1f7693de8f7e61374c0e51d0c54760f8efeea9839de9005a21f54e`

Largest retained jobs after fallback:

- `H1258/H0258/H2258`: 2535 tokens
- `H1220/H2220`: 2515 tokens, recovered protein `A1B4`
- `T1295/T1295O`: 2345 tokens after chain-prefix fallback
- `H0217/H1217/H2217`: 2312 tokens after fallback
- `H0272/H1272/H2272`: 2285 tokens after fallback
- `H0220`: 1912 tokens, recovered protein A/B

This artifact supersedes the older v2 no-over-token stack for future attack
budgets because it fixes the protein-oligo input modality gap before spending
multi-candidate compute.
