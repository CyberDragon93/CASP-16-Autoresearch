# yang_terminal_tag_antibody_fv_cleanup_v1

Purpose: combine two audited sequence-only construct cleanups into one
full-set server benchmark candidate:

- `yang_terminal_tag_cleanup_v1` for obvious terminal expression/purification
  tags.
- `yang_antibody_fv_cleanup_v1` for antibody heavy/light constant-region
  trimming.

This strategy preserves all original `casp16_server_protein_v1` jobs and target
IDs. It does not inspect native references, official score tables, previous
target scores, or leaderboard artifacts during input generation.

## Generated Artifacts

- `casp16_server_protein_v1/inputs.json`: full 106-job Protenix input JSON.
- `casp16_server_protein_v1/manifest.tsv`: per-protein-chain audit table with
  original/optimized lengths and exact applied rule.

Generation command:

```bash
./casp16 strategy-inputs --benchmark casp16_server_protein_v1 --strategy yang_terminal_tag_antibody_fv_cleanup_v1
```

Current generation summary:

- jobs: 106
- protein sequences audited: 172
- changed sequences: 23
- changed targets: 15
- output sha256: `add69e2af5921d59214d40493db99d2a6ee5149f7c0417b6ef9501357c32f2f9`

Changed target groups:

- terminal tag cleanup: `T1201`, `T1266`, `T1278`, `T1292`, `H1204`,
  `T1201O`, `T1292O`
- antibody Fv cleanup: `H0222`, `H0223`, `H0225`, `H0233`, `H1222`, `H1223`,
  `H1225`, `H1233`

## Launch Gate

Queue this after the individual terminal-tag and antibody-Fv ablations. The
point is to test whether the two non-overlapping construct cleanups compose
cleanly on the fixed full server target set.

Potential full-run spec command:

```bash
./casp16 run-spec \
  --run-id server_protenix_yang_terminal_tag_antibody_fv_cleanup_seed101 \
  --benchmark casp16_server_protein_v1 \
  --input-json strategies/yang_terminal_tag_antibody_fv_cleanup_v1/casp16_server_protein_v1/inputs.json \
  --input-manifest strategies/yang_terminal_tag_antibody_fv_cleanup_v1/casp16_server_protein_v1/manifest.tsv \
  --strategy yang_terminal_tag_antibody_fv_cleanup_v1 \
  --use-msa --use-template --use-default-params \
  --enable-cache --enable-fusion
```

Use the fixed server benchmark budget: backend `protenix`, seed `101`, sample
`1`, selected model policy `first_output_only`, MSA/templates/default params
enabled, and cache/fusion/TF32 matching the baseline.
