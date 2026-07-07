# CASP16 Autoresearch Queue

This queue turns winner-recipe notes into executable full-benchmark attempts.
The queue is allowed to change quickly; benchmark definitions are not.

## Post-P25 Fast Decision Queue

Current live P25 gate, checked `2026-07-07 14:09 CDT`: `ready=false`,
`compatible=true`, `1106` observed candidates, `944` shard-level candidates
missing, and `874` full 25-candidate slots missing. One target is now complete
at the full 25-candidate budget, but the merged P25 row is not scoreable yet.
Slurm has 19 P25 jobs
running and 5 P25 jobs pending behind `QOSMaxJobsPerUserLimit`. Do not submit
any branch in this section until the complete P25 row is merged and scored.
Current running shards show normal large-complex inference and queue waiting,
not repeated MSA recomputation. The latest error keyword scan is clean, and
`run-next --dry-run` reports `no_pending_runs`.

P25 closeout is now one command. Run dry-run until it reports ready, then run
the same wrapper without `--dry-run`:

```bash
scripts/finish_p25_scoreable_input_repair.sh --dry-run
scripts/finish_p25_scoreable_input_repair.sh
```

For frequent live polling, override the dry-run TSV path so a read-only check
does not dirty the tracked readiness file:

```bash
scripts/finish_p25_scoreable_input_repair.sh --dry-run \
  --output-tsv /tmp/casp16_p25_readiness_live.tsv
```

The wrapper calls `finish-shards` with the seed101-105 overlay plus every
submitted seed106-125 target-shard run id, `--candidate-count 5`,
`--merged-candidate-count 25`, `--allow-target-shards`, the scoreable repaired
input JSON, and the TMscore binary. It writes the readiness TSV and returns
`finish_status=not_ready` while any declared candidate is still missing.
The JSON now includes a compact `status_summary`; for P25 polling, read
`status_summary.action` first. `wait_for_declared_candidates` means keep
waiting and do not score or branch, while `run_finish_without_dry_run` means
the same wrapper can be rerun without `--dry-run`. `zero_output_shards` and
`largest_missing_shards` identify queue-blocked or slow execution shards
without inspecting partial target scores.

Follow-up health check, `2026-07-07 14:11 CDT`: a keyword scan across the P25
Slurm/stderr logs found no traceback, OOM, killed-process, missing-file, or
RuntimeError signatures. The newest CIF mtimes are still advancing inside
running shards, with recent writes from shard03/shard04/shard05 targets such
as `H2236`, `H0227`, `H2233`, and `T2249V1O`. The five zero-output shards in
the readiness JSON correspond to pending jobs behind the queue limit, not
observed execution failures. Keep waiting for declared candidates rather than
scoring partial output.

After the wrapper succeeds and the leaderboard is regenerated, run the
aggregate branch gate before selecting any deferred branch:

```bash
./casp16 post-p25-readout
```

On current artifacts this command returns `decision_status=not_scored` and
`next_branch=finish_or_score_p25`, which is expected because the merged P25 row
does not exist yet. It also emits a non-executing `launch_plan` object with
the selected action, run ids, preflight TSV, target-shard flag, command
templates, read-only run-spec summaries, and read-only preflight summaries.
When the chosen branch has run ids, `run_specs` reports whether each
`run_spec.json` exists, its latest lifecycle status from `runs/status.tsv`,
budget tier, candidate count, rank eligibility, input/output paths, and MSA
reuse summary. The current P17 repaired-input baseline is score-path clean
(`79/79` scoreable targets `ok`) with fixed-set mean `0.114371554` and 96
no-reference zero rows.
The readout now also emits predeclared branch diagnostics for D6a input-repair
targets, antibody/Fv oligo rows, exact non-antibody oligo signal, and
reference-limited scoreable coverage. Use those aggregate diagnostics after
the complete P25 score exists instead of manually mining `target_scores.csv` to
pick a target-specific next move.
It also emits `target_delta_summary`, which compares only locally scoreable
targets between P25 and P17 and summarizes improved/regressed/nonzero-gained
counts plus status transitions. It reports `status: incomplete` and
`valid_for_analysis: false` until both compared rows have complete scoreable
target scores. Treat the `status: ok` digest as a post-score explanation
layer, not a permission slip for per-target tuning.

While P25 is still running, use this read-only branch readiness audit to avoid
rediscovering prepared artifacts:

```bash
./casp16 post-p25-branch-readiness
```

It should report P27b, D6a, O5b, and P15/v4 as launch-ready before any branch
is selected. A stale deferred status label is not itself a blocker; missing run
specs or non-`ok` preflight rows are blockers.

Use this queue immediately after the complete P25 score exists:

| Priority | Trigger After P25 | Branch | Why This Beats Waiting | Launch Gate |
| --- | --- | --- | --- | --- |
| 1 | P25 has broad nonzero scoreable rows and improves over P17 | No new branch; analyze P25 target deltas and selection failures first | The 25-candidate budget is then the first serious signal for whether Protenix seed scaling helps | Record exact domain/oligo means, ok/missing/failed counts, and only then choose P27b/O5b/D6a |
| 2 | P25 is flat versus P17 while predictions and metrics are valid | P27b repaired-input default-params model/config variant | Reproduces the winner clue that model/config diversity can matter more than more seeds on one input | Run only the six `server_v2_attack_scoreable_input_repair_defaultparams_shard*` specs; preflight is `6/6 ok`, MSA `146/146`, 0 stale |
| 3 | P25 domain zeros or failures concentrate on `T1276/T1228V1/T1239V1/T2276`-class input-kind/alias repairs | D6a domain sequence recovery full run | More seeds repeat bad inputs; the D6a input is now cache-complete and repairs the sequence modality class | Mark `server_v2_domain_sequence_recovery_oligo_nofail_msa_reuse_after_warmup_seed101` pending, dry-run it, then run a single `dev_fixed` job |
| 4 | P25 oligo QSglob failures concentrate on antibody/Fv rows while non-antibody exact oligos show signal | O5b repaired-input antibody/Fv shards | Target-lab Fv diagnostics were positive, and O5b promotes the rule without hand-picking targets | Run only the six `server_v2_attack_scoreable_input_repair_antibody_fv_shard*` specs; preflight is `6/6 ok`, MSA `146/146`, 0 stale |
| 5 | P25 is mostly capped by `missing_reference` while predictions are otherwise usable | P15/v4 or V5 refmap work, not more GPU | Additional predictions cannot score without references; reference work must be versioned | Do not patch v2/v4 in place; use accepted refmap rows and a new benchmark version when needed |

While P25 is still running, use the non-GPU V5 reference queue in
`diagnostics/reference_gap/casp16_server_protein_v5_refmap_recovery_queue.tsv`
for scoring-infrastructure work. It groups the 94 v4 missing-reference rows
into 42 target-family tasks, with explicit lanes for `T1228V1` provenance,
deferred sequence-hit review, domain manual native search, oligo assembly
mapping, input/alias repair, and oligo manual native search. This queue is not
prediction guidance and must not be used for target-specific strategy tuning.
The Lane C input-alias details are now split out in
`diagnostics/reference_gap/casp16_server_protein_v5_input_alias_repair_candidates.tsv`:
`T1228V2/T1294V2` can move through D6a-style repaired inputs, and
`H1265_V1/V2/V3` now have sequence-level H1265 A/B input repair in
`yang_protein_oligo_sequence_recovery_v1` with complete MSA-cache coverage.
All five Lane C rows remain `not_reference_ready` until explicit native/domain
or assembly/QSglob mapping proof exists.

For a selected deferred run, record the decision before launch:

```bash
./casp16 mark-run --run-id <run_id> --status pending --message "selected after complete P25 readout: <reason>"
./casp16 run-one --run-id <run_id> --dry-run
ssh login1 'cd /scratch/10992/liaorunlong93/casp16-leaderboard && RUN_ID=<run_id> sbatch --export=ALL slurm/casp16_run_one_gh200.slurm'
```

For target-disjoint shard branches, submit each selected shard run id with the
same `RUN_ID=... sbatch` pattern. Do not use `--allow-parallel` unless the
target-shard manifest has already proven the selected shards are disjoint.
Prefer the `launch_plan` object from `post-p25-readout` as the machine-readable
source for selected run ids and preflight files.

## Next To Run

| Priority | Run | Benchmark | Status | Why It Matters | Next Gate |
| --- | --- | --- | --- | --- | --- |
| done P17 | Fix scoreability before more compute | `casp16_server_protein_v2_aliasfix` | P17 overlay completed and scored, repairing the 5 available-reference `missing_prediction` targets from P14 by reusing the P14 74-target run plus an added-only 5-target run | Required before extra seeds can become server-leaderboard progress | P25 seed106-125 target-seed jobs are now submitted; merge/score only after all declared candidates are present |
| cancelled | Run `server_attack_protenix_terminal_tag_seed101_105` | separate from `dev_fixed` | Slurm job `810719` cancelled while in seed104; partial diagnostic score was weak: domain fixed mean `0.044437`, oligo `0.000000` | Winner-level server comparison should not pretend one seed/sample is enough, but this older v1 terminal-tag path is not beating the v2 scoreable signal | Keep partial artifacts only; GPU budget was reallocated to the v2 target-sharded scoreable attack |
| P2 | `server_protenix_yang_large_target_split_or_fallback_seed101` | `casp16_server_protein_v1` | pending behind attack job | Extra seeds cannot fix `n_token > 2560` hard failures | Submit after attack job `810719` completes if coverage recovery remains highest leverage |
| P3 | `server_protenix_yang_sequence_recovery_seed101` | `casp16_server_protein_v1` | pending behind active jobs | Several domain hard zeros are local sequence parsing/alias failures, not model failures | Submit after attack and large-target fallback jobs; expect more jobs but better domain coverage |
| P4 | `server_protenix_yang_sequence_recovery_large_target_fallback_seed101` | `casp16_server_protein_v1` | pending behind active jobs | Combine the two coverage fixes before spending larger attack budgets | Submit after the attack and component coverage runs unless their results make the stack unnecessary |
| P5 | `yang_oligo_stoichiometry_recovery_v1` derivative | `casp16_server_protein_v1` | artifacts generated, not queued | Several oligo inputs silently use one copy per entity despite official A/B copy counts | Build token-safe or windowed derivative before queuing a full run |
| P6 | `server_protenix_yang_oligo_stoichiometry_token_safe_seed101` | `casp16_server_protein_v1` | pending behind active jobs | Restores exact stoichiometry for 5 under-budget oligo jobs without reintroducing token-limit failures | Submit after active pending jobs if exact stoichiometry remains the next oligo signal |
| superseded | `server_attack_protenix_coverage_stoich_seed101_105` | separate from `dev_fixed` | superseded:msa_reuse_successor | Same five-candidate attack budget as terminal-tag attack, but spent on inputs with sequence recovery, token fallback, and token-safe stoichiometry | Replaced by the MSA-reuse variant below; do not run the non-reuse row |
| pending | `server_attack_protenix_coverage_stoich_msa_reuse_seed101_105` | `casp16_server_protein_v1` | pending run spec; MSA preflight reuses 180/196 exact-sequence protein-chain paths and misses 16 | Lower-cost successor to the v1 coverage/stoich attack, but still an older v1 stack and less cache-complete than the v2 scoreable nofail attack | Do not launch before current terminal-tag and v2 scoreable attacks are scored; prefer v2 scoreable nofail while references remain incomplete |
| done | `casp16_server_protein_v2_aliasfix` | new benchmark version | generated | `2xxx` score-table rows inherit references/sequences from matching metadata; refs improved 54 -> 79 and jobs 106 -> 163 | Use for future winner-comparison runs; do not rewrite v1 |
| superseded | `server_v2_protenix_yang_coverage_stoich_seed101` | `casp16_server_protein_v2_aliasfix` | Slurm wrapper job `810938` is running the current oligo-recovery nofail dev row, not this superseded row | Older alias-fixed coverage + token-safe stoich input lacks protein-oligo sequence recovery | Keep only as ablation |
| superseded | `server_v2_protenix_yang_coverage_stoich_low_complexity_seed101` | `casp16_server_protein_v2_aliasfix` | superseded | Older low-complexity row lacks protein-oligo sequence recovery | Keep only as ablation |
| superseded | `server_v2_protenix_yang_coverage_stoich_low_complexity_large_fallback_seed101` | `casp16_server_protein_v2_aliasfix` | superseded | Older no-over-token row lacks protein-oligo sequence recovery | Keep only as ablation |
| done | `yang_protein_oligo_sequence_stoich_token_safe_v1` derivative | `casp16_server_protein_v2_aliasfix` | composed into no-over-token stack | Fixes a concrete server-input realism gap: several protein-oligo rows, including `H0220/H1220/H2220`, were locally represented as RNA or missing despite official protein sequences | Use the oligo-recovery nofail stack for the next v2 comparison |
| cancelled | `server_v2_attack_scoreable_oligo_recovery_msa_reuse_protenix5_seed101_105` | `casp16_server_protein_v2_aliasfix` | Slurm job `811751` cancelled while stuck at 36 seed101 CIFs on large `H1220`; last useful diagnostic had domain mean `0.099576`, oligo mean `0.028394`, and nonzero rows `H1202=0.924`, `H0272=0.428`, `H1204=0.421` | Confirms exact H-oligo QSglob can move, but also proves the monolithic Protenix target loop is the bottleneck once MSA is cached | Keep partial artifacts only; target-sharded P14 is now the main path |
| done P14 | `server_v2_attack_scoreable_size_balanced_msa_reuse_protenix5_seed101_105` | `casp16_server_protein_v2_aliasfix` | completed and scored: 370/370 candidates, domain mean `0.102777`, oligo mean `0.116923`; P16 consensus replay scored slightly lower | Current best complete v2 scoreable attack, but still had 5 available-reference targets as `missing_prediction` | Keep as baseline; P17 is the active input-repair successor |
| done P17 | `server_v2_attack_scoreable_input_repair_overlay_msa_reuse_protenix5_seed101_105` | `casp16_server_protein_v2_aliasfix` | completed and scored: 395/395 candidates, domain mean `0.107690`, oligo mean `0.118933`; the full repaired rerun jobs `812765..812770` were cancelled and replaced by the P14 plus added-only overlay | Repairs `T1212`, `T1239V2`, `T1249V2O`, `T1269V1O`, and `T2249V2O` without changing the locked benchmark | Use as seed101-105 overlay input for P25; consensus replay was lower, so keep `protenix_confidence_v1` |
| deferred | `server_v2_attack_scoreable_oligo_size_first_phase_alias_msa_reuse_protenix5_seed101_105` | `casp16_server_protein_v2_aliasfix` | superseded:target_sharded_replacement; old auto-advance Slurm job `812202` was cancelled | Same input and budget as P14 but monolithic, so it would repeat the H1220/H0258 blocking pattern | Keep only as a serial-scheduler ablation |
| P15 | `server_v4_attack_scoreable_size_balanced_shard01..06_msa_reuse_protenix5_seed101_105` | `casp16_server_protein_v4_refmap` | prepared, not submitted; six run specs are `deferred:await_p14_score`, rank-ineligible, and refreshed `diagnostics/msa_cache/protenix5_v4_scoreable_target_run_preflight.tsv` is `6/6 ok` with complete MSA reuse and 0 stale paths | Same five-candidate scoreable attack as P14, but on the v4 refmap benchmark with audited `T1278/T2278 -> 9hav` reference coverage, raising the scoreable subset from 74 to 76 jobs | Re-evaluate after P17 is merged/scored and only report as v4, not v2 |
| done P16 | `server_v2_attack_scoreable_size_balanced_msa_reuse_protenix5_seed101_105_consensus_replay` | `casp16_server_protein_v2_aliasfix` | predeclared before P14 target-score inspection and scored with no new GPU work | Replayed the same completed P14 prediction pool with `diversity_confidence_consensus_v1`, testing QA/model selection without references or official scores | Slightly below P14, so selector replay is not the next bottleneck |
| deferred O5 | `server_v2_attack_scoreable_antibody_fv_size_balanced_shard01..06_msa_reuse_protenix5_seed101_105` | `casp16_server_protein_v2_aliasfix` | prepared, not submitted; all six run specs are `deferred:base_target_shards_first`, rank-ineligible, and have complete MSA reuse | Target-sharded version of the risky antibody branch: same 74-job scoreable set and five-candidate budget as P14, but trims sequence-detected antibody constant regions on 12 H targets after target-lab Fv evidence | Do not submit until P17 is merged/scored; launch only if exact server QSglob/domain scoring suggests the Fv branch is worth the next GPU wave |
| O5b | `server_v2_attack_scoreable_input_repair_antibody_fv_shard01..06_msa_reuse_protenix5_seed101_105` | `casp16_server_protein_v2_aliasfix` | prepared, not submitted; budget JSON and shard TSV are checked in; all six run specs are `deferred:await_p25_score`, rank-ineligible, `server_attack`, and batch preflight is `6/6 ok` with complete MSA reuse (`146/146`, 0 stale) | Repaired-input successor to O5 on the P17/P25 79-job scoreable input; trims 24 antibody-like constant-region sequences across 12 targets while preserving all repaired jobs | Do not submit while P25 is running or unscored; use only if P25 shows antibody/Fv oligos remain the next recoverable weakness |
| superseded | `server_v2_attack_scoreable_oligo_first_phase_alias_msa_reuse_protenix5_seed101_105` | `casp16_server_protein_v2_aliasfix` | superseded:oligo_size_first_successor | Corrected A1B4 phase aliases but starts with 2515-token `H0220` and reaches 2535-token blockers early | Keep only as a scheduling ablation; do not launch |
| superseded | `server_v2_attack_scoreable_oligo_first_msa_reuse_protenix5_seed101_105` | `casp16_server_protein_v2_aliasfix` | superseded:phase_alias_oligo_state_fix | Older oligo-first source input kept `H0220` as `A1B1` despite later official aliases exposing `A1B4` | Keep only as an ablation of queue ordering; do not launch |
| superseded | `server_v2_attack_oligo_recovery_nofail_msa_reuse_protenix5_seed101_105` | `casp16_server_protein_v2_aliasfix` | superseded:scoreable_subset_attack; Slurm wrapper job `811751` will now pick the scoreable-subset run via `run-next` | Same nofail stack and five-candidate budget, but 165 jobs repeats no-reference heavy targets such as `T1295/T1295O` before reference recovery | Keep as the full-input ablation; do not run ahead of the scoreable-subset attack |
| deferred | `server_v2_protenix_yang_oligo_sequence_stoich_hydrophobic_leader_nofail_msa_reuse_seed101` | `casp16_server_protein_v2_aliasfix` | deferred:slurm_wrapper_cancelled; pending Slurm wrapper `811754` was cancelled after `run-next --dry-run` returned `no_pending_runs` | Narrow D1d construct-cleanup ablation on the current nofail stack: trims signal-like hydrophobic leaders on 8 T0240/T1210/T1240 alias jobs, keeps 165 jobs and 0 over-token, reuses 260/268 MSA paths | Re-enable only after scoreable attack and full v2 dev score clarify whether this ablation is worth a slot |
| superseded | `server_v2_attack_oligo_recovery_nofail_protenix5_seed101_105` | `casp16_server_protein_v2_aliasfix` | superseded:msa_reuse_attack | Same strategy and budget as P13, but would repeat MSA search across runs | Do not submit; keep as the non-reuse ablation row |
| superseded | `server_v2_attack_nofail_protenix5_seed101_105` | `casp16_server_protein_v2_aliasfix` | superseded candidate | Older five-candidate no-over-token v2 stack lacks protein-oligo sequence recovery | Do not submit before the new oligo-recovery nofail attack unless an ablation requires it |
| covered | `target_lab/h1258_interaction_window_v1` | target_lab only | artifact generated; standalone run skipped because the same H1258 window job completed inside `small_complex_stoich_batch_v1` | Public CASP16 complex clue says top Yang H1258 models used LRRK2 interaction-domain window | Promote only as a target-agnostic window rule |
| done | `target_lab/small_complex_stoich_batch_v1` | target_lab only | job `811114` complete; 6/6 structures and confidence files | Compact batch for exact stoichiometry plus H1258 window learning | DockQ diagnostic: H1233 strong positive `0.850`, H1236 moderate `0.206`, H1232 weak `0.023`, H1258 window chain mapping failed; promote only target-agnostic exact-stoich/QSglob work |
| done | `target_lab/domain_fragment_batch_v1` | target_lab only | job `810862` complete; 12/12 structures and confidence files | Compact domain-decomposition reproduction for D2 winner recipe | Diagnostic confidence is high on most fragments; promote only target-agnostic segmentation, not CASP-domain hand crops |
| target_lab | `811918` | `targetlab_protenix_yang_antibody_fv_seed101` | target_lab only | complete on `c620-142`; 8/8 CIFs, confidence summaries, and DockQ diagnostics | Eight full-MSA/template Fv-only antibody-antigen jobs from `yang_antibody_fv_fragment_inputs_v1`; DockQ strong positives `H0233__fv=0.916` and `H1233__fv=0.891`; never ranked |
| superseded P18 | `casp16_server_attack_protenix25_scoreable_nofail` | `casp16_server_protein_v2_aliasfix` | prepared, not queued; target+seed shard manifest has 30 rows for the pre-P17 74-target input | Winner-like compute is likely more than five candidates, but this artifact predates P17's 79-target input repair | Do not launch the old 74-target P18 grid; use the repaired P25 plan below if P17 justifies scale-up |
| P25 submitted | `casp16_server_attack_protenix25_scoreable_input_repair` | `casp16_server_protein_v2_aliasfix` | submitted Slurm jobs `812935..812958` for the 24 seed106-125 target-seed shards; latest live gate at `2026-07-07 14:09 CDT` is `ready=false`, `compatible=true`, 19 running, 5 pending behind `QOSMaxJobsPerUserLimit`, `1106` observed candidates, `944` shard-level missing, complete MSA reuse, and large-complex inference currently active on scoreable targets | This is the winner-like 25-candidate successor to P17 on the repaired 79-target scoreable input | Wait for all jobs to finish, merge with the overlay, then score/leaderboard the complete 25-candidate row; do not score partial output or launch O5b/P27b early |
| P19 | `casp16_server_attack_protenix25_nofail` | `casp16_server_protein_v2_aliasfix` | planned, not queued; keep as full-input ablation while references are incomplete | Same 25-seed budget on the 165-job oligo-recovery nofail stack, with exact-sequence MSA paths reused across shards | Do not launch before reference recovery or a recorded decision to spend compute on full-input ablation |
| design P27 | `casp16_server_attack_msa_model_diversity_v1` | post-P17 server benchmark, likely `casp16_server_protein_v2_aliasfix` unless v4 is selected first | non-executable budget design recorded in `attack_budgets/casp16_server_attack_msa_model_diversity_v1.json`; selector hook `diversity_confidence_consensus_v1` is implemented; P27a below is the first concrete model/config variant | Reproduces the MULTICOM4/QA4-style lesson: diverse MSA/model generation plus QA, with real MSA/template settings, rather than just turning one Protenix input through more seeds | Build broader MSA/model variants only if P17 and P27a evidence show that model/config diversity is worth more than seed scaling, reference recovery, or input repair |
| P27a | `server_v2_attack_scoreable_defaultparams_shard01..06_msa_reuse_protenix5_seed101_105` | `casp16_server_protein_v2_aliasfix` | prepared, not submitted; budget JSON and shard TSV are checked in; all six run specs are `deferred:await_p14_score`, rank-ineligible, `server_attack`, and batch preflight is `6/6 ok` with complete MSA reuse | First executable model/config diversity probe on the pre-P17 74-target scoreable target shards, seeds `101..105`, sample count, real MSA/template, and selector, flipping only `use_default_params:false -> true` | Retarget after P17 if model/config diversity is selected; keep as a separate attack row, never merge into P17 |
| P27b | `server_v2_attack_scoreable_input_repair_defaultparams_shard01..06_msa_reuse_protenix5_seed101_105` | `casp16_server_protein_v2_aliasfix` | prepared, not submitted; budget JSON and shard TSV are checked in; all six run specs are `deferred:await_p25_score`, rank-ineligible, `server_attack`, and batch preflight is `6/6 ok` with complete MSA reuse (`146/146`, 0 stale) | Repaired-input successor to P27a on the P17/P25 79-job scoreable input; same seeds, selector, real MSA/template settings, and only `use_default_params:false -> true` changed | Do not submit while P25 is running or unscored; use only if P25 shows seed scaling is weak and model/config diversity is selected |
| deferred D6 | `server_v2_domain_sequence_recovery_oligo_nofail_msa_reuse_after_warmup_seed101` | `casp16_server_protein_v2_aliasfix` | `deferred:await_p14_score`; 169 jobs, 0 over-token, warmup predictions and MSA cache exist for repaired `T1228V1/T1239V1/T1276`, and refreshed preflight is `1/1 ok` with complete exact-sequence MSA reuse (`276/276` protein chains, 0 stale) in `diagnostics/msa_cache/domain_sequence_recovery_after_warmup_preflight.tsv`; no follow-up predictions yet | Reference-gap triage found protein-domain targets misparsed as DNA or empty jobs (`T1276/T1228V1/T1239V1/T2276` class), but it is a single-seed input-repair ablation | Keep queued behind P25; launch only if the complete P25 score still shows domain zeros from input-kind or alias repair classes |

## Latest Baseline Result

Pinned server targets live in `docs/SERVER_SCORE_TARGETS.md`: beat domain
leader `110s` fixed mean `0.923321` on GDT_TS and oligo leader `456s` fixed
mean `0.582615` on QSglob.

| Run | Status | Domain mean | Domain coverage | Oligo status | Key failure signal |
| --- | --- | --- | --- | --- | --- |
| `server_protenix_full_msa_template_seed101` | complete and scored | `0.063962` | 15 ok / 30 missing prediction / 26 missing reference over 71 official server-domain targets | needs QSglob rescore after mapping validation | 8 Protenix jobs failed with `n_token > 2560`: `T1295`, `H0217`, `H0258`, `H0272`, `H1217`, `H1258`, `H1272`, `T1295O` |
| `server_protenix_yang_terminal_tag_cleanup_seed101` | complete and scored | `0.066908` | 15 ok / 30 missing prediction / 26 missing reference over 71 official server-domain targets | needs QSglob rescore after mapping validation | Same 8 Protenix token-limit failures as baseline; small net domain gain from `T1234`, `T1298`, and `T1210` |
| `server_protenix_yang_oversize_domain_monomer_fallback_seed101` | complete and scored | `0.065114` | 15 ok / 29 missing prediction / 27 failed or missing-reference over 71 official server-domain targets | needs QSglob rescore after mapping validation | Produced 99/106 CIFs and rescued `T1295` inference, but `T1295` still scores `0` because the local server benchmark lacks a reference mapping |
| `server_protenix_yang_antibody_fv_cleanup_seed101` | complete and scored | `0.060677` | 15 ok / 30 missing prediction / 26 missing reference over 71 official server-domain targets | needs QSglob rescore after mapping validation | Produced 98/106 CIFs; antibody oligo predictions exist for H0222/H0223/H0225/H1222/H1223/H1225 but need assembly mapping before ranked QSglob claims |

QSglob signal probe on six oligo targets: baseline `H0222=0.075`,
`T1249V1O=0.090`; terminal-tag cleanup `T1249V1O=0.122`; oversize fallback
`H1232=0.032`; antibody-Fv cleanup `H0222=0.037`, `T1249V1O=0.125`. This is
not a full oligo leaderboard, but it shows QSglob can guide strategy triage
once mapping false zeros are isolated.

## Queued Next

| Priority | Run | Strategy | Artifact | Benchmark | Status | Hypothesis |
| --- | --- | --- | --- | --- | --- | --- |
| done | `server_protenix_yang_oversize_domain_monomer_fallback_seed101` | `yang_oversize_domain_monomer_fallback_v1` | `strategies/yang_oversize_domain_monomer_fallback_v1/casp16_server_protein_v1/` | `casp16_server_protein_v1` | complete and scored | Rescue the known `T1295` server-domain zero caused by Protenix `n_token > 2560` by replacing only a single-entity domain `A8` job with one representative chain |
| done | `server_protenix_yang_antibody_fv_cleanup_seed101` | `yang_antibody_fv_cleanup_v1` | `strategies/yang_antibody_fv_cleanup_v1/casp16_server_protein_v1/` | `casp16_server_protein_v1` | complete and scored negative | Antibody-Fv cleanup lowered the ranked domain mean and cannot yet be judged on oligos until QSglob assembly mapping is validated |
| deferred | `server_protenix_yang_terminal_tag_antibody_fv_cleanup_seed101` | `yang_terminal_tag_antibody_fv_cleanup_v1` | `strategies/yang_terminal_tag_antibody_fv_cleanup_v1/casp16_server_protein_v1/` | `casp16_server_protein_v1` | deferred | Do not launch the stacked run before QSglob mapping or a positive antibody-complex signal exists |
| deferred | `server_protenix_yang_epitope_tag_cleanup_seed101` | `yang_epitope_tag_cleanup_v1` | `strategies/yang_epitope_tag_cleanup_v1/casp16_server_protein_v1/` | `casp16_server_protein_v1` | deferred | Token-limit hard failures need a predeclared split/fallback policy before another construct-cleanup full run |
| cancelled | `server_attack_protenix_terminal_tag_seed101_105` | `yang_terminal_tag_cleanup_v1_server_attack` | `runs/server_attack_protenix_terminal_tag_seed101_105/` | `casp16_server_protein_v1` | Slurm job `810719` cancelled after partial weak diagnostic; latest CIF counts were `98/98/98/81/0` for seeds `101..105` | Five fixed seeds on the old v1 terminal-tag path were not competitive with the v2 scoreable signal, so the GPU was reallocated |
| P2 | `server_protenix_yang_large_target_split_or_fallback_seed101` | `yang_large_target_split_or_fallback_v1` | `runs/server_protenix_yang_large_target_split_or_fallback_seed101/` | `casp16_server_protein_v1` | pending behind attack job | Convert the eight `n_token > 2560` failures into under-budget jobs by predeclared chain/copy fallback |
| P3 | `server_protenix_yang_sequence_recovery_seed101` | `yang_sequence_recovery_v1` | `runs/server_protenix_yang_sequence_recovery_seed101/` | `casp16_server_protein_v1` | pending behind active jobs | Recover protein-domain inputs that were missing or misparsed as nucleic-acid records |
| P4 | `server_protenix_yang_sequence_recovery_large_target_fallback_seed101` | `yang_sequence_recovery_large_target_fallback_v1` | `runs/server_protenix_yang_sequence_recovery_large_target_fallback_seed101/` | `casp16_server_protein_v1` | pending behind active jobs | Stack sequence recovery with token-budget fallback; 40 unique changed targets and max optimized job 2535 tokens |
| generated | not queued | `yang_oligo_stoichiometry_recovery_v1` | `strategies/yang_oligo_stoichiometry_recovery_v1/casp16_server_protein_v1/` | `casp16_server_protein_v1` | artifacts generated | Restore official oligo copy counts for 9 existing jobs; 5 remain under token limit and 4 need construct/window handling |
| P6 | `server_protenix_yang_oligo_stoichiometry_token_safe_seed101` | `yang_oligo_stoichiometry_token_safe_v1` | `runs/server_protenix_yang_oligo_stoichiometry_token_safe_seed101/` | `casp16_server_protein_v1` | pending behind active jobs | Apply exact stoichiometry only for under-budget oligo jobs on top of stacked coverage recovery |
| superseded | `server_attack_protenix_coverage_stoich_seed101_105` | `yang_coverage_stoich_token_safe_v1_server_attack` | `runs/server_attack_protenix_coverage_stoich_seed101_105/` | `casp16_server_protein_v1` | superseded:msa_reuse_successor | Non-reuse predecessor of the stacked coverage + token-safe stoichiometry attack |
| pending | `server_attack_protenix_coverage_stoich_msa_reuse_seed101_105` | `yang_coverage_stoich_token_safe_v1_server_attack_msa_reuse` | `runs/server_attack_protenix_coverage_stoich_msa_reuse_seed101_105/` | `casp16_server_protein_v1` | pending; MSA preflight `180/196` reused, `16` missing source | Keep as a lower-priority v1 ablation; do not run ahead of the v2 scoreable nofail path |
| superseded | `server_v2_protenix_yang_coverage_stoich_seed101` | `yang_oligo_stoichiometry_token_safe_v1` | `runs/server_v2_protenix_yang_coverage_stoich_seed101/` | `casp16_server_protein_v2_aliasfix` | superseded; Slurm wrapper job `810938` is running the new oligo-recovery nofail dev row | Older v2 baseline lacks protein-oligo sequence recovery; keep only as ablation |
| superseded | `server_v2_protenix_yang_coverage_stoich_low_complexity_seed101` | `yang_coverage_stoich_low_complexity_v1` | `runs/server_v2_protenix_yang_coverage_stoich_low_complexity_seed101/` | `casp16_server_protein_v2_aliasfix` | superseded | Older construct-cleanup row lacks protein-oligo sequence recovery; keep only as ablation |
| superseded | `server_v2_protenix_yang_coverage_stoich_low_complexity_large_fallback_seed101` | `yang_coverage_stoich_low_complexity_large_fallback_v1` | `runs/server_v2_protenix_yang_coverage_stoich_low_complexity_large_fallback_seed101/` | `casp16_server_protein_v2_aliasfix` | superseded | Older no-over-token row lacks protein-oligo sequence recovery; keep only as ablation |
| generated | not queued | `yang_protein_oligo_sequence_recovery_v1` | `strategies/yang_protein_oligo_sequence_recovery_v1/casp16_server_protein_v2_aliasfix/` | `casp16_server_protein_v2_aliasfix` | artifacts generated | Recover 5 protein-oligo targets whose local server inputs were missing or represented as nucleic-acid records despite official protein-like sequences |
| generated | not queued | `yang_protein_oligo_sequence_stoich_token_safe_v1` | `strategies/yang_protein_oligo_sequence_stoich_token_safe_v1/casp16_server_protein_v2_aliasfix/` | `casp16_server_protein_v2_aliasfix` | artifacts generated | Compose oligo sequence recovery with token-safe stoichiometry; changes 15 targets but is not a no-over-token full stack because unrelated v2 jobs such as `H0272` still exceed 2560 tokens |
| generated | not queued | `yang_protein_oligo_sequence_stoich_token_safe_v1` | `strategies/yang_protein_oligo_sequence_stoich_token_safe_v1/casp16_server_protein_v4_refmap/` | `casp16_server_protein_v4_refmap` | artifacts generated; MSA cache `286/286`, 0 stale | Carries the H1265 score-table variant alias repair into v4/refmap inputs; `H1265_V1/V2/V3` become H1265-derived two-chain protein jobs, but remain reference-blocked until variant/native assembly and QSglob mapping are proven |
| cancelled | `server_v2_protenix_yang_oligo_sequence_stoich_low_complexity_large_fallback_seed101` | `yang_oligo_sequence_stoich_low_complexity_large_fallback_v1` | `runs/server_v2_protenix_yang_oligo_sequence_stoich_low_complexity_large_fallback_seed101/` | `casp16_server_protein_v2_aliasfix` | cancelled:scoreable_subset_attack after 39/165 CIFs when it reached no-reference `T1295`; Slurm job `810938` is `CANCELLED+`/cleaning | Keep partial artifacts/MSA cache only; do not resume full-input dev before reference recovery |
| cancelled | `server_v2_attack_scoreable_oligo_recovery_msa_reuse_protenix5_seed101_105` | `scoreable_target_subset_v1_oligo_recovery_nofail_server_attack_protenix5` | `runs/server_v2_attack_scoreable_oligo_recovery_msa_reuse_protenix5_seed101_105/` | `casp16_server_protein_v2_aliasfix` | Slurm job `811751` cancelled after 36/74 seed-101 CIFs while stuck on `H1220` | Five fixed seeds on the strongest no-over-token v2 stack produced useful partial QSglob signal but was replaced by target-sharded execution |
| done P14 | `server_v2_attack_scoreable_size_balanced_msa_reuse_protenix5_seed101_105` | `target_shards_scoreable_size_balanced_v1_server_attack_protenix5` | `strategies/target_shards_scoreable_size_balanced_v1/casp16_server_protein_v2_aliasfix/` and merged `runs/server_v2_attack_scoreable_size_balanced_msa_reuse_protenix5_seed101_105/` | `casp16_server_protein_v2_aliasfix` | completed and scored: 370/370 candidates, domain mean `0.102777`, oligo mean `0.116923`; 5 scoreable rows remained `missing_prediction`; P16 consensus replay scored slightly lower | Keep as current best complete v2 scoreable attack, but treat the exposed 5 missing predictions as the next score-path fix before scale-up |
| done P17 | `server_v2_attack_scoreable_input_repair_overlay_msa_reuse_protenix5_seed101_105` | `target_shards_scoreable_input_repair_overlay_v1_server_attack_protenix5` | `strategies/scoreable_target_subset_input_repair_added_only_v1/`, P14 merged predictions, and `runs/server_v2_attack_scoreable_input_repair_overlay_msa_reuse_protenix5_seed101_105/` | `casp16_server_protein_v2_aliasfix` | completed and scored: 79 scoreable jobs, 395 CIFs, domain mean `0.107690`, oligo mean `0.118933`; full P17 shard jobs were replaced by the overlay | Same five-candidate budget as P14, but repairs `T1212`, `T1239V2`, `T1249V2O`, `T1269V1O`, and `T2249V2O`; use this as seeds101-105 for P25 |
| P15 | `server_v4_attack_scoreable_size_balanced_shard01..06_msa_reuse_protenix5_seed101_105` | `target_shards_scoreable_size_balanced_v1_server_attack_protenix5` | `strategies/target_shards_scoreable_size_balanced_v1/casp16_server_protein_v4_refmap/` and `runs/server_v4_attack_scoreable_size_balanced_shard*/` | `casp16_server_protein_v4_refmap` | prepared only; six run specs are `deferred:await_p14_score`, rank-ineligible, and `diagnostics/msa_cache/protenix5_v4_scoreable_target_run_preflight.tsv` is `6/6 ok` with complete MSA reuse | Same five-candidate scoreable attack on the v4 refmap benchmark, adding the audited `T1278/T2278` scoreable jobs; re-evaluate after P17 and report as v4, not v2 |
| deferred O5 | `server_v2_attack_scoreable_antibody_fv_size_balanced_shard01..06_msa_reuse_protenix5_seed101_105` | `target_shards_scoreable_antibody_fv_size_balanced_v1_server_attack_protenix5` | `strategies/target_shards_scoreable_antibody_fv_size_balanced_v1/casp16_server_protein_v2_aliasfix/` and `runs/server_v2_attack_scoreable_antibody_fv_size_balanced_shard*/` | `casp16_server_protein_v2_aliasfix` | prepared only; six run specs are `deferred:base_target_shards_first`, rank-ineligible, and MSA preflight is `141/141` reused with `0` missing | Target-sharded O5 branch for the same scoreable attack budget; trims antibody constant regions in a sequence-only way, but target-lab DockQ positives are not server QSglob evidence |
| O5b | `server_v2_attack_scoreable_input_repair_antibody_fv_shard01..06_msa_reuse_protenix5_seed101_105` | `target_shards_scoreable_input_repair_antibody_fv_size_balanced_v1_server_attack_protenix5` | `strategies/scoreable_input_repair_antibody_fv_cleanup_v1/`, `strategies/target_shards_scoreable_input_repair_antibody_fv_size_balanced_v1/`, and six run specs | `casp16_server_protein_v2_aliasfix` | prepared only; six run specs are `deferred:await_p25_score`, rank-ineligible, and MSA preflight is `146/146` reused with `0` stale | Repaired 79-job antibody/Fv branch; use instead of the stale 74-job O5 branch if P25 identifies Fv/antibody oligos as the next weakness |
| deferred | `server_v2_attack_scoreable_antibody_fv_oligo_size_first_phase_alias_msa_reuse_protenix5_seed101_105` | `scoreable_antibody_fv_oligo_size_first_phase_alias_v1_server_attack_protenix5` | `runs/server_v2_attack_scoreable_antibody_fv_oligo_size_first_phase_alias_msa_reuse_protenix5_seed101_105/` | `casp16_server_protein_v2_aliasfix` | deferred:target_shards_first; MSA preflight `141/141` reused, `0` missing, using target-lab Fv MSA source | Tests sequence-only antibody constant trimming on top of the phase-alias size-first attack; keep behind the safer target-sharded scoreable run |
| superseded | `server_v2_attack_scoreable_oligo_first_phase_alias_msa_reuse_protenix5_seed101_105` | `scoreable_target_subset_oligo_first_phase_alias_v1_nofail_server_attack_protenix5` | `runs/server_v2_attack_scoreable_oligo_first_phase_alias_msa_reuse_protenix5_seed101_105/` | `casp16_server_protein_v2_aliasfix` | superseded:oligo_size_first_successor | Correct A1B4 input but poorer queue order than the size-first successor |
| superseded | `server_v2_attack_scoreable_oligo_first_msa_reuse_protenix5_seed101_105` | `scoreable_target_subset_oligo_first_v1_oligo_recovery_nofail_server_attack_protenix5` | `runs/server_v2_attack_scoreable_oligo_first_msa_reuse_protenix5_seed101_105/` | `casp16_server_protein_v2_aliasfix` | superseded:phase_alias_oligo_state_fix | Older pending retry had stale `H0220` `A1B1`; replaced by the phase-alias A1B4 row |
| superseded | `server_v2_attack_oligo_recovery_nofail_msa_reuse_protenix5_seed101_105` | `yang_oligo_sequence_stoich_low_complexity_large_fallback_v1_msa_reuse_server_attack_protenix5` | `runs/server_v2_attack_oligo_recovery_nofail_msa_reuse_protenix5_seed101_105/` | `casp16_server_protein_v2_aliasfix` | superseded:scoreable_subset_attack; Slurm job `811751` remains as the dependency wrapper but will call `run-next` | Full 165-job MSA-reuse attack; keep as ablation until missing references are recovered |
| deferred | `server_v2_protenix_yang_oligo_sequence_stoich_hydrophobic_leader_nofail_msa_reuse_seed101` | `yang_oligo_sequence_stoich_low_complexity_hydrophobic_leader_large_fallback_v1_msa_reuse` | `runs/server_v2_protenix_yang_oligo_sequence_stoich_hydrophobic_leader_nofail_msa_reuse_seed101/` | `casp16_server_protein_v2_aliasfix` | deferred:slurm_wrapper_cancelled; Slurm job `811754` cancelled before launch because v2 `run-next` has no pending row | Single-seed hydrophobic-leader cleanup on T0240/T1210/T1240 alias jobs; run after scoreable attack only if still useful |
| superseded | `server_v2_attack_oligo_recovery_nofail_protenix5_seed101_105` | `yang_oligo_sequence_stoich_low_complexity_large_fallback_v1_server_attack_protenix5` | `runs/server_v2_attack_oligo_recovery_nofail_protenix5_seed101_105/` | `casp16_server_protein_v2_aliasfix` | superseded:msa_reuse_attack | Non-reuse predecessor of the P12 run; keep only as an ablation |
| superseded | `server_v2_attack_nofail_protenix5_seed101_105` | `yang_coverage_stoich_low_complexity_large_fallback_v1_server_attack_protenix5` | `runs/server_v2_attack_nofail_protenix5_seed101_105/` | `casp16_server_protein_v2_aliasfix` | superseded | Older no-over-token attack input lacks protein-oligo sequence recovery; keep only as ablation unless explicitly launched |
| target_lab | covered | `h1258_interaction_window_v1` | `target_lab/h1258_interaction_window_v1/` | target_lab only | artifact generated; standalone run skipped because the same H1258 window completed inside `small_complex_stoich_batch_v1` | LRRK2 residues 861-1014 plus 14-3-3 A1B2, total 648 tokens |
| target_lab | `811114` | `small_complex_stoich_batch_v1` | `target_lab/small_complex_stoich_batch_v1/` | target_lab only | complete; 6/6 structures and DockQ diagnostics generated | Six-job batch: H1232/H1233/H1236/H1244/H1267 exact stoich plus H1258 window |
| target_lab | `810862` | `domain_fragment_batch_v1` | `target_lab/domain_fragment_batch_v1/` | target_lab only | complete; 12/12 structures and confidence summary generated | Twelve domain-fragment jobs testing whether CASP-domain decomposition is worth a future target-agnostic rule |
| target_lab | `811918` | `targetlab_protenix_yang_antibody_fv_seed101` | `runs/targetlab_protenix_yang_antibody_fv_seed101/` | target_lab only | complete; 8/8 structures, confidence summaries, and DockQ diagnostics generated | Eight full-MSA/template Fv-only antibody-antigen jobs; H0233/H1233 DockQ-positive diagnostic for O5, never ranked |

The terminal-tag, oversize-domain fallback, and antibody-Fv runs are complete
and scored. The next valuable work is scorer mapping and benchmark capability,
not another single-seed construct rerun. `run-next` should not be used again until the
deferred statuses are intentional or new run specs are created for the next
predeclared policy.

Generation commands used:

```bash
./casp16 strategy-inputs --benchmark casp16_server_protein_v1 --strategy yang_terminal_tag_cleanup_v1
./casp16 run-spec \
  --run-id server_protenix_yang_terminal_tag_cleanup_seed101 \
  --benchmark casp16_server_protein_v1 \
  --input-json strategies/yang_terminal_tag_cleanup_v1/casp16_server_protein_v1/inputs.json \
  --input-manifest strategies/yang_terminal_tag_cleanup_v1/casp16_server_protein_v1/manifest.tsv \
  --strategy yang_terminal_tag_cleanup_v1 \
  --use-msa --use-template --use-default-params \
  --enable-cache --enable-fusion
./casp16 strategy-inputs --benchmark casp16_server_protein_v1 --strategy yang_oversize_domain_monomer_fallback_v1
./casp16 run-spec \
  --run-id server_protenix_yang_oversize_domain_monomer_fallback_seed101 \
  --benchmark casp16_server_protein_v1 \
  --input-json strategies/yang_oversize_domain_monomer_fallback_v1/casp16_server_protein_v1/inputs.json \
  --input-manifest strategies/yang_oversize_domain_monomer_fallback_v1/casp16_server_protein_v1/manifest.tsv \
  --strategy yang_oversize_domain_monomer_fallback_v1 \
  --use-msa --use-template --use-default-params \
  --enable-cache --enable-fusion
./casp16 strategy-inputs --benchmark casp16_server_protein_v1 --strategy yang_antibody_fv_cleanup_v1
./casp16 run-spec \
  --run-id server_protenix_yang_antibody_fv_cleanup_seed101 \
  --benchmark casp16_server_protein_v1 \
  --input-json strategies/yang_antibody_fv_cleanup_v1/casp16_server_protein_v1/inputs.json \
  --input-manifest strategies/yang_antibody_fv_cleanup_v1/casp16_server_protein_v1/manifest.tsv \
  --strategy yang_antibody_fv_cleanup_v1 \
  --use-msa --use-template --use-default-params \
  --enable-cache --enable-fusion
./casp16 strategy-inputs --benchmark casp16_server_protein_v1 --strategy yang_terminal_tag_antibody_fv_cleanup_v1
./casp16 run-spec \
  --run-id server_protenix_yang_terminal_tag_antibody_fv_cleanup_seed101 \
  --benchmark casp16_server_protein_v1 \
  --input-json strategies/yang_terminal_tag_antibody_fv_cleanup_v1/casp16_server_protein_v1/inputs.json \
  --input-manifest strategies/yang_terminal_tag_antibody_fv_cleanup_v1/casp16_server_protein_v1/manifest.tsv \
  --strategy yang_terminal_tag_antibody_fv_cleanup_v1 \
  --use-msa --use-template --use-default-params \
  --enable-cache --enable-fusion
./casp16 strategy-inputs --benchmark casp16_server_protein_v1 --strategy yang_epitope_tag_cleanup_v1
./casp16 run-spec \
  --run-id server_protenix_yang_epitope_tag_cleanup_seed101 \
  --benchmark casp16_server_protein_v1 \
  --input-json strategies/yang_epitope_tag_cleanup_v1/casp16_server_protein_v1/inputs.json \
  --input-manifest strategies/yang_epitope_tag_cleanup_v1/casp16_server_protein_v1/manifest.tsv \
  --strategy yang_epitope_tag_cleanup_v1 \
  --use-msa --use-template --use-default-params \
  --enable-cache --enable-fusion
```

All queued Protenix reruns intentionally match the baseline engine flags:
MSA, templates, default params, cache, fusion, and TF32 are enabled.

## Budget Discipline

The current queue is the `dev_fixed` tier: one seed (`101`), one sample, and
`first_output_only`. It is deliberately strict so agents can compare strategy
changes without compute-budget noise. It is not a claim that CASP16 winner
servers used only one seed or one internal candidate.

After single-seed failures and wins are scored, promote promising strategies to
a separate `server_attack` tier with a fixed multi-seed or multi-sample budget
and a predeclared confidence-only model selection rule. Do not mix
`server_attack` rows into `dev_fixed` rankings, and do not choose the submitted
model using references, official scores, or target-score feedback.

The first `server_attack` budget uses five candidates per target because it is
the smallest useful realism check, not because CASP16 winners are assumed to
have used only five candidates. A winner-like budget probably includes more
than literal random seeds: MSA/template variants, model/backend variants,
refinement, ranking, and submitted models all count as candidates. Any larger
candidate budget must be a new predeclared attack-budget version and should
report candidates per target, expected GPU-hours, actual wall time, and
selection policy.

The first larger planned tier is
`attack_budgets/casp16_server_attack_protenix25.json`: 25 fixed seeds
(`101..125`), one sample per seed, the same `protenix_confidence_v1` selector,
and five predeclared seed shards. The exact shard run ids, seed ranges, input
artifact, and selector live in
`attack_budgets/casp16_server_attack_protenix25_shards.tsv`. It is not queued
until the active `protenix5` run and the v2 alias-fixed development baseline
justify the spend.

The nofail 25-candidate tier is
`attack_budgets/casp16_server_attack_protenix25_nofail.json`. It uses the same
25 seeds and selector, but its shards now point at the current 165-job
MSA-reused `inputs_msa_reuse_from_dev_seed101.json` artifact rather than the
older coverage/stoich nofail input. Do not submit it before the scoreable
`protenix5` attack and reference-recovery decision; if local references remain
incomplete, create an explicit scoreable-subset 25-seed budget instead of
silently changing this one.

The old scoreable nofail 25-candidate tier exists as
`attack_budgets/casp16_server_attack_protenix25_scoreable_nofail.json`.
It uses the same 25 seeds, predicts the pre-P17 74 locally scoreable jobs, and keeps
the locked 175-target scoring set through the benchmark `input_manifest.tsv`.
The launch manifest
`attack_budgets/casp16_server_attack_protenix25_scoreable_target_seed_shards.tsv`
is prepared as a six target-shard by five seed-block grid. It predates P17's
79-target repaired input and is superseded for launches by the repaired tier
below.

The current scoreable input-repair 25-candidate tier is
`attack_budgets/casp16_server_attack_protenix25_scoreable_input_repair.json`.
It uses the P17 repaired 79-job target shards, reuses the six running
seed101-105 P17 shards, and prepares 24 deferred seed106-125 specs in
`attack_budgets/casp16_server_attack_protenix25_scoreable_input_repair_target_seed_shards.tsv`.
`diagnostics/msa_cache/protenix25_scoreable_input_repair_target_seed_run_preflight.tsv`
is `30/30 ok` with complete exact-sequence MSA reuse and 0 stale paths. The
readiness probe intentionally reports `ready=false` while P17 is still running
and seed106-125 are deferred. This is preparation for a post-P17 scale-up, not
permission to launch it.

The oversize-domain fallback result is a reminder to spend realistic attack
compute carefully: extra seeds will not fix hard Protenix token-limit failures,
missing references, or unvalidated QSglob mapping. Clean coverage, reference
mapping, and scorer validation should come before a costly multi-candidate
push.
The same applies after installation: extra candidates cannot fix a scorer that
maps the predicted assembly to the wrong reference chains.

The antibody-Fv result reinforces the same rule. A strategy that is negative on
the ranked domain track and unmeasurable on oligos should not be promoted to a
multi-seed attack tier merely because CASP16 winners likely used more than one
internal candidate.

## Backlog

| Priority | Strategy | Status | Reason To Try | Stop Condition |
| --- | --- | --- | --- | --- |
| done | Install OpenStructure `ost` for QSglob | installed at `/scratch/10992/liaorunlong93/conda/envs/ost-qsglob/bin/ost` | Oligo server scores are not rank-comparable without QSglob | Next bottleneck is assembly/chain mapping, not tool availability |
| P6 | `yang_low_complexity_terminal_cleanup_v1` | artifacts generated, not queued | H0217/H0272/H1217/H1272 have short terminal low-complexity regions that match Yang-style construct cleanup | Queue only after tag cleanup helps or baseline failures justify more aggressive trimming |
| P7 | `yang_hydrophobic_leader_cleanup_v1` | v2 nofail derivative queued as `server_v2_protenix_yang_oligo_sequence_stoich_hydrophobic_leader_nofail_msa_reuse_seed101` | T0240/T1210/T1240-style N termini contain signal-like hydrophobic leaders; construct cleanup may improve folded-core prediction | Risky branch; judge only as full-set `dev_fixed` after the current nofail mainline |
| P8 | `yang_domain_fragment_inputs_v1` | target-lab artifacts generated, not queued | Domain decomposition is a major winner recipe; CASP domain-summary fragments give a fast diagnostic upper bound | Not server-ranked; promote only via new benchmark version or predeclared segmentation rule |
| done | `yang_antibody_fv_fragment_inputs_v1` | target-lab run `811918` complete; 8/8 CIFs and DockQ diagnostics | Fv-only changed-target jobs are useful for fast antibody assembly diagnosis; H0233/H1233 are strong DockQ positives | Not server-ranked; keep separate from full-set claims |
| P26 | `scoreable_antibody_fv_oligo_size_first_phase_alias_v1` | target-sharded run specs prepared, not submitted | Promotes the Fv target-lab signal into an automatic scoreable full-benchmark attack branch without hand-picking targets | Launch only after P17 is merged/scored; stop if QSglob rejects the trimmed antibody branch |
| P10 | Domain crop/chain mapping | not started | Domain GDT_TS can be noisy or wrong without explicit CASP domain crops | Stop after target classes with clear mapping; do not hand-map every hard outlier |
| done | Alias-fixed server benchmark version | generated as `casp16_server_protein_v2_aliasfix` | `0xxx/1xxx/2xxx` aliasing recovers many server rows without target-specific tuning | Use v2 for future winner-comparison runs; keep in-flight v1 runs on v1 |
| P11 | Validate `server_attack` budget | first run spec pending | Winner-like server runs almost certainly use more than one internal candidate; local attack runs need fixed multi-seed/multi-sample rules | Score `server_attack_protenix_terminal_tag_seed101_105` and compare only as attack-tier evidence |
| P12 | `yang_large_target_split_or_fallback_v1` | artifacts generated | The new fallback changes exactly the 8 known token-limit failures and brings each optimized job under 2560 tokens | Queue only after the active attack job, then judge as coverage recovery rather than full assembly quality |
| P13 | Extra sampling/ranking lab | diagnostic only | CASP16 reports show sampling helps, but ranking is fragile | Never use best-of-N for ranked v1 without a new benchmark version |
| P14 | `yang_sequence_recovery_large_target_fallback_v1` | queued as `server_protenix_yang_sequence_recovery_large_target_fallback_seed101` | Sequence recovery exposes two additional oversized domain jobs, so the fixes should be tested together before larger attack budgets | Run only after active pending jobs unless component results make the stack unnecessary |
| P15 | `yang_oligo_stoichiometry_recovery_v1` | artifacts generated | Exact stoichiometry changes H1232/H1233/H1236/H1244/H1267 safely and exposes H1217/H1227/H1258/H1265 as oversized realistic assemblies | Do not queue exact full assemblies directly; create a token-safe or domain-window derivative first |
| P16 | `yang_oligo_stoichiometry_token_safe_v1` | queued as `server_protenix_yang_oligo_stoichiometry_token_safe_seed101` | This is the token-safe derivative: 5 exact-stoichiometry changes, max job 2535 tokens | Run after active pending jobs; keep oligos diagnostic until QSglob assembly mapping is validated |
| P17 | H1258 interaction-window target_lab | artifact generated | Public assessment says top Yang H1258 models used LRRK2 interacting region instead of full-length LRRK2 | Run as target_lab only; never count it as a ranked server result |
| done | Small complex stoich batch | job `811114` complete; summaries regenerated | Fast learning set for under-budget exact stoich and H1258 public window, max job 1929 tokens | H1233 is a strong exact-stoich positive; H1258 window remains unpromoted due DockQ chain-mapping failure |
| done | Domain fragment batch | job `810862` complete; 12/12 structures and confidence files summarized | Fast learning set for domain decomposition on long/multidomain protein targets, max fragment 1633 residues | Use only as target_lab evidence; promote only target-agnostic segmentation or new benchmark version |
| superseded | v2 low-complexity large fallback | queued as `server_v2_protenix_yang_coverage_stoich_low_complexity_large_fallback_seed101` | Extra seeds cannot repair v2 jobs that still exceed Protenix's token limit, but this older row lacks protein-oligo sequence recovery | Keep only as ablation; current queue uses the oligo-recovery nofail stack |
| done | `yang_protein_oligo_sequence_stoich_token_safe_v1` | composed into no-over-token stack | H0220/H1220/H2220-style false zeros may be bad input modality/sequence recovery problems before they are scorer problems | Next comparison should use the oligo-recovery nofail stack |
| cancelled | `yang_oligo_sequence_stoich_low_complexity_large_fallback_v1` | full-input `dev_fixed` job `810938` cancelled at no-reference `T1295`; partial artifacts kept | Current strongest runnable v2 input stack became the parent for scoreable-subset attack | Do not resume full-input dev before reference recovery |
| P23 | `protenix25` attack tier | budget JSON and shard TSV created, not queued; merge path implemented | Winner-scale comparison needs more than the starter five candidates | Keep as broader full-input ablation; use scoreable 25-seed first while references are incomplete |
| superseded P24 | `protenix25_scoreable_nofail` attack tier | budget JSON, target+seed shard TSV, readiness TSV, and 24 deferred seed106-125 run specs prepared for the pre-P17 74-target input | It was the first scoreable 25-seed plan | Superseded by the repaired 79-target P25 plan; keep for provenance only |
| P25 | `protenix25_scoreable_input_repair` attack tier | budget JSON, target+seed shard TSV, readiness TSV, and 24 seed106-125 run specs submitted as Slurm jobs `812935..812958`; preflight `24/24 ok` for the submitted slice | P17 was candidate-limited, so spend 25 seeds on the repaired locally scoreable jobs without repeating MSA search or reverting to the stale 74-target input | Wait for jobs, then score only via merged run with `--merged-candidate-count 25` readiness |
| P26 | `server_v2_domain_sequence_recovery_oligo_nofail_msa_reuse_after_warmup_seed101` | `deferred:await_p14_score` dev-fixed run spec with complete MSA reuse after completed 4-task warmup `server_v2_domain_sequence_recovery_msa_warmup_seed101` | Repairs domain inputs that reference-gap triage exposed as protein-vs-DNA/empty parsing failures while keeping the strongest v2 nofail stack under the token limit | Do not queue multi-seed until P17 is handled; run this single-seed ablation only if the post-P17 decision matrix selects D6a |
| P27 | `casp16_server_attack_msa_model_diversity_v1` | design JSON created; P27a default-params variant prepared for the old 74-job scoreable input; P27b default-params variant prepared for the repaired 79-job input and deferred behind P25 | Public MULTICOM4/QA4 clues point to diverse MSA/model pools plus QA when a single input stack is valid but weak | Do not submit P27b before P25 scoring; no MSA-disabled toy setting, no hidden per-target variant choice, and broader MSA variants still need automatic preflightable inputs |
| O5b | `casp16_server_attack_protenix5_input_repair_antibody_fv` | budget JSON, shard TSV, repaired-input strategy artifacts, and six deferred run specs prepared; preflight `6/6 ok` | Target-lab Fv-only diagnostics were positive on antibody examples, and this variant brings that target-agnostic cleanup onto the repaired 79-job scoreable input | Do not submit before P25 scoring; launch only if P25 shows antibody/Fv oligo failures are a better next spend than P27b or reference recovery |

## Evidence Links

- CASP16 official z-score page: https://predictioncenter.org/casp16/zscores_final.cgi
- CASP16 monomer assessment: https://pmc.ncbi.nlm.nih.gov/articles/PMC12157625/
- Yang Lab optimized-input paper: https://yanglab.qd.sdu.edu.cn/papers/Wang_Proteins_2026.pdf
- MULTICOM4 CASP16 paper: https://www.nature.com/articles/s42003-025-08960-6
