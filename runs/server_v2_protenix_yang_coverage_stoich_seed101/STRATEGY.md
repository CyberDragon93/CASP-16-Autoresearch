# Strategy Record

- Run ID: `server_v2_protenix_yang_coverage_stoich_seed101`
- Benchmark: `casp16_server_protein_v2_aliasfix`
- Strategy: `yang_oligo_stoichiometry_token_safe_v1`
- Parent run: none on v2
- Budget tier: `dev_fixed`
- Backend: `protenix`
- Seed: `101`
- Sample: `1`
- Selected model policy: `first_output_only`

## Hypothesis

The alias-fixed server benchmark removes many artificial v1 reference/input
gaps. Running the current stacked coverage plus token-safe stoichiometry input
on v2 gives the first useful single-seed baseline for future winner-comparison
attack budgets.

## Changed Knobs

- Benchmark changes from `casp16_server_protein_v1` to
  `casp16_server_protein_v2_aliasfix`.
- Inputs use the target-agnostic `yang_oligo_stoichiometry_token_safe_v1`
  transform generated from the v2 benchmark inputs.

## Fixed Budget

- MSA/templates/default params/cache/fusion/TF32 are enabled.
- Seed/sample stay fixed at `101`/`1`.
- No confidence-based or reference-based model selection is used.

## Commands

```bash
./casp16 strategy-inputs --benchmark casp16_server_protein_v2_aliasfix --strategy yang_oligo_stoichiometry_token_safe_v1
./casp16 run-spec --run-id server_v2_protenix_yang_coverage_stoich_seed101 --benchmark casp16_server_protein_v2_aliasfix --input-json strategies/yang_oligo_stoichiometry_token_safe_v1/casp16_server_protein_v2_aliasfix/inputs.json --input-manifest strategies/yang_oligo_stoichiometry_token_safe_v1/casp16_server_protein_v2_aliasfix/manifest.tsv --strategy yang_oligo_stoichiometry_token_safe_v1 --use-msa --use-template --use-default-params --enable-cache --enable-fusion
```

## No Oracle Checklist

- Native/reference structures were not used for prediction-time decisions.
- Official scores were not used for per-target tuning.
- Previous target scores were not used for per-target parameter selection.
- Confidence is not used as quality score in this `dev_fixed` run.
