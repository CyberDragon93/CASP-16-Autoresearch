# CASP16 Winner Match Runbook

This is the operational runbook for the current score chase. It is shorter
than `docs/CASP16_WINNER_RECIPES.md` on purpose: when P25 finishes, use this
file to move from completed predictions to the next winner-reproduction branch
without re-debating the benchmark.

## Score Target

Use `casp16_server_protein_v2_aliasfix` for the current server-style comparison.
The official server leaders to beat are pinned in
`docs/SERVER_SCORE_TARGETS.md`:

| Track | Metric | Fixed targets | Server leader | Mean to beat |
| --- | --- | ---: | --- | ---: |
| protein domain | GDT_TS | 71 | `110s` MIEnsembles-Server | `0.923321` |
| protein oligo | QSglob | 104 | `456s` Yang-Multimer | `0.582615` |

The current best complete local row is
`server_v2_attack_scoreable_input_repair_overlay_msa_reuse_protenix5_seed101_105`:
domain `0.107690`, oligo `0.118933`. Treat that as a floor, not as a near-win.

## Immediate Gate

P25 is the active gate:

```bash
scripts/finish_p25_scoreable_input_repair.sh --dry-run \
  --output-tsv /tmp/casp16_p25_readiness_live.tsv
```

If the JSON reports `status_summary.action=wait_for_declared_candidates`,
do not score, do not launch P27b/D6a/O5b/P15, and do not claim a winner
comparison. Only use read-only health checks:

```bash
./casp16 post-p25-branch-readiness
rg -n "Traceback|RuntimeError|CUDA out of memory|out of memory|Killed|killed|No such file|FileNotFoundError|ImportError|segmentation|ERROR|Exception" \
  runs/server_v2_attack_scoreable_input_repair_size_balanced_shard*_msa_reuse_protenix25_seed*/logs/*.log \
  runs/server_v2_attack_scoreable_input_repair_size_balanced_shard*_msa_reuse_protenix25_seed*/logs/p25_*.err
```

When the dry-run reports `status_summary.action=run_finish_without_dry_run`,
run the same wrapper without `--dry-run`:

```bash
scripts/finish_p25_scoreable_input_repair.sh
./casp16 post-p25-readout --benchmark casp16_server_protein_v2_aliasfix
```

The wrapper must merge the P17 seed101-105 overlay with all seed106-125 P25
target shards, score the normal `protenix_confidence_v1` row, score the
no-GPU consensus replay, regenerate the leaderboard, and write the
post-P25 decision JSON. Partial rows are not winner-comparable.

## Branch Selector

Use only the complete post-P25 aggregate readout. Do not mine individual target
scores to tune target-specific inputs.

| Complete P25 signal | Winner capability being reproduced | Next action |
| --- | --- | --- |
| Broad domain and oligo gain over P17 | candidate budget plus predeclared QA can move the server-style mean | inspect aggregate deltas and selector behavior before launching another GPU branch |
| Flat versus P17, with predictions and metrics valid | MIEnsembles/MULTICOM-style model/config diversity | launch P27b repaired-input default-params shards |
| Domain zeros/failures cluster on predeclared input-kind or alias classes | Yang-style sequence/construct repair | launch D6a domain sequence recovery |
| Oligo weakness clusters on antibody/Fv rows while other oligos show signal | specialized antibody/complex handling | launch O5b repaired-input antibody/Fv shards |
| Most loss is missing reference or unresolved QSglob mapping | measurement coverage, not prediction compute | continue v5 refmap or explicitly run P15/v4 only as v4 |

## Ready Branches

The read-only readiness audit at `2026-07-07 16:05 CDT` reported all four
deferred branch families as launch-ready after P25 selection:

| Branch | Prepared artifact | Preflight |
| --- | --- | --- |
| P27b model/config diversity | `attack_budgets/casp16_server_attack_protenix5_input_repair_defaultparams_model_variant_shards.tsv` | `6/6 ok`, `146/146` chains reused |
| D6a domain input repair | `runs/server_v2_domain_sequence_recovery_oligo_nofail_msa_reuse_after_warmup_seed101/run_spec.json` | `1/1 ok`, `276/276` chains reused |
| O5b antibody/Fv | `attack_budgets/casp16_server_attack_protenix5_input_repair_antibody_fv_shards.tsv` | `6/6 ok`, `146/146` chains reused |
| P15/v4 refmap comparison | `attack_budgets/casp16_server_attack_protenix5_v4_scoreable_target_shards.tsv` | `6/6 ok`, `143/143` chains reused |

For a selected target-sharded branch, mark only the selected run ids pending,
dry-run each selected run id, then submit through a login node:

```bash
./casp16 mark-run --run-id <run_id> --status pending \
  --message "selected after complete P25 readout: <decision_status>"
./casp16 run-one --run-id <run_id> --dry-run
ssh login1 'cd /scratch/10992/liaorunlong93/casp16-leaderboard && RUN_ID=<run_id> sbatch --export=ALL slurm/casp16_run_one_gh200.slurm'
```

Do not launch a branch unless the expected aggregate winner-gap reduction is
named before submission.

## Current Live Note

At `2026-07-07 16:05 CDT`, P25 was still not ready:
`ready=false`, `1413` observed candidates, `645` shard-level missing
candidates, `580` full 25-candidate slots missing, and `6/79` full-budget
tasks complete. Slurm showed 19 P25 jobs running and 5 P25 jobs pending behind
`QOSMaxJobsPerUserLimit`; the zero-output rows were shard05 seed121-125 and all
four shard06 seed blocks. The error keyword scan was clean, and prediction
artifacts were still being written at 16:05 CDT.
