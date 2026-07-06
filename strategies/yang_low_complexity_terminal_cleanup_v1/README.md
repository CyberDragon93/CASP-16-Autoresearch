# yang_low_complexity_terminal_cleanup_v1

Purpose: explore the next Yang-style optimized-input step after obvious tag
removal: trimming only short terminal low-complexity regions that look like
construct or disorder noise.

This strategy is intentionally more aggressive than `yang_epitope_tag_cleanup_v1`.
It is sequence-only and target-agnostic, but it can remove real biology if used
carelessly. It is therefore generated as an artifact and not queued as a full
run yet.

## Generated Artifacts

- `casp16_server_protein_v1/inputs.json`: Protenix input JSON derived from the
  locked server benchmark input JSON.
- `casp16_server_protein_v1/manifest.tsv`: per-protein-chain audit table with
  original/optimized lengths and exact applied rule.

Generation command:

```bash
./casp16 strategy-inputs --benchmark casp16_server_protein_v1 --strategy yang_low_complexity_terminal_cleanup_v1
```

Current generation summary:

- jobs: 106
- protein sequences audited: 172
- changed sequences: 17
- changed targets: 13

Additional changes beyond `yang_epitope_tag_cleanup_v1`:

- `H0217`: trim 40-aa N-terminal low-complexity region on chain `E`
- `H0272`: trim 40-aa C-terminal low-complexity region on chain `G`
- `H0272`: trim 40-aa N-terminal low-complexity region on chain `I`
- `H1217`: trim 40-aa N-terminal low-complexity region on chain `E`
- `H1272`: trim 40-aa C-terminal low-complexity region on chain `G`
- `H1272`: trim 40-aa N-terminal low-complexity region on chain `I`

The low-complexity rule trims exactly 40 terminal residues only when the
terminal segment has low Shannon entropy, high `G/S` content, or high
composition in `GSPQKENR`, and only if at least 80 residues remain.

## Launch Gate

Do not queue this until one of these is true:

- the conservative terminal cleanup run has finished and tag cleanup clearly
  helps, or
- the baseline shows these H0217/H0272/H1217/H1272 chains are among the main
  failures and a more aggressive construct cleanup is justified.

Potential full-run spec command:

```bash
./casp16 run-spec \
  --run-id server_protenix_yang_low_complexity_terminal_cleanup_seed101 \
  --benchmark casp16_server_protein_v1 \
  --input-json strategies/yang_low_complexity_terminal_cleanup_v1/casp16_server_protein_v1/inputs.json \
  --input-manifest strategies/yang_low_complexity_terminal_cleanup_v1/casp16_server_protein_v1/manifest.tsv \
  --strategy yang_low_complexity_terminal_cleanup_v1 \
  --use-msa --use-template --use-default-params
```

Use the same fixed budget as the baseline: backend `protenix`, seed `101`,
sample `1`, and selected model policy `first_output_only`.
