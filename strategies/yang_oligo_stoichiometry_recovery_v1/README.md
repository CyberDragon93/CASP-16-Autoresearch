# yang_oligo_stoichiometry_recovery_v1

This strategy recovers official protein-oligo stoichiometry when the generated
server-benchmark input fell back to one copy per sequence because the local
server target row had `UNK` stoichiometry.

Base input:

- `strategies/yang_terminal_tag_cleanup_v1/casp16_server_protein_v1/inputs.json`

Rules:

1. Read benchmark target metadata and the official parsed CASP16 target list.
2. Apply only to `protein_oligo` jobs that are protein-only.
3. If the official `Oligo.State` has one count per input protein entity, rewrite
   `count` and chain IDs in original entity order.
4. Record whether the recovered assembly exceeds the 2560-token Protenix
   budget.
5. Do not read native/reference structures, official score tables, or previous
   target scores.

Generated server benchmark artifacts:

- `casp16_server_protein_v1/inputs.json`
- `casp16_server_protein_v1/manifest.tsv`

On the current server benchmark inputs it changes 9 existing jobs:

- Under the Protenix token limit after recovery: `H1232`, `H1233`, `H1236`,
  `H1244`, `H1267`.
- Above the token limit after recovery: `H1217`, `H1227`, `H1258`, `H1265`.

This is a strategy artifact, not a queued run. It exposes the next real
winner-style step: combine exact stoichiometry with domain/window construction
instead of silently predicting smaller A1B1-like assemblies.
