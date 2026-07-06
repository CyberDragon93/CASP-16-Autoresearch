# Strategy Record

## Identity

- Run ID: `server_protenix_yang_oversize_domain_monomer_fallback_seed101`
- Strategy name: `yang_oversize_domain_monomer_fallback_v1`
- Parent run: `server_protenix_full_msa_template_seed101`
- Author/agent: Codex
- Date: 2026-07-06

## Hypothesis

The full Protenix baseline lost `T1295` on the server-domain track before
prediction because the benchmark input expanded one protein entity to `A8` and
exceeded Protenix's token guard. For a protein-domain run, predicting one
representative chain is a conservative coverage recovery that can turn a
forced zero into a scorable model without changing references or score rules.

## Changes

- Changed knobs: input JSON only, via `./casp16 strategy-inputs --strategy
  yang_oversize_domain_monomer_fallback_v1`.
- Changed code/scripts: added a strategy-input transform that only applies to
  protein-domain, protein-only, single-entity, multi-copy jobs whose expanded
  protein length exceeds 2560 tokens.
- Unchanged fixed budget:
  - backend: `protenix`
  - seed: `101`
  - sample count: `1`
  - selected model policy: `first_output_only`
  - MSA/templates/default Protenix params/cache/fusion/TF32: enabled, matching
    parent baseline and queued optimized-input runs

## Commands Used

```bash
./casp16 strategy-inputs --benchmark casp16_server_protein_v1 --strategy yang_oversize_domain_monomer_fallback_v1
./casp16 run-spec \
  --run-id server_protenix_yang_oversize_domain_monomer_fallback_seed101 \
  --benchmark casp16_server_protein_v1 \
  --input-json strategies/yang_oversize_domain_monomer_fallback_v1/casp16_server_protein_v1/inputs.json \
  --input-manifest strategies/yang_oversize_domain_monomer_fallback_v1/casp16_server_protein_v1/manifest.tsv \
  --strategy yang_oversize_domain_monomer_fallback_v1 \
  --use-msa --use-template --use-default-params \
  --enable-cache --enable-fusion
```

## Result Summary

- Rank status: ranked on the protein-domain track; unranked on protein-oligo
  until a `QSglob` scorer exists.
- Mean score: protein-domain `0.065114`, rank 2 among current local ranked
  runs. This is above the full Protenix baseline `0.063962` but below
  `server_protenix_yang_terminal_tag_cleanup_seed101` at `0.066908`.
- Eligible targets: fixed `casp16_server_protein_v1` target set.
- OK targets: 15/71 protein-domain targets.
- Missing targets: 29/71 protein-domain targets.
- Failed or missing-reference targets: 27/71 protein-domain targets.
- Metric unavailable targets: expected for oligo QSglob until scorer exists.
- Artifact path: `runs/server_protenix_yang_oversize_domain_monomer_fallback_seed101/`.

## Failure Notes

The full run produced 99/106 CIF files, one more than the baseline and
terminal-tag cleanup runs. `T1295` was rescued at inference time: it ran as one
representative 469-residue chain instead of the original `A8` 3752-token job.

The rescued `T1295` prediction did not improve the current ranked score because
the local server benchmark still lacks a reference mapping for that target, so
it remains `missing_reference` and scores `0`. `T1295O` and the six large
`H*` complex targets still failed the Protenix `n_token > 2560` guard, as
expected, because this strategy intentionally touched only the safe
single-entity protein-domain case.

This is a useful coverage fix but not a winner-level score improvement. It
argues for better reference/domain mapping and a separate predeclared
large-complex split policy before spending a realistic multi-seed attack
budget.

## No-Oracle Checklist

- [x] Did not inspect native/reference structures before prediction.
- [x] Did not use official score tables for target-specific tuning.
- [x] Did not use previous target scores for target-specific parameter choices.
- [x] Did not replace structure metrics with confidence diagnostics.
- [x] Regenerated inputs only through `./casp16 strategy-inputs`; results are
      scored only through `./casp16 score` and `./casp16 leaderboard`.

## Next Action

Do not promote this strategy by itself to the realistic attack-budget tier.
Use it as evidence that token-limit coverage fixes are necessary, then either
improve reference/domain mapping for rescued targets or design a broader
predeclared large-target fallback that can handle the remaining complex
failures without per-target oracle choices.
