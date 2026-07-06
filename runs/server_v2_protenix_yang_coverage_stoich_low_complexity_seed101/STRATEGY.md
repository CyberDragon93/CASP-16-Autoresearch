# Strategy Record

Run ID: `server_v2_protenix_yang_coverage_stoich_low_complexity_seed101`

Strategy name: `yang_coverage_stoich_low_complexity_v1`

Parent run: `server_v2_protenix_yang_coverage_stoich_seed101`

Benchmark: `casp16_server_protein_v2_aliasfix`

## Hypothesis

Yang-style optimized inputs may benefit from conservative terminal construct
cleanup after alias-fixed coverage and token-safe stoichiometry are already in
place. The highest-value changes are expected on large/complex targets where
terminal low-complexity or expression-tag segments can waste Protenix tokens or
distort interfaces.

## Changed Knobs

- Base input:
  `strategies/yang_oligo_stoichiometry_token_safe_v1/casp16_server_protein_v2_aliasfix/inputs.json`
- Added low-complexity terminal cleanup with sequence-only rules.
- Changed 27 protein sequences across 21 targets.

## Fixed Budget

- backend: `protenix`
- model: `protenix-v2`
- seed: `101`
- sample: `1`
- selected model policy: `first_output_only`
- MSA/templates/default params/cache/fusion/TF32: enabled

## Commands

```bash
./casp16 strategy-inputs \
  --benchmark casp16_server_protein_v2_aliasfix \
  --strategy yang_low_complexity_terminal_cleanup_v1 \
  --input-json strategies/yang_oligo_stoichiometry_token_safe_v1/casp16_server_protein_v2_aliasfix/inputs.json \
  --output-json strategies/yang_coverage_stoich_low_complexity_v1/casp16_server_protein_v2_aliasfix/inputs.json \
  --manifest strategies/yang_coverage_stoich_low_complexity_v1/casp16_server_protein_v2_aliasfix/manifest.tsv

./casp16 run-spec \
  --run-id server_v2_protenix_yang_coverage_stoich_low_complexity_seed101 \
  --benchmark casp16_server_protein_v2_aliasfix \
  --input-json strategies/yang_coverage_stoich_low_complexity_v1/casp16_server_protein_v2_aliasfix/inputs.json \
  --input-manifest strategies/yang_coverage_stoich_low_complexity_v1/casp16_server_protein_v2_aliasfix/manifest.tsv \
  --strategy yang_coverage_stoich_low_complexity_v1 \
  --use-msa --use-template --use-default-params \
  --enable-cache --enable-fusion
```

## No Oracle Use

- Native/reference structures were not read during strategy generation.
- Official score tables were not used for target-specific parameter choices.
- Previous target-level local scores were not used to select edited targets.
- Confidence files are not used as quality scores in this `dev_fixed` run.

## Launch Gate

Run after `server_v2_protenix_yang_coverage_stoich_seed101` is scored. Treat
this as a v2 `dev_fixed` ablation, not as an attack-budget result.
