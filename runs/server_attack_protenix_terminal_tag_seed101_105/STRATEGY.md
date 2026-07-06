# Strategy Record: server_attack_protenix_terminal_tag_seed101_105

## Run

- Run ID: `server_attack_protenix_terminal_tag_seed101_105`
- Strategy name: `yang_terminal_tag_cleanup_v1_server_attack`
- Parent run: `server_protenix_yang_terminal_tag_cleanup_seed101`
- Benchmark: `casp16_server_protein_v1`
- Budget tier: `server_attack`

## Hypothesis

The current best `dev_fixed` strategy is terminal tag cleanup at domain mean
`0.066908`. A realistic CASP server-style run should not assume a single seed:
generate five fixed Protenix candidates per target and choose one with a
predeclared confidence-only selector before scoring. This tests whether
sampling plus non-oracle model selection closes any of the gap while preserving
the same input transform.

## Changed Knobs

- Seeds: `101,102,103,104,105`
- Sample per seed: `1`
- Selected model policy: `protenix_confidence_v1`
- Selection signals: same-run Protenix confidence JSON only

## Unchanged Fixed Budget

- Backend: `protenix`
- Model: `protenix-v2`
- Input strategy: `yang_terminal_tag_cleanup_v1`
- MSA: enabled
- Template: enabled
- Default params: enabled
- Cache/fusion/TF32: enabled
- dtype: `bf16`

## Commands

```bash
./casp16 run-spec \
  --run-id server_attack_protenix_terminal_tag_seed101_105 \
  --benchmark casp16_server_protein_v1 \
  --input-json strategies/yang_terminal_tag_cleanup_v1/casp16_server_protein_v1/inputs.json \
  --input-manifest strategies/yang_terminal_tag_cleanup_v1/casp16_server_protein_v1/manifest.tsv \
  --strategy yang_terminal_tag_cleanup_v1_server_attack \
  --seeds 101,102,103,104,105 \
  --sample 1 \
  --selected-model-policy protenix_confidence_v1 \
  --use-msa --use-template --use-default-params \
  --enable-cache --enable-fusion --enable-tf32
```

```bash
ssh login1 'cd /scratch/10992/liaorunlong93/casp16-leaderboard && sbatch runs/server_attack_protenix_terminal_tag_seed101_105/run_gh200.slurm'
```

After completion:

```bash
./casp16 score --benchmark casp16_server_protein_v1
./casp16 leaderboard --benchmark casp16_server_protein_v1
```

## Result Summary

- Run status: submitted as Slurm job `810719`; initial state
  `PENDING (Priority)`.
- Rank status: pending until predictions finish and scoring is regenerated.
- Expected candidate budget: 5 candidates per target.
- Expected target jobs: 106 Protenix jobs from the server benchmark input set.
- Expected wall time: up to one GH200 48-hour allocation; previous single-seed
  full-set runs took about 3 hours, but multi-seed runtime may be higher and
  MSA/template cache behavior is target-dependent.

## No Oracle Checklist

- [x] No native/reference structures are read during prediction.
- [x] No official score tables are read during prediction.
- [x] No previous `target_scores.csv` rows are used for per-target tuning.
- [x] No manual per-target candidate choice after seeing scores.
- [x] Confidence is used only through the predeclared
      `protenix_confidence_v1` selector.
