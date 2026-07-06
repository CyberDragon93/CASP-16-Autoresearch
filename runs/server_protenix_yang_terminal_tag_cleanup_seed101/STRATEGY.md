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
  - MSA/templates/default Protenix params/cache/fusion/TF32: enabled, matching
    parent baseline

## Commands Used

```bash
./casp16 strategy-inputs --benchmark casp16_server_protein_v1 --strategy yang_terminal_tag_cleanup_v1
./casp16 run-spec \
  --run-id server_protenix_yang_terminal_tag_cleanup_seed101 \
  --benchmark casp16_server_protein_v1 \
  --input-json strategies/yang_terminal_tag_cleanup_v1/casp16_server_protein_v1/inputs.json \
  --input-manifest strategies/yang_terminal_tag_cleanup_v1/casp16_server_protein_v1/manifest.tsv \
  --strategy yang_terminal_tag_cleanup_v1 \
  --use-msa --use-template --use-default-params \
  --enable-cache --enable-fusion
```

## Result Summary

- Rank status: ranked on `protein_domain`; unranked on `protein_oligo` because
  QSglob is unavailable.
- Mean score: domain `0.066908`, versus parent baseline `0.063962`.
- Eligible targets: fixed `casp16_server_protein_v1` target set.
- OK targets: 15 domain rows scored.
- Missing targets: 30 domain rows missing prediction in the fixed official
  domain set.
- Failed targets: 26 domain rows missing local reference mapping; 8 Protenix
  inference jobs failed with `n_token > 2560`.
- Metric unavailable targets: expected for oligo QSglob until scorer exists.
- Artifact path: `runs/server_protenix_yang_terminal_tag_cleanup_seed101/`.

## Failure Notes

The run generated 98/106 CIFs. The same 8 jobs as the baseline failed the
Protenix token guard: `T1295`, `H0217`, `H0258`, `H0272`, `H1217`, `H1258`,
`H1272`, and `T1295O`.

Largest positive domain deltas versus baseline: `T1234` `+0.1122`, `T1298`
`+0.0863`, and `T1210` `+0.0519`. Main regressions: `T0234`, `T1249V1`, and
`T1299`. The net signal is positive but far below server-winner scale.

## No-Oracle Checklist

- [x] Did not inspect native/reference structures before prediction.
- [x] Did not use official score tables for target-specific tuning.
- [x] Did not use previous target scores for target-specific parameter choices.
- [x] Did not replace structure metrics with confidence diagnostics.
- [x] Regenerated inputs only through `./casp16 strategy-inputs`.
- [x] Scored only after predictions completed.

## Next Action

Run `server_protenix_yang_oversize_domain_monomer_fallback_seed101` next to
recover the known `T1295` server-domain token-limit zero before adding
multi-seed attack-budget runs.
