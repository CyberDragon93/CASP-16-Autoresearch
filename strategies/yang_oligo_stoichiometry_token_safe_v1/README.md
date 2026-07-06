# yang_oligo_stoichiometry_token_safe_v1

This strategy is the queue-safe derivative of
`yang_oligo_stoichiometry_recovery_v1`.

Base input:

- `strategies/yang_sequence_recovery_large_target_fallback_v1/casp16_server_protein_v1/inputs.json`

Rules:

1. Start from the stacked coverage-recovery input so missing sequence and
   token-limit hard failures are already handled.
2. Restore official parsed `Oligo.State` only when the recovered protein-only
   assembly stays within the 2560-token Protenix budget.
3. Leave oversize or already-fallback-reduced assemblies unchanged and record
   the skip reason.
4. Do not read native/reference structures, official score tables, or previous
   target scores.

Generated server benchmark artifacts:

- `casp16_server_protein_v1/inputs.json`
- `casp16_server_protein_v1/manifest.tsv`

On the current stacked server input it changes 5 oligo jobs:

- `H1232`: `A2B2`
- `H1233`: `A2B2C2`
- `H1236`: `A3B6`
- `H1244`: `A2B2C2`
- `H1267`: `A2B2`

It skips exact recovery for assemblies that would exceed the token budget or
whose entity list was already reduced by the upstream fallback. The generated
input keeps 135 jobs, and the largest optimized job remains 2535 tokens.
