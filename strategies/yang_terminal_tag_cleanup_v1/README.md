# yang_terminal_tag_cleanup_v1

Purpose: reproduce the lowest-risk part of the CASP16 Yang-style optimized
input recipe by removing only obvious terminal expression/purification tags
from benchmark inputs.

This strategy is target-agnostic. It does not inspect references, official
target scores, previous local target scores, or any native structures.

## Generated Artifacts

- `casp16_server_protein_v1/inputs.json`: Protenix input JSON derived from the
  locked server benchmark input JSON.
- `casp16_server_protein_v1/manifest.tsv`: per-protein-chain audit table with
  original/optimized lengths and the exact rule applied.

Generation command:

```bash
./casp16 strategy-inputs --benchmark casp16_server_protein_v1 --strategy yang_terminal_tag_cleanup_v1
```

Current generation summary:

- jobs: 106
- protein sequences audited: 172
- changed sequences: 7
- changed targets: 7

Changed targets:

- `T1201`: trim C-terminal `HHHHHH`
- `T1266`: trim N-terminal `MGSSHHHHHHSSGLVPRGSH`
- `T1278`: trim N-terminal `MGSSHHHHHHSSGLVPRGSH`
- `T1292`: trim C-terminal `HHHHHH`
- `H1204`: trim C-terminal `HHHHHH`
- `T1201O`: trim C-terminal `HHHHHH`
- `T1292O`: trim C-terminal `HHHHHH`

## Launch Gate

Do not launch this while the current full Protenix baseline is using the GH200.
After the baseline finishes, create a full fixed-budget run spec with:

```bash
./casp16 run-spec \
  --run-id server_protenix_yang_terminal_tag_cleanup_seed101 \
  --benchmark casp16_server_protein_v1 \
  --input-json strategies/yang_terminal_tag_cleanup_v1/casp16_server_protein_v1/inputs.json \
  --input-manifest strategies/yang_terminal_tag_cleanup_v1/casp16_server_protein_v1/manifest.tsv \
  --strategy yang_terminal_tag_cleanup_v1 \
  --use-msa --use-template --use-default-params \
  --enable-cache --enable-fusion
```

Rank eligibility should use the same fixed budget as the baseline: backend
`protenix`, seed `101`, sample `1`, and selected model policy
`first_output_only`. MSA, templates, default params, cache, fusion, and TF32
should match the baseline.
