# yang_large_target_split_or_fallback_v1

This is a predeclared coverage-recovery strategy for Protenix jobs that fail
before inference with `n_token > 2560`.

The rule is target-agnostic:

1. Leave jobs at or below the Protenix token budget unchanged.
2. For oversized protein-only jobs, apply conservative epitope/His/TEV tag
   cleanup to each protein chain.
3. If the cleaned full job still exceeds 2560 tokens, keep the original-order
   prefix of chains or chain copies that fits within 2560 tokens.
4. Record every kept and dropped chain in the manifest.

This is not an oracle strategy. It does not read native references, official
scores, or previous target scores. It is expected to hurt some assembly quality
while converting hard inference failures into scored or diagnosable predictions.

Generated server benchmark artifacts:

- `casp16_server_protein_v1/inputs.json`
- `casp16_server_protein_v1/manifest.tsv`

On the current server benchmark inputs it changes exactly the eight known
Protenix token-limit failures: `T1295`, `H0217`, `H0258`, `H0272`, `H1217`,
`H1258`, `H1272`, and `T1295O`.

