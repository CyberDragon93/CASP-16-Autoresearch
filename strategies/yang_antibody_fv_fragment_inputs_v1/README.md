# yang_antibody_fv_fragment_inputs_v1

Purpose: test a narrow antibody-antigen construct hypothesis inspired by the
CASP16 complex winner notes. This target-lab artifact trims obvious antibody
heavy/light constant regions and keeps the antigen chain unchanged, producing
Fv-style complex inputs for diagnostic runs.

This strategy uses only input sequences and conservative antibody motifs, but
it is still a target-lab branch. Do not queue it as a ranked server result
without first promoting the rule into a predeclared full benchmark policy.

## Generated Artifacts

- `casp16_server_protein_v1/inputs.json`: Fv-only Protenix input JSON for
  changed antibody-antigen targets.
- `casp16_server_protein_v1/manifest.tsv`: per-protein-chain audit table with
  chain IDs, original/optimized lengths, and exact trim rules.

Generation command:

```bash
./casp16 strategy-inputs --benchmark casp16_server_protein_v1 --strategy yang_antibody_fv_fragment_inputs_v1
```

Current generation summary:

- Fv jobs: 8
- changed targets: 8
- changed antibody chains: 16
- audited protein chains: 172
- output sha256: `ed3187affd645d3de2183ae5bd4619a4b826eab8110fd516a964161b41862b04`

Changed target jobs:

- `H0222__fv`
- `H0223__fv`
- `H0225__fv`
- `H0233__fv`
- `H1222__fv`
- `H1223__fv`
- `H1225__fv`
- `H1233__fv`

The rule requires a heavy/light antibody-like N terminus, a recognized
variable-domain terminal motif around residues 85-135, and at least 50
C-terminal residues removed. Short antigen-like chains are preserved.

## Launch Gate

Use this only for target-lab learning:

- compare Fv-only antibody-antigen predictions with full antibody predictions,
- inspect whether constant regions are distracting assembly prediction,
- promote only if the rule becomes a target-agnostic, predeclared server
  strategy with full-set evaluation.

Potential lab-only run spec command:

```bash
./casp16 run-spec \
  --run-id targetlab_protenix_yang_antibody_fv_seed101 \
  --benchmark casp16_server_protein_v1 \
  --input-json strategies/yang_antibody_fv_fragment_inputs_v1/casp16_server_protein_v1/inputs.json \
  --input-manifest strategies/yang_antibody_fv_fragment_inputs_v1/casp16_server_protein_v1/manifest.tsv \
  --strategy yang_antibody_fv_fragment_inputs_v1 \
  --rank-eligible false \
  --use-msa --use-template --use-default-params
```

Keep results from this branch separate from server-track leaderboard claims.
