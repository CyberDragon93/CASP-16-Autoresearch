# Domain Fragment Target-Lab Status

- Slurm job: `810862`
- Submitted: 2026-07-06
- Partition: `gh`
- Scope: target_lab only, not ranked
- Budget: Protenix v2, seed `101`, sample `1`, MSA/templates/default params enabled

Purpose: test whether CASP-domain fragment inputs are worth promoting into a
future target-agnostic segmentation strategy or benchmark version.

After completion:

```bash
python target_lab/domain_fragment_batch_v1/summarize_outputs.py
```

Do not register this as a ranked CASP16 server run.
