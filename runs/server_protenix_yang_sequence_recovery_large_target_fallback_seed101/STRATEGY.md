# Strategy Record: server_protenix_yang_sequence_recovery_large_target_fallback_seed101

## Run

- Run ID: `server_protenix_yang_sequence_recovery_large_target_fallback_seed101`
- Strategy name: `yang_sequence_recovery_large_target_fallback_v1`
- Parent run: `server_protenix_yang_terminal_tag_cleanup_seed101`
- Benchmark: `casp16_server_protein_v1`
- Budget tier: `dev_fixed`

## Hypothesis

The next single-seed coverage win should combine the two hard-zero fixes before
spending more attack compute. Sequence recovery repairs missing or misparsed
protein-domain inputs, while large-target fallback prevents Protenix
`n_token > 2560` failures after those recovered inputs are added.

## Changed Knobs

- Base input: `yang_terminal_tag_cleanup_v1`.
- Recover protein-domain jobs from official parsed sequence aliases.
- Apply large-target epitope cleanup and original-order chain/copy prefix
  fallback after recovery.
- Keep every optimized Protenix job under 2560 tokens.

## Unchanged Fixed Budget

- Backend: `protenix`
- Model: `protenix-v2`
- Seed: `101`
- Sample: `1`
- Selected model policy: `first_output_only`
- MSA: enabled
- Template: enabled
- Default params: enabled
- Cache/fusion/TF32: enabled
- dtype: `bf16`

## Commands

```bash
./casp16 strategy-inputs \
  --benchmark casp16_server_protein_v1 \
  --strategy yang_sequence_recovery_large_target_fallback_v1 \
  --input-json strategies/yang_terminal_tag_cleanup_v1/casp16_server_protein_v1/inputs.json \
  --output-json strategies/yang_sequence_recovery_large_target_fallback_v1/casp16_server_protein_v1/inputs.json \
  --manifest strategies/yang_sequence_recovery_large_target_fallback_v1/casp16_server_protein_v1/manifest.tsv
```

```bash
./casp16 run-spec \
  --run-id server_protenix_yang_sequence_recovery_large_target_fallback_seed101 \
  --benchmark casp16_server_protein_v1 \
  --input-json strategies/yang_sequence_recovery_large_target_fallback_v1/casp16_server_protein_v1/inputs.json \
  --input-manifest strategies/yang_sequence_recovery_large_target_fallback_v1/casp16_server_protein_v1/manifest.tsv \
  --strategy yang_sequence_recovery_large_target_fallback_v1 \
  --use-msa --use-template --use-default-params \
  --enable-cache --enable-fusion --enable-tf32
```

After the active attack and component coverage jobs complete:

```bash
ssh login1 'cd /scratch/10992/liaorunlong93/casp16-leaderboard && sbatch runs/server_protenix_yang_sequence_recovery_large_target_fallback_seed101/run_gh200.slurm'
```

## Result Summary

- Run status: pending; not submitted while earlier pending jobs exist.
- Rank status: pending until predictions finish and scoring is regenerated.
- Expected target jobs: 135.
- Changed targets: 40 unique targets.
- Sequence recovery: 32 targets.
- Large-target fallback: 10 targets.
- Largest optimized job: 2535 tokens.

## No Oracle Checklist

- [x] No native/reference structures are read during prediction.
- [x] No official score tables are read during prediction.
- [x] No previous `target_scores.csv` rows are used for per-target tuning.
- [x] Sequence recovery uses benchmark target metadata and official parsed
  sequences.
- [x] Token-budget fallback is predeclared and independent of target scores.
