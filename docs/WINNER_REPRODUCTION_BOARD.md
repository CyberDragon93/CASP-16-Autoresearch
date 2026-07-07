# CASP16 Winner Reproduction Board

This is the short control board for the score-chasing loop. Keep the long
evidence and history in `docs/CASP16_WINNER_RECIPES.md`,
`docs/AUTORESEARCH.md`, and `docs/AUTORESEARCH_QUEUE.md`; use this file when
choosing the next concrete branch.

## Current Score Target

Official server leaders to beat on the local server-style comparator:

| Track | Official metric | Fixed targets | Server leader | Mean to beat |
| --- | --- | ---: | --- | ---: |
| protein domain | GDT_TS | 71 | `110s` MIEnsembles-Server | `0.923321` |
| protein oligo | QSglob | 104 | `456s` Yang-Multimer | `0.582615` |

Current best complete local server-v2 attack baseline:

| Run | Budget | Domain | Oligo | Full fixed-set mean |
| --- | --- | ---: | ---: | ---: |
| `server_v2_attack_scoreable_input_repair_overlay_msa_reuse_protenix5_seed101_105` | 5 candidates, confidence selector | `0.107690` | `0.118933` | `0.114371554` |

This is not close to the winners yet. The immediate goal is to raise valid
scoreable-target signal and coverage without using references or official
per-target scores during prediction.

## Winner-Match Gap

The current complete local row is still a reproduction scaffold, not a
champion-level method:

| Track | Best complete local | Server winner | Absolute gap | Relative level |
| --- | ---: | ---: | ---: | ---: |
| protein domain | `0.107690` | `0.923321` | `0.815631` | `11.7%` of winner |
| protein oligo | `0.118933` | `0.582615` | `0.463682` | `20.4%` of winner |

To call a run "winner-matching", it must be scored on the server-style fixed
target sets, with the same missing-as-zero rule, and be compared to
server-only groups in `official_server_groups.csv`. A `target_lab` result,
DockQ-only result, small `casp16_protein_v1` result, partial shard, or
unmerged P25 row is not a winner-comparison point.

The fastest honest route to matching the winner is not to add random
infrastructure. It is:

1. Finish P25 and test whether a 25-candidate pool plus predeclared selector
   materially improves the repaired P17 baseline.
2. If P25 is flat but complete, launch P27b to test model/config diversity.
3. If P25 exposes a predeclared input failure class, launch D6a or O5b as
   selected by the aggregate post-P25 readout.
4. If scoring is reference-capped, continue only versioned refmap work before
   spending more GPU.

## Active Gate

Checked `2026-07-07 15:56 CDT`: P25 is still incomplete, but the live jobs
look healthy.

| Gate | Status |
| --- | --- |
| run family | `casp16_server_attack_protenix25_scoreable_input_repair` |
| benchmark | `casp16_server_protein_v2_aliasfix` |
| observed candidates | `1388` |
| shard-level missing candidates | `670` |
| full 25-candidate slots still missing | `603` |
| complete full-budget tasks | `4 / 79` |
| Slurm | 19 P25 jobs running, 5 P25 jobs pending behind `QOSMaxJobsPerUserLimit`; `gh` `MaxJobsPU=20` and one `tacc-vscode` job is also running |
| health | no traceback/OOM/killed-process signatures in P25 logs; recent CIF writes reached 15:54 CDT |
| action | wait for declared candidates, then run the P25 closeout wrapper |

Do not score the P25 row or launch O5b/P27b/D6a from partial outputs. The
current wait is queue plus large-complex Protenix forward time; it is not an
MSA-cache failure or a reason to open another infrastructure detour.

MSA diversity note: Protenix exposes a real `--msa_server_mode` switch
(`protenix` or `colabfold`), and local `run-spec` now records this as a first
class field. That makes a future ColabFold/MMseqs MSA variant auditable without
turning off MSA. Keep it behind the complete P25 readout and the prepared P27b
model/config probe unless the post-P25 decision explicitly selects MSA
diversity.

## Recipe Reproduction Board

| Winner clue | Local reproduction | Current evidence | Next action | Stop or skip condition |
| --- | --- | --- | --- | --- |
| Top domain servers had broad coverage and high automatic accuracy | Yang-style input repair: sequence recovery, phase aliases, low-complexity cleanup, token-safe fallback | P17 repaired the 5 scoreable missing-prediction rows and is the best complete local server-v2 row | Keep P17 as the seed101-105 overlay for P25 | Stop adding input-cleanup variants until P25 shows a specific failure class |
| Top server families are MIEnsembles/Zheng/Yang/Guijun rather than a single narrow trick | balanced automatic pipeline with input realism, candidate diversity, and QA | official group registry maps `110s` to MIEnsembles-Server, `456s` to Yang-Multimer, `052s` to Yang-Server, `019s/147s` to Zheng, and `148s` to Guijunlab-Complex | Keep winner reproduction focused on broad server-style rows, not isolated target rescues | Do not claim a recipe matched the winner unless the fixed-set server score closes the gap |
| Winner-scale systems use multiple internal candidates, but ranking is fragile | P25: 25 fixed seeds on the repaired 79-job scoreable subset with `protenix_confidence_v1` | Submitted as Slurm jobs `812935..812958`; MSA preflight was complete; still running | Finish P25, merge, score, regenerate leaderboard, then inspect aggregate deltas | Never score a partial 25-candidate row; if flat and valid, do not just add more seeds |
| MULTICOM/QA-style systems rely on diverse model/MSA pools plus QA | P27b repaired-input default-params model/config variant; broader MSA/model diversity design gate; future P28a-style `msa_server_mode=colabfold` probe | P27b is prepared and MSA-clean, but deferred behind P25; MSA server mode is now explicit in run specs | If complete P25 is flat with valid predictions/metrics, launch P27b before another seed grid; only then consider a production ColabFold/MMseqs MSA variant | Do not turn off MSA or use toy settings; do not choose variants per target from scores |
| Complex winners/top methods still struggle on antibodies and high-order stoichiometry; specialized handling can help | O5b repaired-input antibody/Fv branch | Target-lab Fv diagnostics were positive, and O5b preflight is clean | Launch only if P25 shows antibody/Fv oligos are the dominant recoverable weakness | Do not use target-lab DockQ positives as leaderboard evidence |
| Domain decomposition and construct boundaries matter | D6a domain sequence recovery after warmup; domain-fragment target-lab evidence | D6a MSA reuse is complete after warmup | Launch D6a only if P25 domain zeros cluster around input-kind/alias/domain classes | Do not hand-pick CASP domain crops from target scores |
| Local comparison is capped by missing references and QSglob mapping | Versioned refmap work: v4 now has 81/175 refs; v5 queue is lane-based | Lane B deferred sequence hits are reviewed and rejected; Lane D oligo assemblies fail target-stoichiometry matching; Lane E all-domain relaxed90 sweep covers 16 families with no accepted references; all 13 Lane F oligo families now have relaxed90 probe coverage with no accepted references; H1265 input aliases are repaired but reference-blocked | Continue only strict v5 reference lanes while GPU jobs run | Do not patch v2/v4 in place or promote sequence hits without native/reference proof |

## Post-P25 Decision

Use only the complete merged P25 score and the read-only helper:

```bash
scripts/finish_p25_scoreable_input_repair.sh --dry-run \
  --output-tsv /tmp/casp16_p25_readiness_live.tsv
scripts/finish_p25_scoreable_input_repair.sh
./casp16 post-p25-readout --benchmark casp16_server_protein_v2_aliasfix
./casp16 post-p25-branch-readiness
```

The P25 closeout wrapper is replay-safe: once all declared candidates exist,
it merges the 25-candidate pool, registers
`server_v2_attack_scoreable_input_repair_size_balanced_msa_reuse_protenix25_seed101_125_consensus_replay`
against the same predictions with `diversity_confidence_consensus_v1`, writes
prediction-only selection QA sidecars, and then scores both rows together. This
adds no GPU work and must be interpreted as candidate-selection evidence, not a
new prediction budget. On a successful closeout it also writes
`diagnostics/score_probes/server_v2_attack_scoreable_input_repair_size_balanced_msa_reuse_protenix25_seed101_125.post_p25_readout.json`
so the next branch decision is captured with the leaderboard refresh.

Decision order:

1. P25 improves broadly over P17: analyze target deltas and selector behavior
   before launching anything else.
2. P25 is flat but valid: launch P27b model/config diversity.
3. P25 domain failures cluster on input-kind/alias/domain classes: launch D6a.
4. P25 oligo failures cluster on antibody/Fv rows: launch O5b.
5. P25 is mostly reference-capped: continue versioned refmap work, not GPU.

## Deferred Branch Artifacts

`./casp16 post-p25-readout` is the machine-readable source of truth for which
branch is selected; its `launch_plan` includes read-only `run_specs` and
`preflight` summaries for the selected branch. This table is the human index
for the prepared artifacts so the next agent does not rediscover them after
P25 finishes.
Those summaries are generated from local `run_spec.json`, `runs/status.tsv`,
and existing preflight TSVs only; they are safe to read before launch and do
not run GPU work.
The same readout includes `target_delta_summary`; it reports `status:
incomplete` until both the baseline and P25 have complete scoreable
`target_scores.csv` rows. After P25 is scored, use the `status: ok` summary to
explain aggregate gains/losses and selector behavior; do not use those target
deltas to tune prediction inputs target by target.
Use `./casp16 post-p25-branch-readiness` while P25 is still running to verify
that all deferred branch artifacts remain launch-clean. Latest read-only audit:
P27b, D6a, O5b, and P15/v4 are all launch-ready after P25 selection, and all
four branch families now have `deferred:await_p25_score` lifecycle rows plus
complete run specs and `ok` preflights.

| Branch | Trigger | Budget or manifest | Preflight | Launch shape |
| --- | --- | --- | --- | --- |
| P27b model/config diversity | P25 complete, valid, and flat versus P17 | `attack_budgets/casp16_server_attack_protenix5_input_repair_defaultparams_model_variant.json`; shards in `attack_budgets/casp16_server_attack_protenix5_input_repair_defaultparams_model_variant_shards.tsv` | `diagnostics/msa_cache/protenix5_input_repair_defaultparams_model_variant_preflight.tsv`, `6/6 ok`, `146/146` chains reused | six target-disjoint GH200 shards, seeds `101..105`, real MSA/template, only `use_default_params=true` differs |
| P28a ColabFold/MMseqs MSA mode | P25 and P27b are valid but model/config diversity alone is flat; score loss looks MSA-depth or pairing related | design only in `attack_budgets/casp16_server_attack_msa_model_diversity_v1.json` | must create fresh run specs with `msa_server_mode=colabfold` or explicit precomputed A3M paths and prove all MSA paths exist | same repaired 79-job scoreable input, real MSA/template, seeds `101..105`; no no-MSA shortcut |
| D6a domain input repair | P25 domain zeros/failures cluster on the predeclared input-kind/alias class | run spec `runs/server_v2_domain_sequence_recovery_oligo_nofail_msa_reuse_after_warmup_seed101/run_spec.json` | `diagnostics/msa_cache/domain_sequence_recovery_after_warmup_preflight.tsv`, `1/1 ok`, `276/276` chains reused | one `dev_fixed` GH200 run; do not scale before the ablation scores |
| O5b antibody/Fv | P25 exact oligo signal exists, but antibody/Fv rows remain the dominant weakness | `attack_budgets/casp16_server_attack_protenix5_input_repair_antibody_fv.json`; shards in `attack_budgets/casp16_server_attack_protenix5_input_repair_antibody_fv_shards.tsv` | `diagnostics/msa_cache/protenix5_input_repair_antibody_fv_preflight.tsv`, `6/6 ok`, `146/146` chains reused | six target-disjoint GH200 shards; keep separate from P25/P27b |
| P15/v4 scoreable refmap | P25 is mostly measurement/reference capped and v4 comparison is explicitly chosen | `attack_budgets/casp16_server_attack_protenix5_v4_scoreable_target_shards.tsv` | `diagnostics/msa_cache/protenix5_v4_scoreable_target_run_preflight.tsv`, `6/6 ok`, `143/143` chains reused | six target-disjoint GH200 shards on `casp16_server_protein_v4_refmap`; report only as v4 |
| v5 refmap work | P25 cannot be fairly compared because missing references or QSglob mapping dominate | `diagnostics/reference_gap/casp16_server_protein_v5_refmap_recovery_queue.tsv` | no GPU preflight; acceptance requires native/domain or assembly/QSglob proof | versioned benchmark work only; never patch v2/v4 in place |

For a selected GPU branch, first mark only the selected run ids pending, then
dry-run the run spec and submit through a login node:

```bash
./casp16 mark-run --run-id <run_id> --status pending \
  --message "selected after complete P25 readout: <decision_status>"
./casp16 run-one --run-id <run_id> --dry-run
ssh login1 'cd /scratch/10992/liaorunlong93/casp16-leaderboard && RUN_ID=<run_id> sbatch --export=ALL slurm/casp16_run_one_gh200.slurm'
```

## File Map

| File | Role |
| --- | --- |
| `docs/CASP16_WINNER_RECIPES.md` | Long recipe rationale and source-to-experiment mapping |
| `docs/AUTORESEARCH.md` | Append-only current truth and experiment history |
| `docs/AUTORESEARCH_QUEUE.md` | Executable queue and branch gates |
| `docs/SERVER_SCORE_TARGETS.md` | Exact score targets, active closeout commands, and comparator rules |
| `docs/MSA_CACHE_PLAN.md` | MSA reuse policy and launch hygiene |
| `docs/REFERENCE_RECOVERY_V5_PLAN.md` | Versioned reference-recovery plan |
| `AGENTS.md` | Rules for agents and humans before modifying strategies or runs |
