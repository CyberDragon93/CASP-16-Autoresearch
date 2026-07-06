# Strategy Record

## Identity

- Run ID: `server_protenix_yang_terminal_tag_cleanup_seed101`
- Strategy name: `yang_terminal_tag_cleanup_v1`
- Parent run: `server_protenix_full_msa_template_seed101`
- Author/agent: Codex
- Date: 2026-07-06

## Hypothesis

Obvious terminal expression and purification tags can distract AF3-like
predictors, especially in assemblies. Removing only target-agnostic terminal
His/expression tags should improve or at least not regress the full server
domain/oligo benchmark relative to the unmodified full Protenix baseline.

## Changes

- Changed knobs: input JSON only, via `./casp16 strategy-inputs --strategy
  yang_terminal_tag_cleanup_v1`.
- Changed code/scripts: generated strategy input under
  `strategies/yang_terminal_tag_cleanup_v1/casp16_server_protein_v1/`.
- Unchanged fixed budget:
  - backend: `protenix`
  - seed: `101`
  - sample count: `1`
  - selected model policy: `first_output_only`
  - MSA/templates/default Protenix params: enabled, matching parent baseline

## Commands Used

```bash
./casp16 strategy-inputs --benchmark casp16_server_protein_v1 --strategy yang_terminal_tag_cleanup_v1
./casp16 run-spec \
  --run-id server_protenix_yang_terminal_tag_cleanup_seed101 \
  --benchmark casp16_server_protein_v1 \
  --input-json strategies/yang_terminal_tag_cleanup_v1/casp16_server_protein_v1/inputs.json \
  --input-manifest strategies/yang_terminal_tag_cleanup_v1/casp16_server_protein_v1/manifest.tsv \
  --strategy yang_terminal_tag_cleanup_v1 \
  --use-msa --use-template --use-default-params
```

## Result Summary

- Rank status: pending, not launched while parent baseline is running.
- Mean score: unavailable.
- Eligible targets: fixed `casp16_server_protein_v1` target set.
- OK targets: unavailable.
- Missing targets: unavailable.
- Failed targets: unavailable.
- Metric unavailable targets: expected for oligo QSglob until scorer exists.
- Artifact path: `runs/server_protenix_yang_terminal_tag_cleanup_seed101/`.

## Failure Notes

No prediction has been launched yet. `run-next` is guarded so the pending run is
not started while another `casp16_server_protein_v1` run is still marked
`running`.

## No-Oracle Checklist

- [x] Did not inspect native/reference structures before prediction.
- [x] Did not use official score tables for target-specific tuning.
- [x] Did not use previous target scores for target-specific parameter choices.
- [x] Did not replace structure metrics with confidence diagnostics.
- [x] Regenerated inputs only through `./casp16 strategy-inputs`; results are
      not yet scored.

## Next Action

After `server_protenix_full_msa_template_seed101` finishes, score the baseline,
then run this queued cleanup strategy as the first full optimized-input
comparison.
