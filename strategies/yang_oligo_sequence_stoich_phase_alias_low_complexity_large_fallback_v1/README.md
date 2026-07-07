# yang_oligo_sequence_stoich_phase_alias_low_complexity_large_fallback_v1

Purpose: create the current phase-alias-corrected no-over-token v2 input stack:
protein-oligo sequence recovery, phase-alias token-safe stoichiometry,
low-complexity cleanup, and target-agnostic large-target fallback.

Base input:

- `strategies/yang_oligo_sequence_stoich_phase_alias_low_complexity_v1/casp16_server_protein_v2_aliasfix/inputs.json`

Generated artifacts:

- `casp16_server_protein_v2_aliasfix/inputs.json`
- `casp16_server_protein_v2_aliasfix/manifest.tsv`
- `casp16_server_protein_v4_refmap/inputs.json`
- `casp16_server_protein_v4_refmap/manifest.tsv`

Generation summary:

- jobs: 165
- changed targets in final fallback phase: 11
- max optimized job length: 2535 tokens
- jobs above 2560 tokens: 0
- output SHA256:
  `360fc88325fb40d97f744f76ab8220e28f9fcafc255bdf1193a636a4e24ae12c`

Largest retained jobs after fallback:

- `H1258/H0258/H2258`: 2535 tokens
- `H0220/H1220/H2220`: 2515 tokens, recovered protein `A1B4`
- `T1295/T1295O`: 2345 tokens after chain-prefix fallback
- `H0217/H1217/H2217`: 2312 tokens after fallback
- `H0272/H1272/H2272`: 2285 tokens after fallback

## v4 Refmap Stack

The v4 stack reuses the same composed recipe on top of
`casp16_server_protein_v4_refmap`, which adds accepted references for
`T1278/T2278`.

Generation chain:

1. `yang_protein_oligo_sequence_stoich_token_safe_v1`
2. `yang_low_complexity_terminal_cleanup_v1`
3. `yang_large_target_split_or_fallback_v1`

Generation summary:

- jobs: 165
- sequence/stoich phase changed targets: 3
- low-complexity changed targets: 21
- final fallback changed targets: 29
- max optimized job length: 2535 tokens
- jobs above 2560 tokens: 0
- output SHA256:
  `8c0f39ace0a9eae282274964b0337cfc894611c95293eceb7e25982f1f8055ae`

`T1278` and `T2278` pass through this stack as 360-token protein-domain jobs
and become scoreable in the v4 scoreable-subset successor.
