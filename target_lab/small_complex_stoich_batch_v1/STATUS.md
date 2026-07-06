# Small Complex Stoich Batch Status

- Submitted: 2026-07-06T16:27:14Z
- Slurm job ID: `810824`
- Slurm job name: `casp16_tlab_complex`
- Initial state: `PENDING (Priority)`
- Scope: target_lab only, not rank eligible
- Command:

```bash
ssh login1 'cd /scratch/10992/liaorunlong93/casp16-leaderboard && sbatch target_lab/small_complex_stoich_batch_v1/run_gh200.slurm'
```

Monitor:

```bash
ssh login1 'squeue -j 810824 -o "%i %T %M %D %R %j"'
```

After completion:

```bash
python target_lab/small_complex_stoich_batch_v1/summarize_outputs.py
```
