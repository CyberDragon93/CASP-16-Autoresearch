# CASP16 Autoresearch Experiments

This is the append-only working log for CASP16 score-chasing experiments.
Strategy changes should be recorded here before they are interpreted as
leaderboard progress.

## Active Baselines

| Run | Benchmark | Status | Purpose | Rank eligible |
| --- | --- | --- | --- | --- |
| `server_eval_opendde_v1_full_msa_template_bf16_h1220_t1220s1` | `casp16_server_protein_v1` | scored diagnostic | reuse 35 existing OpenDDE local-v1 predictions to expose server coverage gap | no |
| `server_protenix_full_msa_template_seed101` | `casp16_server_protein_v1` | pending | full server-target Protenix baseline with real MSA/template settings | yes, once predictions and required scorers exist |

## Current Score Truth

- Server domain comparator to beat: `110s`, fixed mean `0.923321`, metric
  `GDT_TS`, 71 targets.
- Server oligo comparator to beat: `456s`, fixed mean `0.582615`, metric
  `QSglob`, 104 targets.
- Current local server diagnostic reuse: domain `0.036428`, oligo `0.000000`.
  The main deficit is coverage and missing QSglob, not just model quality.

## Next Experiment Queue

1. Run `server_protenix_full_msa_template_seed101` on a GH200 node to generate
   predictions for the 106 server benchmark Protenix jobs.
   - Submit from a Vista login node with
     `sbatch runs/server_protenix_full_msa_template_seed101/run_gh200.slurm`.
   - Startup sanity has passed through Protenix argparse help with
     `cuda/12.5`, Protenix source-first `PYTHONPATH`, and NVIDIA math libs
     include/library paths for `cusparse.h`.
2. Score the domain track immediately after predictions finish; oligo rows will
   stay `metric_unavailable` until a QSglob scorer exists.
3. Install or implement QSglob, then rescore the oligo track.
4. Start target_lab loops on H1258 and H1232 only as diagnostics for
   stoichiometry/construct tricks; promotion requires a target-agnostic full
   benchmark rerun.
5. Add domain cropping and chain/residue mapping before drawing conclusions
   from hard multi-domain domain targets.

## Promotion Rules

- A target_lab improvement is not a leaderboard improvement.
- A manual rescue is not a server-style result unless it becomes an automatic
  target-agnostic rule.
- Confidence can help analyze failures, but it is never a quality score.
- If a trick changes target eligibility, budget, metric identity, or model
  selection policy, create a new benchmark version.
