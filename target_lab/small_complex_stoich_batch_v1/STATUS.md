# Small Complex Stoich Batch Status

- Submitted: 2026-07-06T16:27:14Z
- Slurm job ID: `810824`
- Slurm job name: `casp16_tlab_complex`
- Final state: failed after start on `c641-002`
- Failure: `runner.batch_inference` was imported from
  `/scratch/10992/liaorunlong93/OpenDDE` instead of `Protenix-Insta`
- Scope: target_lab only, not rank eligible
- Command:

```bash
ssh login1 'cd /scratch/10992/liaorunlong93/casp16-leaderboard && sbatch target_lab/small_complex_stoich_batch_v1/run_gh200.slurm'
```

Fix:

- `run_protenix.sh` now prepends
  `/scratch/10992/liaorunlong93/Protenix-Insta` to `PYTHONPATH`.
- The script also exports the Protenix data root, conda env `bin` path, and
  CUDA/math library paths so Protenix can find `protenix_cli`, `ninja`, and
  CUDA runtime libraries.
- Import preflight passed after the fix:
  `/scratch/10992/liaorunlong93/Protenix-Insta/runner/batch_inference.py`
  with `protenix_cli=True`.

Resubmission:

- Submitted: 2026-07-06T18:10Z
- Slurm job ID: `811114`
- Current state: running on `c639-081`
- Latest output: CIF generation has started; currently in Protenix inference

Monitor:

```bash
ssh login1 'squeue -j 811114 -o "%i %T %M %D %R %j"'
```

After completion:

```bash
python target_lab/small_complex_stoich_batch_v1/summarize_outputs.py
python target_lab/small_complex_stoich_batch_v1/score_dockq.py
```
