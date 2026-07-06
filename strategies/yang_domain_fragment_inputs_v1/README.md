# yang_domain_fragment_inputs_v1

Purpose: reproduce the CASP16 winner-style domain decomposition idea as a
controlled `target_lab` artifact. This generates Protenix inputs for individual
CASP domain fragments instead of full target sequences.

This strategy uses CASP domain-summary metadata, so it is not a clean
server-stage automatic strategy. It must not be queued into the ranked
`casp16_server_protein_v1` workflow without creating a new benchmark version or
otherwise declaring the post hoc metadata policy.

## Generated Artifacts

- `casp16_server_protein_v1/inputs.json`: fragment-only Protenix input JSON.
- `casp16_server_protein_v1/manifest.tsv`: per-domain audit table with source
  target, domain id, residue ranges, status, skip reason, and fragment length.

Generation command:

```bash
./casp16 strategy-inputs --benchmark casp16_server_protein_v1 --strategy yang_domain_fragment_inputs_v1
```

Current generation summary:

- fragment jobs: 44
- source targets: 33
- emitted domains: 44
- skipped domains: 18
- output sha256: `c4ebff6dc782dfb09f56e10cc8d0f7479c3fba5d59bc1872904045795a9962cd`

Skip reasons are intentionally conservative:

- `requires_single_copy_entity`: multi-copy/multimer inputs are not cropped in
  v1 because chain/domain mapping would be ambiguous.
- `requires_single_protein_entity`: mixed or unsupported inputs are skipped.
- `non_contiguous_domain`: split domains such as `301-401,468-535` are not
  stitched in v1.

## Launch Gate

Do not queue this as a ranked server run. Use it for fast target-lab learning:

- compare domain-fragment predictions against full-target predictions after the
  baseline has produced structures,
- identify whether domain decomposition is worth a new benchmark version,
- design a future predeclared domain predictor or segmentation rule that does
  not depend on post hoc CASP domain summaries.

Potential lab-only run spec command:

```bash
./casp16 run-spec \
  --run-id targetlab_protenix_yang_domain_fragment_seed101 \
  --benchmark casp16_server_protein_v1 \
  --input-json strategies/yang_domain_fragment_inputs_v1/casp16_server_protein_v1/inputs.json \
  --input-manifest strategies/yang_domain_fragment_inputs_v1/casp16_server_protein_v1/manifest.tsv \
  --strategy yang_domain_fragment_inputs_v1 \
  --rank-eligible false \
  --use-msa --use-template --use-default-params
```

Keep any result from this branch separate from server-track claims.
