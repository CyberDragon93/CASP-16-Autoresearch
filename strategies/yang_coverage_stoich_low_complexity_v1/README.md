# yang_coverage_stoich_low_complexity_v1

Purpose: test a riskier Yang-style construct cleanup on the alias-fixed server
benchmark after the coverage and token-safe stoichiometry fixes are already in
place.

Base input:

- `strategies/yang_oligo_stoichiometry_token_safe_v1/casp16_server_protein_v2_aliasfix/inputs.json`

Rules:

1. Preserve the v2 alias-fixed target set and the upstream coverage/stoich
   changes.
2. Apply the existing low-complexity terminal cleanup only from sequence
   content.
3. Do not read native/reference structures, official scores, or previous target
   scores.
4. Keep the fixed `dev_fixed` budget: Protenix, seed `101`, sample `1`,
   `first_output_only`.

Generated artifacts:

- `casp16_server_protein_v2_aliasfix/inputs.json`
- `casp16_server_protein_v2_aliasfix/manifest.tsv`

Generation summary:

- jobs: 163
- protein sequences audited: 264
- changed sequences: 27
- changed targets: 21

Notable changed target classes:

- terminal His/expression tags: `T1201`, `T1266`, `T1278`, `T1292`, and phase
  aliases
- low-complexity complex segments: `H0217`, `H0272`, `H1217`, `H1272`, and
  phase aliases
- H1258/H0258/H2258 tag cleanup on the large LRRK2-like chain and partner
  chain

Launch gate: this row is now superseded by
`yang_oligo_sequence_stoich_low_complexity_large_fallback_v1`, which adds
protein-oligo sequence recovery and keeps 0 over-token jobs. Run this older
candidate only as an explicit ablation, not as the main attack path.
