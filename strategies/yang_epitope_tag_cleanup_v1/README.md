# yang_epitope_tag_cleanup_v1

Purpose: extend the terminal-tag cleanup strategy to catch obvious N-terminal
epitope, FLAG-like, His, and TEV-cleavage expression artifacts while remaining
fully target-agnostic.

This strategy uses only input sequence prefixes/suffixes. It does not inspect
references, native structures, official score rows, previous target scores, or
leaderboard artifacts.

## Generated Artifacts

- `casp16_server_protein_v1/inputs.json`: Protenix input JSON derived from the
  locked server benchmark input JSON.
- `casp16_server_protein_v1/manifest.tsv`: per-protein-chain audit table with
  original/optimized lengths and exact applied rule.

Generation command:

```bash
./casp16 strategy-inputs --benchmark casp16_server_protein_v1 --strategy yang_epitope_tag_cleanup_v1
```

Current generation summary:

- jobs: 106
- protein sequences audited: 172
- changed sequences: 11
- changed targets: 9
- output sha256: `0d07bd99e4424f947b0e7ab907a98de7ef8ec345c964e440ff66bab3155eb10a`

Changed targets:

- `T1201`: trim C-terminal `HHHHHH`
- `T1266`: trim N-terminal `MGSSHHHHHHSSGLVPRGSH`
- `T1278`: trim N-terminal `MGSSHHHHHHSSGLVPRGSH`
- `T1292`: trim C-terminal `HHHHHH`
- `H0258`: trim N-terminal `MGSDYKDHDGDYKDHDIDYKDDDDKLG`; trim N-terminal `MGSHHHHHHSGENLYFQG`
- `H1204`: trim C-terminal `HHHHHH`
- `H1258`: trim N-terminal `MGSDYKDHDGDYKDHDIDYKDDDDKLG`; trim N-terminal `MGSHHHHHHSGENLYFQG`
- `T1201O`: trim C-terminal `HHHHHH`
- `T1292O`: trim C-terminal `HHHHHH`

## Launch Gate

This strategy is queued as `server_protenix_yang_epitope_tag_cleanup_seed101`.
It remains behind the lower-risk terminal-tag, antibody-Fv, and combined
construct-cleanup ablations so the queue preserves interpretable comparisons.

Full-run spec command:

```bash
./casp16 run-spec \
  --run-id server_protenix_yang_epitope_tag_cleanup_seed101 \
  --benchmark casp16_server_protein_v1 \
  --input-json strategies/yang_epitope_tag_cleanup_v1/casp16_server_protein_v1/inputs.json \
  --input-manifest strategies/yang_epitope_tag_cleanup_v1/casp16_server_protein_v1/manifest.tsv \
  --strategy yang_epitope_tag_cleanup_v1 \
  --use-msa --use-template --use-default-params \
  --enable-cache --enable-fusion
```

Use the same fixed budget as the baseline: backend `protenix`, seed `101`,
sample `1`, selected model policy `first_output_only`, MSA/templates/default
params enabled, and cache/fusion/TF32 enabled.
