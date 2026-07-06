# Strategy Record

Run ID: `server_v2_protenix_yang_coverage_stoich_low_complexity_large_fallback_seed101`

Strategy name: `yang_coverage_stoich_low_complexity_large_fallback_v1`

Parent run: `server_v2_protenix_yang_coverage_stoich_low_complexity_seed101`

Benchmark: `casp16_server_protein_v2_aliasfix`

## Hypothesis

The v2 coverage/stoichiometry plus low-complexity cleanup candidate still has
11 jobs above Protenix's 2560-token limit. Those targets are guaranteed
inference failures under the current backend, so a predeclared chain-prefix
fallback may improve fixed-set coverage before any larger multi-seed attack
budget is spent.

This is a pragmatic coverage-recovery ablation. It may lose assembly
information on cropped oligo targets, so its oligo result must be interpreted
with QSglob mapping and coverage diagnostics.

## Changed Knobs

- Base input:
  `strategies/yang_coverage_stoich_low_complexity_v1/casp16_server_protein_v2_aliasfix/inputs.json`
- Applied target-agnostic large-target split/fallback to jobs still above
  2560 tokens.
- Changed 11 targets and reduced all generated jobs below the token limit.

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
  --strategy yang_large_target_split_or_fallback_v1 \
  --input-json strategies/yang_coverage_stoich_low_complexity_v1/casp16_server_protein_v2_aliasfix/inputs.json \
  --output-json strategies/yang_coverage_stoich_low_complexity_large_fallback_v1/casp16_server_protein_v2_aliasfix/inputs.json \
  --manifest strategies/yang_coverage_stoich_low_complexity_large_fallback_v1/casp16_server_protein_v2_aliasfix/manifest.tsv

./casp16 run-spec \
  --run-id server_v2_protenix_yang_coverage_stoich_low_complexity_large_fallback_seed101 \
  --benchmark casp16_server_protein_v2_aliasfix \
  --input-json strategies/yang_coverage_stoich_low_complexity_large_fallback_v1/casp16_server_protein_v2_aliasfix/inputs.json \
  --input-manifest strategies/yang_coverage_stoich_low_complexity_large_fallback_v1/casp16_server_protein_v2_aliasfix/manifest.tsv \
  --strategy yang_coverage_stoich_low_complexity_large_fallback_v1 \
  --use-msa --use-template --use-default-params \
  --enable-cache --enable-fusion
```

## No Oracle Use

- Native/reference structures were not read during strategy generation.
- Official score tables were not used for target-specific parameter choices.
- Previous target-level local scores were not used to select edited targets.
- Confidence files are not used as quality scores in this `dev_fixed` run.

## Launch Gate

Run after `server_v2_protenix_yang_coverage_stoich_seed101` and
`server_v2_protenix_yang_coverage_stoich_low_complexity_seed101` are scored.
Treat this as a v2 `dev_fixed` coverage-recovery ablation, not as an
attack-budget result.
