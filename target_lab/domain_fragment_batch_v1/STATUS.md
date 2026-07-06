# Domain Fragment Target-Lab Status

- Slurm job: `810862`
- Submitted: 2026-07-06
- Current state: completed on `c622-022` with exit code `0:0`
- Partition: `gh`
- Scope: target_lab only, not ranked
- Budget: Protenix v2, seed `101`, sample `1`, MSA/templates/default params enabled
- Output: 12/12 structures and confidence files; `SUMMARY.md` and
  `summary.tsv` regenerated after completion

Purpose: test whether CASP-domain fragment inputs are worth promoting into a
future target-agnostic segmentation strategy or benchmark version.

Regenerate summary:

```bash
python target_lab/domain_fragment_batch_v1/summarize_outputs.py
```

Do not register this as a ranked CASP16 server run.
