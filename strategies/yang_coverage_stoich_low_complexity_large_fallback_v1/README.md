# yang_coverage_stoich_low_complexity_large_fallback_v1

Purpose: keep the alias-fixed v2 coverage/stoichiometry/construct-cleanup
candidate from wasting a full Protenix run on known `n_token > 2560` hard
failures.

Base input:

- `strategies/yang_coverage_stoich_low_complexity_v1/casp16_server_protein_v2_aliasfix/inputs.json`

Rules:

1. Preserve the v2 alias-fixed target set and all upstream coverage,
   token-safe stoichiometry, and terminal low-complexity cleanup changes.
2. For jobs still above the Protenix 2560-token limit, apply the existing
   target-agnostic large-target fallback: expression-tag cleanup first, then
   original-order chain/copy prefix selection under the token budget.
3. Do not read native/reference structures, official scores, previous target
   scores, or confidence files during input generation.
4. Keep the fixed `dev_fixed` budget: Protenix, seed `101`, sample `1`,
   `first_output_only`.

Generated artifacts:

- `casp16_server_protein_v2_aliasfix/inputs.json`
- `casp16_server_protein_v2_aliasfix/manifest.tsv`

Generation summary:

- jobs: 163
- changed targets: 11
- oversize jobs before fallback: 11
- oversize jobs after fallback: 0
- output SHA256:
  `e480cf42d9d680d83c4a67b2f87b1532a7f2214624ba42ee0ad61a01f2d6e72f`

Changed target classes:

- protein-domain `T1295`
- protein-oligo phase aliases for `H0217`, `H0258`, `H0272`, `H1217`,
  `H1258`, `H1272`, `H2217`, `H2258`, `H2272`
- `T1295O`

Launch gate: this row is now superseded by
`yang_oligo_sequence_stoich_low_complexity_large_fallback_v1`, which keeps the
same no-over-token property while adding protein-oligo sequence recovery. Treat
this older row as a coverage-recovery ablation; it is not an attack-budget row
and does not claim full-assembly fidelity for cropped oligo targets.
