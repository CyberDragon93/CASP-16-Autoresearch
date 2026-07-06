# Domain Fragment Target Lab

This target-lab batch turns the `yang_domain_fragment_inputs_v1` strategy into a
small runnable Protenix experiment. It tests the CASP16 winner-style hypothesis
that domain decomposition can improve difficult protein-domain targets before
we spend a full benchmark run.

This is not a ranked leaderboard run. The fragment choices use CASP domain
summary metadata, so any promotion must become a new predeclared benchmark
version or a target-agnostic segmentation rule.

## Jobs

The batch contains 12 single-chain fragment jobs:

- `T1210__T1210-D1`: long-domain positive control with a cached reference.
- `T1218__T1218-D1`, `T1218__T1218-D2`, `T1218__T1218-D3`: three-domain
  Cry26Aa decomposition.
- `T1269__T1269-D1`, `T1269__T1269-D2`, `T1269__T1269-D3`: large-chain
  three-domain decomposition.
- `T1257__T1257-D1`: long single-domain crop from a 1263-aa source.
- `T1240__T1240-D1`, `T1240__T1240-D2`: short domains from a multidomain
  source.
- `T1270__T1270-D1`, `T1270__T1270-D2`: two-domain split.

Largest fragment: 1633 residues. Total fragment tokens across jobs: 5327.

## Generate

```bash
python target_lab/domain_fragment_batch_v1/build_batch.py
```

This writes:

- `inputs.json`
- `manifest.tsv`

## Run

```bash
bash target_lab/domain_fragment_batch_v1/run_protenix.sh
```

Outputs are written under:

```text
target_lab/domain_fragment_batch_v1/predictions/protenix-v2/
```

## Summarize

After completion:

```bash
python target_lab/domain_fragment_batch_v1/summarize_outputs.py
```

This writes `summary.tsv` and `SUMMARY.md`. The summary is prediction coverage
and confidence diagnostics only; confidence must not be reported as a CASP
quality score.
