# Strategy Record

## Identity

- Run ID: `server_protenix_yang_antibody_fv_cleanup_seed101`
- Strategy name: `yang_antibody_fv_cleanup_v1`
- Parent run: `server_protenix_full_msa_template_seed101`
- Author/agent: Codex
- Date: 2026-07-06

## Hypothesis

Antibody-antigen server targets may be hurt by modeling full antibody constant
regions when the relevant complex behavior is driven by the Fv region. A
full-set, sequence-only constant-region cleanup should improve antibody-complex
assembly without changing the benchmark target set or using target scores.

## Changes

- Changed knobs: input JSON only, via `./casp16 strategy-inputs --strategy
  yang_antibody_fv_cleanup_v1`.
- Changed code/scripts: generated strategy input under
  `strategies/yang_antibody_fv_cleanup_v1/casp16_server_protein_v1/`.
- Unchanged fixed budget:
  - backend: `protenix`
  - seed: `101`
  - sample count: `1`
  - selected model policy: `first_output_only`
  - MSA/templates/default Protenix params/cache/fusion/TF32: enabled, matching
    parent baseline and queued optimized-input runs

## Commands Used

```bash
./casp16 strategy-inputs --benchmark casp16_server_protein_v1 --strategy yang_antibody_fv_cleanup_v1
./casp16 run-spec \
  --run-id server_protenix_yang_antibody_fv_cleanup_seed101 \
  --benchmark casp16_server_protein_v1 \
  --input-json strategies/yang_antibody_fv_cleanup_v1/casp16_server_protein_v1/inputs.json \
  --input-manifest strategies/yang_antibody_fv_cleanup_v1/casp16_server_protein_v1/manifest.tsv \
  --strategy yang_antibody_fv_cleanup_v1 \
  --use-msa --use-template --use-default-params \
  --enable-cache --enable-fusion
```

## Result Summary

- Rank status: ranked on `protein_domain`; unranked on `protein_oligo` because
  QSglob is unavailable.
- Mean score: domain `0.060677`.
- Eligible targets: 71 protein-domain targets and 104 protein-oligo targets.
- OK targets: domain 15; oligo 0 until QSglob exists.
- Missing targets: domain 30; oligo 47.
- Failed targets: domain 26; oligo 30.
- Metric unavailable targets: oligo 27 due to missing QSglob scorer.
- Artifact path: `runs/server_protenix_yang_antibody_fv_cleanup_seed101/`.

## Failure Notes

The run completed the full 106-job server benchmark with 98 CIF files and
returncode 0. The same 8 Protenix jobs as baseline hit the `n_token > 2560`
guard: `T1295`, `H0217`, `H0258`, `H0272`, `H1217`, `H1258`, `H1272`, and
`T1295O`.

The domain result is negative: `0.060677`, below baseline `0.063962` and below
terminal-tag cleanup `0.066908`. Major regressions were `T0234`, `T1234`, and
`T1298`. The antibody oligo targets `H0222`, `H0223`, `H0225`, `H1222`,
`H1223`, and `H1225` produced predictions but remain `metric_unavailable`
because QSglob is not installed.

## No-Oracle Checklist

- [x] Did not inspect native/reference structures before prediction.
- [x] Did not use official score tables for target-specific tuning.
- [x] Did not use previous target scores for target-specific parameter choices.
- [x] Did not replace structure metrics with confidence diagnostics.
- [x] Regenerated inputs only through `./casp16 strategy-inputs`; scoring used
      the locked `./casp16 score` and `./casp16 leaderboard` workflow.

## Next Action

Do not promote antibody-Fv cleanup to a multi-seed attack budget. Install or
register QSglob first if antibody-complex strategies are the question; for the
ranked domain track, keep terminal-tag cleanup as the current best local
`dev_fixed` run.
