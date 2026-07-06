# yang_hydrophobic_leader_cleanup_v1

Purpose: test a riskier Yang-style construct-cleanup variant for N-terminal
hydrophobic leader or signal-like peptides, while still using only target input
sequences.

This strategy inherits `yang_low_complexity_terminal_cleanup_v1`, then applies a
conservative hydrophobic-leader heuristic. It does not inspect native
references, official score rows, previous target scores, or leaderboard
artifacts. It is generated as an artifact and is not queued as a full run yet.

## Generated Artifacts

- `casp16_server_protein_v1/inputs.json`: Protenix input JSON derived from the
  locked server benchmark input JSON.
- `casp16_server_protein_v1/manifest.tsv`: per-protein-chain audit table with
  original/optimized lengths and exact applied rule.

Generation command:

```bash
./casp16 strategy-inputs --benchmark casp16_server_protein_v1 --strategy yang_hydrophobic_leader_cleanup_v1
```

Current generation summary:

- jobs: 106
- protein sequences audited: 172
- changed sequences: 22
- changed targets: 18
- output sha256: `8742be5ebb8c0e425ac0a63f5889340736313e2f695dc3197df488120d534d8f`

Additional changes beyond `yang_low_complexity_terminal_cleanup_v1`:

- `T0240`: trim 29-aa N-terminal hydrophobic leader on chain `A`
- `T1210`: trim 15-aa N-terminal hydrophobic leader on chain `A`
- `T1240`: trim 29-aa N-terminal hydrophobic leader on chain `A`
- `T0240O`: trim 29-aa N-terminal hydrophobic leader on chain `A`
- `T1240O`: trim 29-aa N-terminal hydrophobic leader on chain `A`

The hydrophobic-leader rule requires an N-terminal `M`, at least 80 residues
remaining after trimming, a short N-terminal candidate cut between residues 15
and 37, high hydrophobic content, enough bulky hydrophobic content, a
hydrophobic run, limited charged residues in the putative h-region, and a
small-residue cleavage-like pattern. The bulky-hydrophobic guard is included to
avoid treating poly-alanine or low-complexity prefixes as signal peptides.

## Launch Gate

Do not queue this until one of these is true:

- the conservative terminal cleanup or epitope cleanup runs improve enough to
  justify a more aggressive construct-cleanup branch, or
- the full baseline shows T0240/T1210/T1240-style hydrophobic leaders are a
  meaningful failure source.

Potential full-run spec command:

```bash
./casp16 run-spec \
  --run-id server_protenix_yang_hydrophobic_leader_cleanup_seed101 \
  --benchmark casp16_server_protein_v1 \
  --input-json strategies/yang_hydrophobic_leader_cleanup_v1/casp16_server_protein_v1/inputs.json \
  --input-manifest strategies/yang_hydrophobic_leader_cleanup_v1/casp16_server_protein_v1/manifest.tsv \
  --strategy yang_hydrophobic_leader_cleanup_v1 \
  --use-msa --use-template --use-default-params
```

Use the same fixed budget as the baseline: backend `protenix`, seed `101`,
sample `1`, and selected model policy `first_output_only`.
