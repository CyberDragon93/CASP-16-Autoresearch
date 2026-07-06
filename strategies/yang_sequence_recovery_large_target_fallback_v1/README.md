# yang_sequence_recovery_large_target_fallback_v1

This strategy stacks two target-agnostic coverage fixes on top of the current
best terminal-tag-cleaned server input.

Base input:

- `strategies/yang_terminal_tag_cleanup_v1/casp16_server_protein_v1/inputs.json`

Rules:

1. Run `yang_sequence_recovery_v1` to recover protein-domain jobs that are
   missing or locally misparsed as nucleic-acid records.
2. Run `yang_large_target_split_or_fallback_v1` on the recovered inputs.
3. Leave jobs at or below the Protenix 2560-token budget unchanged.
4. For oversized protein-only jobs, use the predeclared epitope cleanup and
   original-order chain/copy prefix budget fallback.
5. Write a phase-aware manifest so each changed target records whether it came
   from sequence recovery or token-budget fallback.

This does not read native/reference structures, official scores, or previous
target scores. It is intended to remove hard local coverage failures before
spending more multi-seed attack compute.

Generated server benchmark artifacts:

- `casp16_server_protein_v1/inputs.json`
- `casp16_server_protein_v1/manifest.tsv`

On the current server benchmark inputs it changes 40 unique targets:

- 32 protein-domain sequence recovery targets, including `T1212`,
  `T1239V1`, `T1239V2`, and `T2280`.
- 10 token-budget fallback targets: `T1295`, `H0217`, `H0258`, `H0272`,
  `H1217`, `H1258`, `H1272`, `T1295O`, plus recovered oversized domains
  `T2257` and `T2270`.

The generated inputs contain 135 Protenix jobs. The largest optimized job is
2535 tokens, below the 2560-token Protenix limit.
