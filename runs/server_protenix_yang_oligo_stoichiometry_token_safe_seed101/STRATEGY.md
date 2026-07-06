# Strategy Record: server_protenix_yang_oligo_stoichiometry_token_safe_seed101

## Run

- Run ID: `server_protenix_yang_oligo_stoichiometry_token_safe_seed101`
- Strategy name: `yang_oligo_stoichiometry_token_safe_v1`
- Parent input: `yang_sequence_recovery_large_target_fallback_v1`
- Benchmark: `casp16_server_protein_v1`
- Budget tier: `dev_fixed`

## Hypothesis

Several protein-oligo jobs in the server benchmark collapsed to one copy per
entity even though the official CASP16 target list has explicit stoichiometry.
Restoring only the under-budget exact stoichiometries should improve assembly
realism without reintroducing Protenix `n_token > 2560` failures.

## Changed Knobs

- Base input: stacked sequence recovery plus large-target fallback.
- Restore official parsed `Oligo.State` for token-safe protein-only oligo jobs.
- Leave oversize or already reduced assemblies unchanged and record skip
  reasons.
- Changed targets: `H1232`, `H1233`, `H1236`, `H1244`, `H1267`.

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
  --strategy yang_oligo_stoichiometry_token_safe_v1 \
  --input-json strategies/yang_sequence_recovery_large_target_fallback_v1/casp16_server_protein_v1/inputs.json \
  --output-json strategies/yang_oligo_stoichiometry_token_safe_v1/casp16_server_protein_v1/inputs.json \
  --manifest strategies/yang_oligo_stoichiometry_token_safe_v1/casp16_server_protein_v1/manifest.tsv
```

```bash
./casp16 run-spec \
  --run-id server_protenix_yang_oligo_stoichiometry_token_safe_seed101 \
  --benchmark casp16_server_protein_v1 \
  --input-json strategies/yang_oligo_stoichiometry_token_safe_v1/casp16_server_protein_v1/inputs.json \
  --input-manifest strategies/yang_oligo_stoichiometry_token_safe_v1/casp16_server_protein_v1/manifest.tsv \
  --strategy yang_oligo_stoichiometry_token_safe_v1 \
  --use-msa --use-template --use-default-params \
  --enable-cache --enable-fusion --enable-tf32
```

After the active pending jobs complete:

```bash
ssh login1 'cd /scratch/10992/liaorunlong93/casp16-leaderboard && sbatch runs/server_protenix_yang_oligo_stoichiometry_token_safe_seed101/run_gh200.slurm'
```

## Result Summary

- Run status: pending; not submitted while earlier pending jobs exist.
- Rank status: pending until predictions finish and scoring is regenerated.
- Expected target jobs: 135.
- Changed targets: 5.
- Largest optimized job: 2535 tokens.
- Oligo scoring remains diagnostic until QSglob is available.

## No Oracle Checklist

- [x] No native/reference structures are read during prediction.
- [x] No official score tables are read during prediction.
- [x] No previous `target_scores.csv` rows are used for per-target tuning.
- [x] Stoichiometry comes from the official target list, not score feedback.
- [x] Oversize assemblies are skipped rather than forced into a broken run.
