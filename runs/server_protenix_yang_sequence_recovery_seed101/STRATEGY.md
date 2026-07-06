# Strategy Record: server_protenix_yang_sequence_recovery_seed101

## Run

- Run ID: `server_protenix_yang_sequence_recovery_seed101`
- Strategy name: `yang_sequence_recovery_v1`
- Parent run: `server_protenix_yang_terminal_tag_cleanup_seed101`
- Benchmark: `casp16_server_protein_v1`
- Budget tier: `dev_fixed`

## Hypothesis

Several server-domain hard zeros are local input coverage failures rather than
model failures. The official sequence archive contains protein-like sequences
that were skipped or emitted as `dnaSequence`/`rnaSequence`. Recovering those
as `proteinChain` on top of the current best terminal-tag cleanup should add
rankable predictions for targets such as `T1212`, `T1239V2`, and `T2280`, and
may correct the existing `T1239V1` input.

## Changed Knobs

- Base input: `yang_terminal_tag_cleanup_v1`.
- Recover missing protein-domain jobs from official parsed sequence aliases.
- Replace non-protein Protenix entities for protein-domain targets when the
  raw sequence is protein-like by alphabet/header.
- Add conservative aliases: `V2 -> V1` and `T2xxx -> T1xxx/T0xxx`.

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
  --strategy yang_sequence_recovery_v1 \
  --input-json strategies/yang_terminal_tag_cleanup_v1/casp16_server_protein_v1/inputs.json \
  --output-json strategies/yang_sequence_recovery_v1/casp16_server_protein_v1/inputs.json \
  --manifest strategies/yang_sequence_recovery_v1/casp16_server_protein_v1/manifest.tsv
```

```bash
./casp16 run-spec \
  --run-id server_protenix_yang_sequence_recovery_seed101 \
  --benchmark casp16_server_protein_v1 \
  --input-json strategies/yang_sequence_recovery_v1/casp16_server_protein_v1/inputs.json \
  --input-manifest strategies/yang_sequence_recovery_v1/casp16_server_protein_v1/manifest.tsv \
  --strategy yang_sequence_recovery_v1 \
  --use-msa --use-template --use-default-params \
  --enable-cache --enable-fusion --enable-tf32
```

After the active attack and large-target fallback jobs complete:

```bash
ssh login1 'cd /scratch/10992/liaorunlong93/casp16-leaderboard && sbatch runs/server_protenix_yang_sequence_recovery_seed101/run_gh200.slurm'
```

## Result Summary

- Run status: pending; not submitted while earlier pending jobs exist.
- Rank status: pending until predictions finish and scoring is regenerated.
- Expected target jobs: 135.
- High-value recoveries: `T1212`, `T1239V1`, `T1239V2`, `T2280`.

## No Oracle Checklist

- [x] No native/reference structures are read during prediction.
- [x] No official score tables are read during prediction.
- [x] No previous `target_scores.csv` rows are used for per-target tuning.
- [x] Recovery uses benchmark target metadata and official parsed sequences.
- [x] Source aliases and record IDs are recorded before scoring.

