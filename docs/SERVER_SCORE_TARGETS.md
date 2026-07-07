# CASP16 Server Score Targets

This file pins the score target for the autoresearch loop. It should be read
with `docs/AUTORESEARCH.md` and `docs/SERVER_ATTACK_POLICY.md`.

## Official Server Targets To Beat

Source: `leaderboards/casp16_server_protein_v2_aliasfix/official_groups.csv`,
server-only groups, fixed eligible target sets.

| Track | Metric | Eligible targets | Server leader | Fixed mean to beat | Coverage |
| --- | --- | ---: | --- | ---: | --- |
| protein domains | GDT_TS | 71 | `110s` | `0.923321` | 71/71 |
| protein oligos | QSglob | 104 | `456s` | `0.582615` | 102/104 |

Top nearby server baselines:

| Track | Rank | Group | Fixed mean |
| --- | ---: | --- | ---: |
| protein domains | 2 | `019s` | `0.908993` |
| protein domains | 3 | `147s` | `0.907055` |
| protein oligos | 2 | `052s` | `0.581712` |
| protein oligos | 3 | `110s` | `0.543327` |

## Current Local Floor

Source: `leaderboards/casp16_server_protein_v1/runs.csv`.

| Track | Best current local full Protenix row | Budget tier | Fixed mean | OK targets | Missing predictions | Gap to leader |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| protein domains | `server_protenix_yang_terminal_tag_cleanup_seed101` | `dev_fixed` | `0.066908` | 15 | 30 | `+0.856413` |
| protein oligos | `server_protenix_yang_terminal_tag_cleanup_seed101` | `dev_fixed` | `0.045865` | 27 | 47 | `+0.536750` |

Interpretation: the local baseline is still failure-level relative to official
server leaders. The immediate useful signals are coverage recovery, correct
metric mapping, and full-set mean increases. A few impressive target-lab or
partial-run examples do not count as server progress.

## Current V2 Diagnostic Floor

Source: `leaderboards/casp16_server_protein_v2_aliasfix/target_scores.csv`,
generated from the current alias-fixed diagnostics.

The best v2 diagnostic row,
`server_v2_protenix_yang_oligo_sequence_stoich_low_complexity_large_fallback_seed101`,
is still dominated by coverage and mapping failures:

| Track | Mean | OK | Missing prediction | Missing reference | Nonzero targets |
| --- | ---: | ---: | ---: | ---: | ---: |
| protein domains | `0.049685` | 13/71 | 32/71 | 26/71 | 9 |
| protein oligos | `0.000923` | 8/104 | 82/104 | 14/104 | 1 |

The only nonzero v2 oligo diagnostic is `T1249V1O` with QSglob `0.096`.
After adding scorer alias diagnostics, all eight current oligo `ok` rows are
`sequence_lookup` matches rather than exact `*O` prediction matches. These rows
are useful for detecting alias/assembly false-zero classes, but they are not a
strong exact-oligo quality signal yet.
The nonranked seed-101 scoreable-attack probe improves the partial domain
picture: 24 exact domain predictions score 17 nonzero targets, with fixed-set
domain mean `0.099576`. After the scorer exact-artifact gate, its oligo rows are
104/104 `missing_prediction`: the previous `sequence_lookup` fallback positives
are not counted when the run input declares exact `TxxxxO`/`Hxxxx` jobs. The
next oligo gate is exact `*O` prediction/assembly scoring, not blindly
increasing the seed count.
Before spending another winner-scale budget, the high-leverage work is still
reference recovery, prediction coverage, and QSglob assembly mapping. More
seeds cannot rescue targets that are missing predictions, missing references,
or mapped to QSglob false zeros.
The concrete reference-recovery worklist is
`diagnostics/reference_gap/casp16_server_protein_v2_aliasfix_missing_references.tsv`;
its first block is 40 existing v2 diagnostic predictions that are currently
scored as `missing_reference`.

## Active Score Gates

Post-P17 update, `2026-07-07`: P14 completed and scored with all 370 declared
candidates, but still had 5 locally scoreable targets as `missing_prediction`.
P17 fixed that via a P14 plus added-only overlay, improved both ranked tracks,
and produced a `candidate_limited_signal`. The active gate is now P25:
wait for the submitted seed106-125 target-seed shards, merge them with the
seed101-105 overlay, then score the complete 25-candidate row.

Latest live checkpoint, `2026-07-07 13:37 CDT`: P25 is still not merge-ready.
`finish_p25_scoreable_input_repair.sh --dry-run` reports `ready=false`,
`compatible=true`, `1091` observed candidates, `959` shard-level candidates
missing, and `889` full 25-candidate slots missing. Slurm still has 19 P25
jobs running and 5 P25 jobs pending behind `QOSMaxJobsPerUserLimit`; shard05
seed121-125 and all shard06 seed blocks remain pending. Do not use a partial
P25 row for score comparisons or for launching O5b/P27b/D6a. Current runtime
is normal large-complex inference plus queue limits, not an MSA-cache miss or a
silent failure class. The latest P25 MSA audit remains `24/24 ok` with
`584/584` protein-chain paths covered and `0` stale paths. The latest error
keyword scan is clean, and `run-next --dry-run` reports `no_pending_runs`.

Current P25 closeout command:

```bash
scripts/finish_p25_scoreable_input_repair.sh --dry-run
scripts/finish_p25_scoreable_input_repair.sh
```

The dry-run JSON includes `status_summary`. The only safe pre-closeout action
for `status_summary.action=wait_for_declared_candidates` is to wait or inspect
execution health; it is not a scoring point and not permission to launch
P27b/O5b/D6a. `status_summary.action=run_finish_without_dry_run` is the merge
and score gate.

1. Historical P14 closeout command sequence, now complete:
   `server_v2_attack_scoreable_size_balanced_msa_reuse_protenix5_seed101_105`.
   The six execution shards are rank-ineligible until every one has all five
   declared candidates for its target subset and has been merged with
   `./casp16 merge-shards --allow-target-shards`. Do not use a partial shard
   score to launch the planned 25-candidate budget.
   Required readout sequence:

   ```bash
   ./casp16 check-shards \
     --benchmark casp16_server_protein_v2_aliasfix \
     --merged-run-id server_v2_attack_scoreable_size_balanced_msa_reuse_protenix5_seed101_105 \
     --merged-input-json strategies/scoreable_target_subset_oligo_size_first_phase_alias_v1/casp16_server_protein_v2_aliasfix/inputs.json \
     --candidate-count 5 \
     --shard-run-id server_v2_attack_scoreable_size_balanced_shard01_msa_reuse_protenix5_seed101_105 \
     --shard-run-id server_v2_attack_scoreable_size_balanced_shard02_msa_reuse_protenix5_seed101_105 \
     --shard-run-id server_v2_attack_scoreable_size_balanced_shard03_msa_reuse_protenix5_seed101_105 \
     --shard-run-id server_v2_attack_scoreable_size_balanced_shard04_msa_reuse_protenix5_seed101_105 \
     --shard-run-id server_v2_attack_scoreable_size_balanced_shard05_msa_reuse_protenix5_seed101_105 \
     --shard-run-id server_v2_attack_scoreable_size_balanced_shard06_msa_reuse_protenix5_seed101_105

   ./casp16 merge-shards \
     --benchmark casp16_server_protein_v2_aliasfix \
     --run-id server_v2_attack_scoreable_size_balanced_msa_reuse_protenix5_seed101_105 \
     --merged-input-json strategies/scoreable_target_subset_oligo_size_first_phase_alias_v1/casp16_server_protein_v2_aliasfix/inputs.json \
     --allow-target-shards \
     --candidate-count 5 \
     --shard-run-id server_v2_attack_scoreable_size_balanced_shard01_msa_reuse_protenix5_seed101_105 \
     --shard-run-id server_v2_attack_scoreable_size_balanced_shard02_msa_reuse_protenix5_seed101_105 \
     --shard-run-id server_v2_attack_scoreable_size_balanced_shard03_msa_reuse_protenix5_seed101_105 \
     --shard-run-id server_v2_attack_scoreable_size_balanced_shard04_msa_reuse_protenix5_seed101_105 \
     --shard-run-id server_v2_attack_scoreable_size_balanced_shard05_msa_reuse_protenix5_seed101_105 \
     --shard-run-id server_v2_attack_scoreable_size_balanced_shard06_msa_reuse_protenix5_seed101_105

   ./casp16 score --benchmark casp16_server_protein_v2_aliasfix \
     --run-id server_v2_attack_scoreable_size_balanced_msa_reuse_protenix5_seed101_105
   ./casp16 leaderboard --benchmark casp16_server_protein_v2_aliasfix
   ```
   P17 closeout should use the repaired full input and the six P17 shards:

   ```bash
   ./casp16 finish-shards \
     --benchmark casp16_server_protein_v2_aliasfix \
     --run-id server_v2_attack_scoreable_input_repair_size_balanced_msa_reuse_protenix5_seed101_105 \
     --merged-input-json strategies/scoreable_target_subset_input_repair_v1/casp16_server_protein_v2_aliasfix/inputs.json \
     --allow-target-shards \
     --candidate-count 5 \
     --output-tsv diagnostics/score_probes/target_shards_scoreable_input_repair_size_balanced_readiness.tsv \
     --tmscore-bin /scratch/10992/liaorunlong93/conda/envs/protein/bin/TMscore \
     --shard-run-id server_v2_attack_scoreable_input_repair_size_balanced_shard01_msa_reuse_protenix5_seed101_105 \
     --shard-run-id server_v2_attack_scoreable_input_repair_size_balanced_shard02_msa_reuse_protenix5_seed101_105 \
     --shard-run-id server_v2_attack_scoreable_input_repair_size_balanced_shard03_msa_reuse_protenix5_seed101_105 \
     --shard-run-id server_v2_attack_scoreable_input_repair_size_balanced_shard04_msa_reuse_protenix5_seed101_105 \
     --shard-run-id server_v2_attack_scoreable_input_repair_size_balanced_shard05_msa_reuse_protenix5_seed101_105 \
     --shard-run-id server_v2_attack_scoreable_input_repair_size_balanced_shard06_msa_reuse_protenix5_seed101_105
   ```
2. Compare only `dev_fixed` to `dev_fixed`. A single-seed row can prove that an
   input strategy is worth more compute, but it is not winner-comparable.
3. Score `server_attack` rows only after every declared candidate is present.
   Partial target candidates score `0`; seed shards must be merged with
   `./casp16 merge-shards` before a 25-candidate row can be scored.
4. For official server comparison, domains use `GDT_TS`; oligos use `QSglob`.
   DockQ and confidence are diagnostics only.

The preferred shard closeout command is `finish-shards`. It is intentionally
safe to run while shards are still live: if readiness is false, it only writes
the readiness report and returns `finish_status=not_ready`. Once readiness is
true, it performs the merge, full benchmark scoring refresh, and leaderboard
refresh in one audited step. The P14 closeout should include the predeclared
P16 replay arguments so the consensus selector row is registered before any
P14 score table is inspected.

```bash
./casp16 finish-shards \
  --benchmark casp16_server_protein_v2_aliasfix \
  --run-id server_v2_attack_scoreable_size_balanced_msa_reuse_protenix5_seed101_105 \
  --merged-input-json strategies/scoreable_target_subset_oligo_size_first_phase_alias_v1/casp16_server_protein_v2_aliasfix/inputs.json \
  --allow-target-shards \
  --candidate-count 5 \
  --output-tsv diagnostics/score_probes/target_shards_scoreable_size_balanced_readiness.tsv \
  --replay-run-id server_v2_attack_scoreable_size_balanced_msa_reuse_protenix5_seed101_105_consensus_replay \
  --replay-selected-model-policy diversity_confidence_consensus_v1 \
  --replay-strategy scoreable_target_subset_oligo_size_first_phase_alias_v1_consensus_selector_replay \
  --replay-selection-qa-output-csv diagnostics/selection_qa/server_v2_attack_scoreable_size_balanced_msa_reuse_protenix5_seed101_105_consensus_replay.selection_qa.csv \
  --post-p14-readout-output-json diagnostics/score_probes/post_p14_readout_latest.json \
  --tmscore-bin /scratch/10992/liaorunlong93/conda/envs/protein/bin/TMscore \
  --shard-run-id server_v2_attack_scoreable_size_balanced_shard01_msa_reuse_protenix5_seed101_105 \
  --shard-run-id server_v2_attack_scoreable_size_balanced_shard02_msa_reuse_protenix5_seed101_105 \
  --shard-run-id server_v2_attack_scoreable_size_balanced_shard03_msa_reuse_protenix5_seed101_105 \
  --shard-run-id server_v2_attack_scoreable_size_balanced_shard04_msa_reuse_protenix5_seed101_105 \
  --shard-run-id server_v2_attack_scoreable_size_balanced_shard05_msa_reuse_protenix5_seed101_105 \
  --shard-run-id server_v2_attack_scoreable_size_balanced_shard06_msa_reuse_protenix5_seed101_105
```

After closeout, use the read-only decision helper before opening the next GPU
branch if the `finish-shards` command did not already write it:

```bash
./casp16 post-p14-readout \
  --benchmark casp16_server_protein_v2_aliasfix \
  --run-id server_v2_attack_scoreable_size_balanced_msa_reuse_protenix5_seed101_105 \
  --replay-run-id server_v2_attack_scoreable_size_balanced_msa_reuse_protenix5_seed101_105_consensus_replay \
  --output-json diagnostics/score_probes/post_p14_readout_latest.json
```

This helper reads only `runs.csv`, `target_scores.csv`, and benchmark target
metadata. It does not read native structures, official per-target score tables,
or prediction outputs, and it does not submit jobs.

Current live P25 status, checked `2026-07-07 13:37 CDT`: P17 overlay is merged
and scored. The 24 seed106-125 GH200 target-seed jobs `812935..812958` are
submitted after `24/24 ok` preflight with complete MSA reuse and 0 stale paths;
the aggregate P25 MSA audit covers `584/584` protein chains with `0` stale.
Slurm currently has 19 P25 jobs running and 5 P25 jobs pending behind
`QOSMaxJobsPerUserLimit`. The latest readiness check is `ready=false`,
`compatible=true`, with 1091 observed candidates, 959 shard-level candidates
missing, and 889 full merged candidate slots still missing. Shard05
seed121-125 and all shard06 seed blocks still have zero observed candidates,
so the merged 25-candidate row is not scoreable yet. Use `--candidate-count 5
--merged-candidate-count 25` for target+seed readiness. Do not score the
25-candidate row, launch a competing branch, or make a winner-comparison claim
before those jobs finish and are merged with the seed101-105 overlay.

## Post-P17 Decision Matrix

After P17 is merged and scored, inspect `runs.csv`, `target_scores.csv`, and
`coverage.md` for the merged run. The next branch should be selected by the
failure mode, not by impatience to spend more GPU time.

Readout order:

1. Verify closeout integrity first: merged P17 exists, `candidate_count=5`,
   `partial_candidate_targets=0`, no metric-unavailable rows, no scoreable
   `missing_prediction` rows, and the leaderboard was regenerated after merge.
2. Separate expected fixed-set zeros from true failures. No-reference targets
   still score `0`; the actionable failures are scoreable-input
   `missing_prediction`, `metric_failed`, exact-artifact lookup misses, and
   newly exposed input-kind mistakes.
3. Compare P17 against the current v2 diagnostic floor and P14, not against a partial
   shard snapshot: domain fixed mean `0.049685`, exact-domain partial probe
   mean `0.099576`, P14 domain mean `0.102777`, and P14 oligo mean
   `0.116923`.
4. Pick one next GPU branch. Do not launch P15, P18/P25, P27b, D6a, and O5b in
   parallel unless a later score readout records why the extra spend is worth
   it.

| P17 observation | Interpretation | Next branch |
| --- | --- | --- |
| Domain and/or oligo fixed means improve over P14 and exact protein-oligo rows include broad nonzero QSglob scores | Five candidates plus the repaired scoreable input stack have real signal; candidate budget and selector are plausible bottlenecks | Launch the prepared repaired-input 25-candidate scoreable target+seed grid |
| P17 has good scoreable-target signal but most full-set zeros are still no-reference rows | Reference recovery can unlock more local measurement without changing the prediction recipe | Launch/refresh P15 on a versioned refmap benchmark, and keep broader refmap work versioned |
| Scoreable rows are still `missing_prediction`, `metric_failed`, or exact oligo rows are not found | This is a pipeline/input/scorer failure, not a sampling failure | Fix the failure class before launching P25 |
| Domain zeros concentrate on known input-kind or sequence-alias repair classes such as `T1276/T1228V1/T1239V1/T2276` | More seeds will repeat bad inputs | Run D6a single-seed domain sequence recovery after MSA warmup |
| Exact QSglob remains weak mainly on antibody/Fv rows after phase-alias stoichiometry is fixed, while non-antibody exact oligos are no longer all zero | Oligo branch may need Fv/docking-inspired input handling | Launch the repaired-input O5b antibody-Fv target shards |
| Predictions and metrics are valid, but P25 remains near P17 and exact oligo QSglob is mostly zero | Current Protenix recipe is not enough; scaling seeds alone is low leverage | Launch P27b/default-params or build the broader MSA/model-variant budget before spending another winner-scale grid |

Prepared branch readiness to revisit after P17:

| Branch | Preflight | Evidence |
| --- | --- | --- |
| P15 v4 refmap target shards | `6/6 ok`, complete MSA reuse, 0 stale | `diagnostics/msa_cache/protenix5_v4_scoreable_target_run_preflight.tsv` |
| superseded P18 74-target scoreable grid | `30/30 ok`, complete MSA reuse, 0 stale | `diagnostics/msa_cache/protenix25_scoreable_target_seed_run_preflight.tsv` |
| P25 repaired 79-target scoreable grid | seed106-125 jobs `812935..812958` submitted after `24/24 ok`, complete MSA reuse, 0 stale; readiness remains false until all submitted jobs finish and merge with the seed101-105 overlay | `diagnostics/msa_cache/protenix25_scoreable_input_repair_target_seed_run_preflight.tsv`, `diagnostics/score_probes/protenix25_scoreable_input_repair_target_seed_readiness.tsv` |
| P27a default-params model/config variant | `6/6 ok`, complete MSA reuse, 0 stale | `diagnostics/msa_cache/protenix5_defaultparams_model_variant_preflight.tsv` |
| P27b repaired-input default-params variant | `6/6 ok`, complete MSA reuse, 0 stale | `diagnostics/msa_cache/protenix5_input_repair_defaultparams_model_variant_preflight.tsv` |
| D6a domain sequence recovery | warmup produced repaired `T1228V1/T1239V1/T1276` predictions and MSA cache; follow-up full run is `1/1 ok`, complete MSA reuse (`276/276`), 0 stale, no predictions yet | `diagnostics/msa_cache/domain_sequence_recovery_after_warmup_preflight.tsv`, `runs/server_v2_domain_sequence_recovery_msa_warmup_seed101/` |
| O5 antibody-Fv target shards | `6/6 ok`, complete MSA reuse, 0 stale | `diagnostics/msa_cache/protenix5_antibody_fv_target_run_preflight.tsv` |
| O5b repaired-input antibody-Fv target shards | `6/6 ok`, complete MSA reuse, 0 stale | `diagnostics/msa_cache/protenix5_input_repair_antibody_fv_preflight.tsv` |

`./casp16 post-p25-readout` returns a `launch_plan` object for the selected
post-P25 branch. Treat that object as the machine-readable run-id and preflight
source after P25 is complete; the tables here are explanatory context.

## What Counts As Progress

- More scoreable domain targets without lowering the full-set mean.
- Higher fixed-set domain mean on the 71 official domain targets.
- Nonzero, correctly mapped QSglob on more of the 104 official oligo targets.
- Reduced hard failures: missing prediction, token-limit failure, metric
  unavailable, metric failed, and missing reference.
- A predeclared multi-candidate attack row that improves over its matching
  `dev_fixed` parent without hidden candidate selection.

## What Does Not Count

- A target-lab improvement that has not become a target-agnostic full benchmark
  rule.
- A single-seed score described as winner-comparable.
- A partial multi-seed run scored as if all candidates exist.
- Confidence-only quality claims.
- A DockQ-only oligo claim against the official server QSglob leaderboard.
