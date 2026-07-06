# yang_antibody_fv_cleanup_v1

Purpose: turn the antibody/Fv construct idea into a full-set, sequence-only
server benchmark candidate. Unlike `yang_antibody_fv_fragment_inputs_v1`, this
strategy preserves all original `casp16_server_protein_v1` jobs and target IDs.
Only detected antibody heavy/light constant regions are trimmed.

This is designed to be rank-compatible with the server benchmark protocol:
same target set, same seed/sample budget, same first-output policy, and no
reference or score-table access during input generation.

## Generated Artifacts

- `casp16_server_protein_v1/inputs.json`: full 106-job Protenix input JSON.
- `casp16_server_protein_v1/manifest.tsv`: per-protein-chain audit table with
  original/optimized lengths and exact applied rule.

Generation command:

```bash
./casp16 strategy-inputs --benchmark casp16_server_protein_v1 --strategy yang_antibody_fv_cleanup_v1
```

Current generation summary:

- jobs: 106
- protein sequences audited: 172
- changed sequences: 16
- changed targets: 8
- output sha256: `31bd85bab3241e8aedc9d577dcf2a04b438b25956164f26b34c06c58e3f481a8`

Changed targets:

- `H0222`: trim antibody chains `B,C`
- `H0223`: trim antibody chains `B,C`
- `H0225`: trim antibody chains `B,C`
- `H0233`: trim antibody chains `B,C`
- `H1222`: trim antibody chains `B,C`
- `H1223`: trim antibody chains `B,C`
- `H1225`: trim antibody chains `B,C`
- `H1233`: trim antibody chains `B,C`

The rule requires a heavy/light antibody-like N terminus, a recognized
variable-domain terminal motif around residues 85-135, and at least 50
C-terminal residues removed. It does not trim short antigen-like chains.

## Launch Gate

Queue this only after the baseline and lower-risk terminal-tag cleanup have
finished or failed clearly. It is more biologically targeted than the broad
dynamic-IDR scan, but it still changes a meaningful antibody-complex subset.

Potential full-run spec command:

```bash
./casp16 run-spec \
  --run-id server_protenix_yang_antibody_fv_cleanup_seed101 \
  --benchmark casp16_server_protein_v1 \
  --input-json strategies/yang_antibody_fv_cleanup_v1/casp16_server_protein_v1/inputs.json \
  --input-manifest strategies/yang_antibody_fv_cleanup_v1/casp16_server_protein_v1/manifest.tsv \
  --strategy yang_antibody_fv_cleanup_v1 \
  --use-msa --use-template --use-default-params
```

Use the fixed server benchmark budget: backend `protenix`, seed `101`, sample
`1`, selected model policy `first_output_only`, MSA enabled, and templates
enabled.
