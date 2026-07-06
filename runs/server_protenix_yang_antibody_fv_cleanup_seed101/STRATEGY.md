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

- Rank status: pending, queued behind `server_protenix_yang_terminal_tag_cleanup_seed101`.
- Mean score: unavailable.
- Eligible targets: fixed `casp16_server_protein_v1` target set.
- OK targets: unavailable.
- Missing targets: unavailable.
- Failed targets: unavailable.
- Metric unavailable targets: expected for oligo QSglob until scorer exists.
- Artifact path: `runs/server_protenix_yang_antibody_fv_cleanup_seed101/`.

## Failure Notes

No prediction has been launched yet. `run-next` is guarded so this pending run
cannot start while `server_protenix_full_msa_template_seed101` is still marked
`running`; it is ordered after the lower-risk terminal-tag cleanup run.

## No-Oracle Checklist

- [x] Did not inspect native/reference structures before prediction.
- [x] Did not use official score tables for target-specific tuning.
- [x] Did not use previous target scores for target-specific parameter choices.
- [x] Did not replace structure metrics with confidence diagnostics.
- [x] Regenerated inputs only through `./casp16 strategy-inputs`; results are
      not yet scored.

## Next Action

Score the full Protenix baseline when it finishes, run the queued terminal-tag
cleanup ablation, then use this run as the first full-set antibody construct
comparison.
