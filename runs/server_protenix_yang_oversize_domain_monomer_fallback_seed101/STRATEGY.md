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

- Rank status: pending, queued behind `server_protenix_yang_terminal_tag_cleanup_seed101`.
- Mean score: unavailable.
- Eligible targets: fixed `casp16_server_protein_v1` target set.
- OK targets: unavailable.
- Missing targets: unavailable.
- Failed targets: unavailable.
- Metric unavailable targets: expected for oligo QSglob until scorer exists.
- Artifact path: `runs/server_protenix_yang_oversize_domain_monomer_fallback_seed101/`.

## Failure Notes

No prediction has been launched yet. The generated manifest changes only
`T1295`, reducing total protein length from 3752 to 469 residues. Multi-entity
oversize jobs and all protein-oligo jobs remain unchanged because they need a
separate predeclared split policy.

## No-Oracle Checklist

- [x] Did not inspect native/reference structures before prediction.
- [x] Did not use official score tables for target-specific tuning.
- [x] Did not use previous target scores for target-specific parameter choices.
- [x] Did not replace structure metrics with confidence diagnostics.
- [x] Regenerated inputs only through `./casp16 strategy-inputs`; results are
      not yet scored.

## Next Action

After the active terminal-tag full run is scored, launch this pending fallback
through `./casp16 run-next --benchmark casp16_server_protein_v1` and compare
the fixed-set server-domain mean against the baseline.
