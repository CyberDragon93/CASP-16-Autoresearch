# Strategy Record

Run ID: `server_v2_protenix_yang_oligo_sequence_stoich_low_complexity_large_fallback_seed101`

Strategy name: `yang_oligo_sequence_stoich_low_complexity_large_fallback_v1`

Parent run: `server_v2_protenix_yang_coverage_stoich_low_complexity_large_fallback_seed101`

Benchmark: `casp16_server_protein_v2_aliasfix`

## Hypothesis

The previous v2 no-over-token stack fixed token-limit failures but still missed
a protein-oligo sequence-modality problem: several `H*220`-style jobs were
locally represented as nucleic-acid inputs or missing even though official
sequence aliases contain protein-like records. Recovering those protein inputs
before low-complexity cleanup and large-target fallback should improve oligo
coverage without reintroducing Protenix hard failures.

## Changed Knobs

- Base input:
  `strategies/yang_protein_oligo_sequence_stoich_token_safe_v1/casp16_server_protein_v2_aliasfix/inputs.json`
- Applied low-complexity terminal cleanup.
- Applied large-target fallback to every remaining job above 2560 tokens.
- Final generated input has 165 jobs, max 2535 tokens, and 0 jobs above the
  Protenix token limit.

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
  --input-json strategies/yang_protein_oligo_sequence_stoich_token_safe_v1/casp16_server_protein_v2_aliasfix/inputs.json \
  --output-json strategies/yang_oligo_sequence_stoich_low_complexity_v1/casp16_server_protein_v2_aliasfix/inputs.json \
  --manifest strategies/yang_oligo_sequence_stoich_low_complexity_v1/casp16_server_protein_v2_aliasfix/manifest.tsv

./casp16 strategy-inputs \
  --benchmark casp16_server_protein_v2_aliasfix \
  --strategy yang_large_target_split_or_fallback_v1 \
  --input-json strategies/yang_oligo_sequence_stoich_low_complexity_v1/casp16_server_protein_v2_aliasfix/inputs.json \
  --output-json strategies/yang_oligo_sequence_stoich_low_complexity_large_fallback_v1/casp16_server_protein_v2_aliasfix/inputs.json \
  --manifest strategies/yang_oligo_sequence_stoich_low_complexity_large_fallback_v1/casp16_server_protein_v2_aliasfix/manifest.tsv

./casp16 run-spec \
  --run-id server_v2_protenix_yang_oligo_sequence_stoich_low_complexity_large_fallback_seed101 \
  --benchmark casp16_server_protein_v2_aliasfix \
  --input-json strategies/yang_oligo_sequence_stoich_low_complexity_large_fallback_v1/casp16_server_protein_v2_aliasfix/inputs.json \
  --input-manifest strategies/yang_oligo_sequence_stoich_low_complexity_large_fallback_v1/casp16_server_protein_v2_aliasfix/manifest.tsv \
  --strategy yang_oligo_sequence_stoich_low_complexity_large_fallback_v1 \
  --use-msa --use-template --use-default-params \
  --enable-cache --enable-fusion
```

## No Oracle Use

- Native/reference structures were not read during strategy generation.
- Official score tables were not used for target-specific choices.
- Previous target-level local scores were not used to choose edited targets.
- Confidence files are not used as quality scores in this `dev_fixed` run.

## Launch Gate

Run after the active v1 attack and v2 baseline state is understood. Prefer this
candidate over the older no-over-token v2 stack if the goal is to spend compute
on the best current input repair stack.
