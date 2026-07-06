# Strategy Record

Run ID: `server_v2_attack_oligo_recovery_nofail_protenix5_seed101_105`

Strategy name: `yang_oligo_sequence_stoich_low_complexity_large_fallback_v1_server_attack_protenix5`

Parent run: `server_v2_protenix_yang_oligo_sequence_stoich_low_complexity_large_fallback_seed101`

Benchmark: `casp16_server_protein_v2_aliasfix`

## Hypothesis

The first realistic v2 attack attempt should spend the five-candidate
`protenix5` budget on the strongest runnable input stack, not on the older
nofail stack that lacks protein-oligo sequence recovery. This candidate fixes
the `H0220/H1220/H2220` input-modality gap, keeps exact token-safe
stoichiometry, removes remaining token-limit hard failures, and uses the
predeclared confidence-only selector.

## Changed Knobs

- Input artifact:
  `strategies/yang_oligo_sequence_stoich_low_complexity_large_fallback_v1/casp16_server_protein_v2_aliasfix/inputs.json`
- Seeds: `101,102,103,104,105`
- Sample per seed: `1`
- Candidate count: `5`
- Selected model policy: `protenix_confidence_v1`

## Fixed Budget

- backend: `protenix`
- model: `protenix-v2`
- MSA/templates/default params/cache/fusion/TF32: enabled
- quality scoring remains official-compatible: domain `GDT_TS`, oligo
  `QSglob`
- confidence is used only for predeclared candidate selection, never as a
  quality metric

## Commands

```bash
./casp16 run-spec \
  --run-id server_v2_attack_oligo_recovery_nofail_protenix5_seed101_105 \
  --benchmark casp16_server_protein_v2_aliasfix \
  --input-json strategies/yang_oligo_sequence_stoich_low_complexity_large_fallback_v1/casp16_server_protein_v2_aliasfix/inputs.json \
  --input-manifest strategies/yang_oligo_sequence_stoich_low_complexity_large_fallback_v1/casp16_server_protein_v2_aliasfix/manifest.tsv \
  --strategy yang_oligo_sequence_stoich_low_complexity_large_fallback_v1_server_attack_protenix5 \
  --seeds 101,102,103,104,105 \
  --sample 1 \
  --selected-model-policy protenix_confidence_v1 \
  --use-msa --use-template --use-default-params \
  --enable-cache --enable-fusion
```

## No Oracle Use

- Native/reference structures are forbidden during prediction and selection.
- Official score tables are forbidden during prediction and selection.
- Previous `target_scores.csv` rows are forbidden for target-specific
  parameter choices.
- The selector may read only confidence JSON files produced by this run.

## Launch Gate

Launch only after the active `server_attack_protenix_terminal_tag_seed101_105`
state is resolved and queue supersession is explicit. Compare this only against
other `server_attack` rows and official server groups with the candidate budget
shown.
