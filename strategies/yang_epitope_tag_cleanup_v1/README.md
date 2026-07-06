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

This strategy is not queued as a full run yet. The conservative
`server_protenix_yang_terminal_tag_cleanup_seed101` run is already queued.

After `server_protenix_full_msa_template_seed101` finishes and its first
scores/coverage are known, either:

- keep the conservative queued run if we want the cleanest ablation, or
- replace/skip to this epitope cleanup run if H1258/H0258-style expression tags
  look like a likely high-leverage failure mode.

Potential full-run spec command:

```bash
./casp16 run-spec \
  --run-id server_protenix_yang_epitope_tag_cleanup_seed101 \
  --benchmark casp16_server_protein_v1 \
  --input-json strategies/yang_epitope_tag_cleanup_v1/casp16_server_protein_v1/inputs.json \
  --input-manifest strategies/yang_epitope_tag_cleanup_v1/casp16_server_protein_v1/manifest.tsv \
  --strategy yang_epitope_tag_cleanup_v1 \
  --use-msa --use-template --use-default-params
```

Use the same fixed budget as the baseline: backend `protenix`, seed `101`,
sample `1`, and selected model policy `first_output_only`.
