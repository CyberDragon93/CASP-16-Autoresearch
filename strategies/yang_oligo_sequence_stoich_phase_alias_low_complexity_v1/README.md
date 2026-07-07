# yang_oligo_sequence_stoich_phase_alias_low_complexity_v1

Purpose: apply the existing sequence-derived low-complexity terminal cleanup on
top of the phase-alias-corrected protein-oligo sequence/stoichiometry input.

Base input:

- `strategies/yang_protein_oligo_sequence_stoich_phase_alias_v1/casp16_server_protein_v2_aliasfix/inputs.json`

Generated artifacts:

- `casp16_server_protein_v2_aliasfix/inputs.json`
- `casp16_server_protein_v2_aliasfix/manifest.tsv`

Generation summary:

- jobs: 165
- protein sequences audited: 280
- changed sequences: 27
- changed targets: 21
- output SHA256:
  `902227831928d4dabfcd442cdfe853d72777c07a696591a91b884b5905512751`

This is an intermediate artifact. Use
`yang_oligo_sequence_stoich_phase_alias_low_complexity_large_fallback_v1` for a
no-over-token full-stack input.

